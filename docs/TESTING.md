# Testing strategy

Run `python -m unittest discover -s tests -v`. The suite creates synthetic NRRDs and video files in disposable directories. It exercises the public command with an actual FFmpeg encode and decode.

| Area | Checks |
| --- | --- |
| NRRD | Raw and gzip storage, signed short, unsigned 8/16/32-bit types, big-endian data, asymmetric XYZ shape, bad dimension count, oversized axis, unsupported dtype. |
| Geometry | Triangle apex and final base, a shorter initial base, rectangular and oblique sections, tolerated small leg difference, unequal legs, coincident or collinear points, noncoplanarity, reversed base size, nonparallel bases, crossed legs, nonfinite values and section size limit. |
| Sampling | Exact analytical arrays from a coordinate-coded volume, halfway ties, fractional out-of-volume coordinates, wholly outside geometry and a singleton axis. |
| CSV | Supplied header format, BOM, headerless input, blank lines, missing fields, malformed quotes, recovery and line order. |
| Video | Padding, signed and uint32 intensity conversion, normal and error frames, output decodability, exact frame count and order through the CLI. |

Run the MRHead demo as a separate integration experiment. Compare its output frame count with the four data rows. Check in-volume coverage for the valid sections and the error frame positions for the invalid sections. Use the synthetic cases as the oracle for pixel correctness because MRHead and the spreadsheet have different coordinate ranges. See the [experiment](EXPERIMENT.md) for observed results and benchmark methodology.
