# Software requirements specification

## Functional requirements

| ID | Requirement |
| --- | --- |
| FR-01 | The program shall accept a scalar 3D NRRD with 1–1023 voxels per axis and uint8, uint16, uint32, or int16 samples. The signed int16 case supports MRHead. |
| FR-02 | The demo shall accept `python Ex0.py file.nrrd file.csv file.mp4`. The CSV shall follow the supplied count-plus-XYZ layout. The parser shall accept an optional supplied header, UTF-8 with or without BOM, standard quoting on one physical line, surrounding whitespace, and blank trailing cells for unused coordinates. Blank lines are ignored. |
| FR-03 | The program shall validate finite point triples, nonzero equal legs with absolute difference below EPS = 0.001, and nondegenerate geometry. A trapezoid shall have coplanar points, nonzero parallel bases, an initial base no longer than its final base, and consistent endpoint order. EPS is in index units. |
| FR-04 | The projector shall sample the bounded section in zero-based voxel index space using nearest-neighbor sampling. It shall return a 2D image in the source dtype, with zero outside the volume and section footprint. |
| FR-05 | The demo shall write one readable MP4 frame per nonblank data record, preserving CSV order. Malformed records and invalid geometry shall produce a marked error frame. An unusable volume, empty CSV, or encoding failure shall cause a command-level error. |
| FR-06 | Frames shall share a single even-sized canvas. The demo shall center each section and use one volume-wide intensity mapping. |

## Performance and operational requirements

- The assignment requires more than 30 projection FPS on a `500³` byte volume and expects at least 100 FPS. The benchmark shall report actual projection throughput separately from I/O and encoding.
- The implementation shall use vectorized NumPy sampling and bound temporary memory by processing rows in blocks. The output MP4 shall be written one frame at a time and replace the destination only after a successful encoder exit.
- The automated tests shall cover axis order, dtype, geometry, sampling, parser recovery, video encoding and decoding. The experiment shall record test and benchmark results and include the demo MP4 for submission.

## Design limits

The geometry may extend outside the volume. The demo accepts coordinates up to an absolute magnitude of 1,000,000 and sections up to 4096 pixels per axis to bound arithmetic and allocation. Larger records produce a marked error frame. NRRD physical-space directions and origin are outside the coordinate contract. Playback is fixed at 2 FPS so viewers can inspect each section.
