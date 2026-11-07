from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest

import imageio_ffmpeg
import nrrd
import numpy as np

from inputs import HEADER, load_volume, read_planes
from projection import PlaneError, project, validate_plane
from video import canvas_shape, render_frame


class ProjectionTests(unittest.TestCase):
    def setUp(self):
        x, y, z = np.indices((5, 5, 4))
        self.volume = (100 * x + 10 * y + z + 1).astype(np.uint16)

    def test_axis_aligned_rectangular_section_and_endpoints(self):
        plane = validate_plane([(0, 1, 0), (0, 1, 3), (4, 1, 0), (4, 1, 3)])
        np.testing.assert_array_equal(project(self.volume, plane), self.volume[:, 1, :])

    def test_oblique_section_rounds_to_nearest_voxel(self):
        plane = validate_plane([(0, 0, 0), (0, 0, 3), (2, 2, 0), (2, 2, 3)])
        result = project(self.volume, plane)
        np.testing.assert_array_equal(result, self.volume[[0, 1, 1, 2], [0, 1, 1, 2], :])

    def test_halfway_ties_round_towards_positive_infinity(self):
        plane = validate_plane([(0.5, 0, 0), (0.5, 0, 1), (0.5, 1, 0), (0.5, 1, 1)])
        np.testing.assert_array_equal(project(self.volume, plane), self.volume[1, :2, :2])

    def test_triangle_apex_and_inclusive_base(self):
        plane = validate_plane([(0, 1, 0), (2, 0, 0), (2, 2, 0)])
        image, inside, count = project(self.volume, plane, coverage=True)
        self.assertEqual(image.shape, (4, 3))
        np.testing.assert_array_equal(image[0], [0, self.volume[0, 1, 0], 0])
        np.testing.assert_array_equal(image[-1], self.volume[2, :3, 0])
        self.assertEqual(inside, count)

    def test_trapezoid_centers_shorter_initial_base(self):
        plane = validate_plane([(0, 1, 0), (0, 3, 0), (4, 0, 0), (4, 4, 0)])
        image = project(self.volume, plane)
        np.testing.assert_array_equal(image[0], [0, *self.volume[0, 1:4, 0], 0])
        np.testing.assert_array_equal(image[-1], self.volume[4, :, 0])

    def test_continuous_bounds_before_rounding(self):
        plane = validate_plane([(-0.25, 0, 0), (-0.25, 0, 1), (0.75, 0, 0), (0.75, 0, 1)])
        image, inside, count = project(self.volume, plane, coverage=True)
        np.testing.assert_array_equal(image, [[0, 0], self.volume[1, 0, :2]])
        self.assertEqual((inside, count), (2, 4))

    def test_entire_section_outside_and_singleton_axis(self):
        plane = validate_plane([(0, 0, 1), (0, 1, 1), (1, 0, 1), (1, 1, 1)])
        result = project(self.volume[:, :, :1], plane)
        self.assertFalse(result.any())

    def test_invalid_geometries(self):
        cases = {
            "equal lengths": [(0, 0, 0), (1, 0, 0), (0, 1.002, 0)],
            "degenerate": [(0, 0, 0), (1, 0, 0), (-1, 0, 0)],
            "coincident": [(0, 0, 0), (1, 0, 0), (1, 0, 0)],
            "coplanar": [(0, 0, 1), (0, 2, -1), (2, 0, 0), (2, 2, 0)],
            "no longer": [(0, 0, 0), (0, 4, 0), (2, 1, 0), (2, 3, 0)],
            "parallel": [(0, 0, 0), (2, 0, 0), (0, 2, 0), (4, 0, 0)],
            "cross": [(0, 2, 0), (0, 0, 0), (2, 0, 0), (2, 2, 0)],
            "finite": [(0, 0, 0), (1, 0, 0), (0, float("nan"), 0)],
            "4096": [(0, 0, 0), (6000, 0, 0), (0, 6000, 0)],
        }
        for message, points in cases.items():
            with self.subTest(message=message), self.assertRaisesRegex(PlaneError, message):
                validate_plane(points)

    def test_accepts_small_leg_length_difference(self):
        validate_plane([(0, 0, 0), (1, 0, 0), (0, 1.0005, 0)])


