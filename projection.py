"""Plane geometry and nearest-voxel sampling in NRRD index coordinates."""

from dataclasses import dataclass

import numpy as np

EPS = 0.001


class PlaneError(ValueError):
    """An invalid plane specification."""


@dataclass(frozen=True)
class Plane:
    start_left: np.ndarray
    start_right: np.ndarray
    end_left: np.ndarray
    end_right: np.ndarray
    leg: float
    base: float
    top: float

    @property
    def shape(self):
        return sample_count(self.leg), sample_count(self.base)


def sample_count(length):
    # Include both ends and absorb floating-point noise at integral lengths.
    return int(np.ceil(length - 1e-9)) + 1


def validate_plane(points):
    """Accept (a,b,c) or (a1,a2,b,c) in the assignment's order."""
    try:
        points = np.asarray(points, dtype=np.float64)
    except (ValueError, TypeError) as exc:
        raise PlaneError("Coordinates must be numeric") from exc
    if points.shape not in ((3, 3), (4, 3)) or not np.isfinite(points).all():
        raise PlaneError("Expected three or four finite XYZ points")
    # A capacity limit also keeps arithmetic and canvas allocation bounded.
    if np.max(np.abs(points)) > 1e6:
        raise PlaneError("Coordinate magnitude exceeds 1,000,000")

    left, right, b, c = points if len(points) == 4 else points[[0, 0, 1, 2]]
    leg_left = b - left
    leg_right = c - right
    length = float(np.linalg.norm(leg_left))
    other = float(np.linalg.norm(leg_right))
    if min(length, other) <= EPS or abs(length - other) >= EPS:
        raise PlaneError("The two nonzero legs must have equal lengths within EPS")

    base_vector = c - b
    base = float(np.linalg.norm(base_vector))
    if base <= EPS:
        raise PlaneError("The final base has coincident endpoints")
    direction = base_vector / base
    normal = np.cross(direction, leg_left)
    height = np.linalg.norm(normal)
    if height <= EPS:
        raise PlaneError("The plane is degenerate or collinear")
    top_vector = right - left
    top = float(np.linalg.norm(top_vector))
    if len(points) == 4:
        if abs(np.dot(top_vector, normal / height)) >= EPS:
            raise PlaneError("Trapezoid points must be coplanar")
        if top <= EPS or top > base:
            raise PlaneError("The initial base must be nonzero and no longer than the final base")
        if np.linalg.norm(np.cross(top_vector, direction)) >= EPS:
            raise PlaneError("Trapezoid bases must be parallel")
        if np.dot(top_vector, direction) <= 0:
            raise PlaneError("Trapezoid legs cross; check the endpoint order")

    plane = Plane(left, right, b, c, length, base, top)
    if max(plane.shape) > 4096:
        raise PlaneError("Section exceeds the 4096-pixel limit per axis")
    return plane


def project(volume, plane, *, coverage=False):
    """Return a YX image with the same dtype as volume, indexed as volume[x,y,z].

    With coverage=True, also return the sampled positions inside the volume
    and the total positions inside the section footprint.
    """
    rows, columns = plane.shape
    t = np.linspace(0.0, 1.0, rows)[:, None]
    leg = plane.end_left - plane.start_left
    span = plane.end_right - plane.end_left
    start_span = plane.start_right - plane.start_left
    constant_width = np.array_equal(span, start_span)
    row_only = (span == 0) & (start_span == 0)
    left = plane.start_left + t * leg
    right = plane.start_right + t * (plane.end_right - plane.start_right)
    widths = np.linalg.norm(right - left, axis=1)
    counts = np.ceil(widths - 1e-9).astype(np.intp) + 1
    np.minimum(counts, columns, out=counts)
    offsets = (columns - counts) // 2
    image = np.zeros((rows, columns), dtype=volume.dtype)
    inside_count = 0
    # Bound the size of temporary arrays even for large sections.
    x = np.arange(columns)[None, :]
    block_rows = max(16, 131072 // columns)
    for start in range(0, rows, block_rows):
        stop = min(start + block_rows, rows)
        block = slice(start, stop)
        if constant_width:
            fraction = x / (columns - 1)
            valid = np.ones((stop - start, columns), dtype=bool)
        else:
            sample = x - offsets[block, None]
            last = counts[block, None] - 1
            fraction = sample / np.maximum(last, 1)
            valid = (sample >= 0) & (sample <= last)
        indices = []
        for axis, size in enumerate(volume.shape):
            origin = left[block, axis, None]
            if row_only[axis]:
                coordinate = origin
            elif constant_width and leg[axis] == 0:
                coordinate = origin[:1] + fraction * span[axis]
            else:
                delta = span[axis] if constant_width else right[block, axis, None] - origin
                coordinate = origin + fraction * delta
            valid &= (coordinate >= 0) & (coordinate <= size - 1)
            index = np.floor(coordinate + 0.5).astype(np.intp)
            np.clip(index, 0, size - 1, out=index)
            indices.append(index)
        np.copyto(image[block], volume[tuple(indices)], where=valid)
        if coverage:
            inside_count += np.count_nonzero(valid)
    if coverage:
        total = rows * columns if constant_width else int(counts.sum())
        return image, inside_count, total
    return image
