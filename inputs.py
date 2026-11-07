"""Load the assignment's NRRD and spreadsheet CSV formats."""

import csv
from dataclasses import dataclass

import nrrd

from projection import Plane, PlaneError, validate_plane

HEADER = ["Number of Points (3 or 4)"] + [
    f"{axis}{point}" for point in range(1, 5) for axis in "xyz"
]


def load_volume(path):
    # Inspect the header before decoding the potentially large voxel array.
    header = nrrd.read_header(str(path))
    if header.get("dimension") != 3 or any(
        not 1 <= size <= 1023 for size in header["sizes"]
    ):
        raise ValueError("Expected three NRRD dimensions in the range 1..1023")
    volume, _ = nrrd.read(str(path), index_order="F")
    if (volume.dtype.kind, volume.dtype.itemsize) not in {
        ("u", 1), ("u", 2), ("u", 4), ("i", 2)
    }:
        raise ValueError("Expected uint8, uint16, uint32, or signed int16 voxels")
    return volume


@dataclass(frozen=True)
class PlaneRow:
    line: int
    plane: Plane | None
    error: str = ""


def parse_plane(fields):
    if fields[0] not in ("3", "4"):
        raise PlaneError("Point count must be 3 or 4")
    count = int(fields[0])
    expected = 1 + 3 * count
    if len(fields) < expected or len(fields) > len(HEADER) or any(fields[expected:]):
        raise PlaneError(f"Expected exactly {count} XYZ points")
    return validate_plane([
        fields[index:index + 3] for index in range(1, expected, 3)
    ])


def read_planes(path):
    """Return ordered records. Blank physical rows are ignored."""
    records = []
    first = True
    with open(path, encoding="utf-8-sig", newline="") as source:
        # The supplied sheet has one plane per physical line. Parsing each
        # line independently lets a broken quote produce a single error frame.
        for line, text in enumerate(source, 1):
            if not text.strip():
                continue
            try:
                fields = [item.strip() for item in next(csv.reader([text], strict=True))]
                if first and [item.casefold() for item in fields] == [
                    item.casefold() for item in HEADER
                ]:
                    continue
                records.append(PlaneRow(line, parse_plane(fields)))
            except (csv.Error, PlaneError) as exc:
                records.append(PlaneRow(line, None, str(exc)))
            finally:
                first = False
    if not records:
        raise ValueError("CSV contains no plane records")
    return records