class InputAndVideoTests(unittest.TestCase):
    triangle = "3,0,1,0,3,0,0,3,2,0,,,"
    trapezoid = "4,0,0,0,0,2,0,3,0,0,3,2,0"

    def setUp(self):
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)
        self.nrrd = self.directory / "input.nrrd"
        self.csv = self.directory / "planes.csv"

    def write_csv(self, rows, *, header=True):
        lines = [",".join(HEADER), *rows] if header else rows
        self.csv.write_text("\n".join(lines) + "\n", encoding="utf-8-sig")

    def test_nrrd_types_endianness_and_axis_order(self):
        for dtype, encoding in [("uint8", "raw"), ("<u2", "gzip"),
                                (">u4", "raw"), ("<i2", "gzip")]:
            with self.subTest(dtype=dtype):
                original = (np.arange(24) + 1).reshape(2, 3, 4).astype(dtype)
                if original.dtype.kind == "i":
                    original -= 12
                nrrd.write(str(self.nrrd), original, header={"encoding": encoding}, index_order="F")
                result = load_volume(self.nrrd)
                np.testing.assert_array_equal(result, original)
                self.assertEqual((result.dtype.kind, result.dtype.itemsize),
                                 (original.dtype.kind, original.dtype.itemsize))

    def test_rejects_unsupported_nrrd(self):
        for data in (np.zeros((2, 2), np.uint8), np.zeros((1024, 1, 1), np.uint8),
                     np.zeros((2, 2, 2), np.float32)):
            nrrd.write(str(self.nrrd), data)
            with self.assertRaises(ValueError):
                load_volume(self.nrrd)

    def test_rejects_malformed_nrrd(self):
        self.nrrd.write_bytes(b"not an NRRD\n")
        with self.assertRaisesRegex(ValueError, "Invalid NRRD"):
            load_volume(self.nrrd)

    def test_csv_mixed_rows_and_recovery(self):
        self.write_csv([self.triangle, "", '"broken', "4,1,2", self.trapezoid])
        records = read_planes(self.csv)
        self.assertEqual([record.line for record in records], [2, 4, 5, 6])
        self.assertEqual([record.plane is not None for record in records],
                         [True, False, False, True])

    def test_headerless_and_empty_csv(self):
        self.write_csv([self.triangle], header=False)
        self.assertIsNotNone(read_planes(self.csv)[0].plane)
        self.write_csv([])
        with self.assertRaisesRegex(ValueError, "no plane records"):
            read_planes(self.csv)

    def test_video_intensity_mapping_and_padding(self):
        section = np.array([[-128, 0, 128]], dtype=np.int16)
        frame = render_frame(section, (4, 6), -128, 128)
        np.testing.assert_array_equal(frame[1], [0, 1, 0, 255, 0, 0])
        full = np.array([[2**32 - 1]], dtype=np.uint32)
        self.assertEqual(render_frame(full, (1, 1), 0, 2**32 - 1)[0, 0], 255)

    def test_cli_video_decodes_one_frame_per_row_in_order(self):
        volume = np.full((4, 3, 1), 127, dtype=np.uint8)
        nrrd.write(str(self.nrrd), volume)
        outside = "4,0,0,2,0,2,2,3,0,2,3,2,2"
        self.write_csv([self.trapezoid, "3,1,2,3", outside])
        output = self.directory / "result.mp4"
        script = Path(__file__).resolve().parents[1] / "Ex0.py"
        result = subprocess.run([sys.executable, "-B", str(script), str(self.nrrd),
                                 str(self.csv), str(output)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("CSV line 3:", result.stderr)
        height, width = canvas_shape(read_planes(self.csv))
        frames = subprocess.run(
            [imageio_ffmpeg.get_ffmpeg_exe(), "-v", "error", "-i", str(output),
             "-f", "rawvideo", "-pix_fmt", "gray", "pipe:1"],
            capture_output=True, check=True,
        ).stdout
        images = np.frombuffer(frames, dtype=np.uint8).reshape(-1, height, width)
        self.assertEqual(len(images), 3)
        self.assertGreater(images[0, height // 2, width // 2], 200)
        self.assertLess(int(images[0, 5, 5]), 30)
        self.assertGreater(images[1, 5, 5], 100)
        self.assertLess(int(images[2].max()), 30)


if __name__ == "__main__":
    unittest.main()
