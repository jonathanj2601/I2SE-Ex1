"""Required demo entry point: python Ex0.py input.nrrd planes.csv output.mp4."""

import argparse
import sys

from inputs import load_volume, read_planes
from video import write_demo


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("volume")
    parser.add_argument("planes")
    parser.add_argument("output")
    args = parser.parse_args()
    try:
        volume = load_volume(args.volume)
        records = read_planes(args.planes)
        report = write_demo(volume, records, args.output)
    except (OSError, ValueError, RuntimeError) as exc:
        parser.exit(1, f"Error: {exc}\n")
    for record, (inside, total) in zip(records, report):
        if record.plane is None:
            print(f"CSV line {record.line}: {record.error}", file=sys.stderr)
        else:
            print(f"CSV line {record.line}: {inside}/{total} samples in volume "
                  f"({inside / total:.1%})")
    print(f"Wrote {len(records)} frames to {args.output}")


if __name__ == "__main__":
    main()
