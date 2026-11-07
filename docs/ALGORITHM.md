# Planar sampling algorithm

## Coordinate model

Read NRRD in Fortran index order so the array is indexed as `volume[x, y, z]` in the axis order listed in the NRRD header. The closed sampling domain is `0 ≤ coordinate ≤ size − 1` on each axis. The 2D output uses the standard image order `image[row, column]`, which corresponds to `E[x][y]` in the handout. Rows run toward the final base and columns run from the left leg to the right leg.

## Validation and scan

1. For a triangle, use the apex as both start points. For a trapezoid, use `a1` and `a2`. Both shapes end at `b` and `c`. Check equal leg lengths using the strict EPS inequality. Reject zero or near-zero legs, final base, and altitude using EPS.
2. For a trapezoid, compute the plane normal from one leg and the final base. The fourth point must lie within EPS of that plane. Check that the initial base is nonzero and at most the final base length, that its perpendicular component relative to the final base is below EPS, and that both bases point in the same direction. This last check rejects crossed legs.
3. Allocate a zeroed image with `ceil(leg length) + 1` rows and `ceil(final base length) + 1` columns. The first leg determines the row count when leg lengths differ within EPS. Treat lengths within `1e-9` above an integer as integral to absorb floating-point noise.
4. Use row fractions from 0 to 1 inclusive to interpolate each leg independently. For a row of width `d`, use `ceil(d) + 1` evenly spaced samples including the endpoints and cap the count at the image width. Center the samples with integer offset `(columns − count) // 2`. Odd padding puts the extra column on the right. For a collapsed apex the sole sample is the apex itself.
5. Check continuous bounds before rounding. Then use `floor(coordinate + 0.5)` to select the nearest voxel on each axis, with exact halfway ties toward the greater index. Temporarily clamp lookup indices for safe array access. Copy only values selected by both the footprint and volume masks.
6. For video, center the image on a canvas sized to fit all valid sections, with even dimensions for YUV 4:2:0. Error text reserves a minimum canvas of 480 × 160. The canvas applies no additional geometric scaling. Rows are based on leg travel, so the scan grid can shear or stretch an oblique polygon relative to an orthonormal view. Map nonzero values from the volume-wide minimum and maximum into grayscale 1–255, with constant nonzero values mapped to white. Zero and padding stay black.

Including both ends fixes the handout's skipped apex or initial base and the extra write on an integer-width final base. Interpolating normalized fractions avoids cumulative drift and prevents overshooting noninteger endpoints. A denominator of at least one handles the single-sample apex. Projection is linear in the output raster area and uses vectorized blocks with no Python loop over individual pixels. An axis that varies only by row uses a broadcast coordinate vector. When both base vectors match exactly, all rows have the same sample count, and axes that vary only by column can also use broadcast coordinate vectors.
