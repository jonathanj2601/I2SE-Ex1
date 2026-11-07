"""Measure projection throughput for a deterministic 500-cubed uint8 volume."""

import argparse
import platform
from time import perf_counter

import numpy as np

from projection import project, validate_plane


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--frames", type=int, default=150, help="frames per case")
    args = parser.parse_args()
    if args.frames < 1:
        parser.error("--frames must be positive")

    volume = np.empty((500, 500, 500), dtype=np.uint8, order="F")
    volume.ravel(order="F")[:] = np.random.default_rng(42).integers(
        0, 256, size=volume.size, dtype=np.uint8
    )
    axis = validate_plane([(0, 0, 100), (0, 0, 499),
                           (499, 0, 100), (499, 0, 499)])
    oblique = validate_plane([(0, 0, 0), (0, 0, 399),
                              (353, 353, 0), (353, 353, 399)])
    triangle = validate_plane([(0, 249.5, 100), (431, 0, 100), (431, 499, 100)])
    print(f"{platform.platform()} | {platform.machine()} | {platform.processor()}")
    print(f"Python {platform.python_version()}, NumPy {np.__version__}")
    for label, plane in (("Axis-aligned", axis), ("Oblique", oblique),
                         ("Triangle", triangle)):
        for _ in range(10):
            project(volume, plane)
        start = perf_counter()
        for _ in range(args.frames):
            project(volume, plane)
        seconds = perf_counter() - start
        print(f"{label} {plane.shape[1]}x{plane.shape[0]}: "
              f"{args.frames / seconds:.2f} FPS ({args.frames} frames in {seconds:.3f}s)")


if __name__ == "__main__":
    main()
