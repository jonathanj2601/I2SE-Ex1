# I2SE Ex1 — Planar sections of a voxel volume

Given a 3D NRRD raster and a CSV of ordered triangle or trapezoid definitions, the program samples each planar section and writes an MP4 in CSV order. Its scope is scalar, three-dimensional voxel data and nearest-neighbor sampling in voxel index space.

## Run on Windows

Use Python 3.10 or later. In PowerShell, from this directory:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
New-Item -ItemType Directory -Force outputs | Out-Null
.\.venv\Scripts\python.exe Ex0.py 'MRHead_1 (1).nrrd' 'Ex0.csv - Sheet1.csv' outputs/demo.mp4
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe benchmark.py
```

The command-line interface is `python Ex0.py file.nrrd file.csv file.mp4`. The output directory must exist. The FFmpeg executable is supplied by the imageio-ffmpeg Windows wheel. If your platform requires a separate binary, set `IMAGEIO_FFMPEG_EXE` to the path of an FFmpeg build with libx264.

The first CSV column is the point count. Each point is an XYZ triple. The supplied header is optional. Use `a,b,c` for a triangle and `a1,a2,b,c` for a trapezoid, where the legs run from `a1` to `b` and from `a2` to `c`. Coordinates are zero-based NRRD axis indices. Invalid records produce marked error frames and a diagnostic with the physical CSV line number.

## Dataset

- [Supplied CSV](Ex0.csv%20-%20Sheet1.csv) contains four records, including two invalid geometries. See the experiment for its coverage on MRHead.
- [MRHead MRI from the assignment](https://drive.google.com/file/d/1cqqOgSf8k4e14K5CBs-V_EvMmATX1K-J/view?usp=sharing) is a gzip NRRD with shape `256 × 256 × 130` and signed 16-bit voxels. Place it in the project root and use its actual filename in the command. Its location and axis metadata describe physical space. CSV coordinates use voxel index space.
- The automated tests generate small NRRDs with known values. The benchmark generates a deterministic `500 × 500 × 500` uint8 volume in memory.

## Project documents

- [Software requirements specification](docs/SRS.md)
- [Algorithm design](docs/ALGORITHM.md)
- [Testing strategy](docs/TESTING.md)
- [Experiment and benchmark results](docs/EXPERIMENT.md)

The local `outputs/` directory is ignored by Git. The small [verified demo MP4](samples/mrhead-demo.mp4) is included in the repository, and the experiment documents how to reproduce it.
