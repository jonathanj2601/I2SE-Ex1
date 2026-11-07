# Experiment and benchmark

## Supplied MRI and spreadsheet

Run the command in the [README](../README.md) to reproduce the [included demo MP4](../samples/mrhead-demo.mp4). The input is the signed 16-bit MRHead NRRD with shape 256 × 256 × 130 and the original four data rows from the supplied spreadsheet.

| MP4 frame | CSV line | Result | Samples in the MRI |
| ---: | ---: | --- | ---: |
| 1 | 2 | Triangle | 9,423 / 90,465 (10.4%) |
| 2 | 3 | Rectangle | 33,150 / 200,901 (16.5%) |
| 3 | 4 | Error frame, unequal legs | N/A |
| 4 | 5 | Error frame, unequal legs | N/A |

Most sample positions in both valid sections are outside this MRI. This is consistent with CSV coordinates up to 500 on an MRI whose highest Z index is 129. Outside positions appear black. Coverage counts positions inside the volume even when their voxel values are zero. FFmpeg decoded four 502 × 450 H.264 frames at 2 FPS. Visual inspection confirmed visible anatomy in frames 1–2 and legible diagnostics in frames 3–4. The included MP4 is 15,659 bytes.

## Projection performance

Run `python benchmark.py --frames 150`. The benchmark generates a seeded, 125,000,000-byte Fortran-order uint8 array with shape 500 × 500 × 500. It warms up each geometry with 10 projections and times 150 full raster projections per case. The same validated geometry is reused for each case. Timing includes generating the sample grid and gathering voxel values, and excludes volume allocation, CSV parsing, validation, video rendering and encoding.

Measured on Windows 11, Intel Core i7-13620H, Python 3.12.14, and NumPy 2.5.4.

| Section | Width × height | Time | Projection FPS |
| --- | ---: | ---: | ---: |
| Axis-aligned rectangle | 400 × 500 | 0.163 s | 919.74 |
| Oblique rectangle | 400 × 501 | 0.251 s | 598.35 |
| Triangle | 500 × 500 | 0.821 s | 182.76 |

All three cases exceeded the mandatory 30 FPS and the expected 100 FPS on this run. The rectangles use the constant-width path. The triangle exercises the variable-width path. Results depend on geometry, memory access, and hardware.

## Automated verification

`python -m unittest discover -s tests -v` passed all 16 tests in 1.271 seconds, including the CLI encode/decode test. The test run emitted an upstream pynrrd deprecation warning about `datetime.utcnow()`.
