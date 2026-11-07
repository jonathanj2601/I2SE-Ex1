"""Render fixed-size grayscale frames and encode a transactional MP4."""

from pathlib import Path
import subprocess
from tempfile import NamedTemporaryFile, TemporaryFile
import textwrap

import imageio_ffmpeg
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from projection import project

PLAYBACK_FPS = 2


def canvas_shape(records):
    shapes = [record.plane.shape for record in records if record.plane is not None]
    height = max((shape[0] for shape in shapes), default=2)
    width = max((shape[1] for shape in shapes), default=2)
    if any(record.plane is None for record in records):
        height, width = max(height, 160), max(width, 480)
    return height + height % 2, width + width % 2


def error_frame(shape, line, error):
    image = Image.new("L", shape[::-1])
    draw = ImageDraw.Draw(image)
    draw.rectangle((5, 5, shape[1] - 6, shape[0] - 6), outline=220, width=2)
    font = ImageFont.load_default(size=20)
    detail = textwrap.fill(error, width=36, max_lines=3, placeholder="...")
    draw.multiline_text((16, 16), f"ERROR - CSV LINE {line}\n{detail}",
                        fill=255, font=font, spacing=5)
    return np.asarray(image)


def render_frame(section, shape, low, high):
    image = np.zeros(shape, dtype=np.uint8)
    height, width = section.shape
    y, x = (shape[0] - height) // 2, (shape[1] - width) // 2
    target = image[y:y + height, x:x + width]
    nonzero = section != 0
    if high == low:
        target[nonzero] = 255
    else:
        scaled = (section[nonzero].astype(np.float64) - low) * (254 / (high - low))
        target[nonzero] = np.rint(scaled).astype(np.uint8) + 1
    return image


def write_demo(volume, records, output):
    """Write one frame per record and return coverage counts in CSV order."""
    output = Path(output)
    if output.suffix.lower() != ".mp4":
        raise ValueError("Output filename must end in .mp4")
    shape = canvas_shape(records)
    low, high = int(volume.min()), int(volume.max())
    counts = []
    with NamedTemporaryFile(dir=output.parent, suffix=".mp4", delete=False) as temp:
        pending = Path(temp.name)
    try:
        command = [
            imageio_ffmpeg.get_ffmpeg_exe(), "-hide_banner", "-loglevel", "error",
            "-y", "-f", "rawvideo", "-pixel_format", "gray",
            "-video_size", f"{shape[1]}x{shape[0]}", "-framerate", str(PLAYBACK_FPS),
            "-i", "pipe:0", "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-movflags", "+faststart", str(pending),
        ]
        with TemporaryFile() as errors, subprocess.Popen(
            command, stdin=subprocess.PIPE, stderr=errors
        ) as encoder:
            broken_pipe = None
            try:
                with encoder.stdin as stream:
                    for record in records:
                        if record.plane is None:
                            frame = error_frame(shape, record.line, record.error)
                            counts.append((0, 0))
                        else:
                            section, inside, total = project(volume, record.plane, coverage=True)
                            frame = render_frame(section, shape, low, high)
                            counts.append((inside, total))
                        stream.write(frame.tobytes())
            except BrokenPipeError as exc:
                broken_pipe = exc
            if encoder.wait() or broken_pipe is not None:
                errors.seek(0)
                detail = errors.read().decode(errors="replace").strip()
                raise RuntimeError(f"FFmpeg could not encode the video: {detail}") from broken_pipe
        pending.replace(output)
    finally:
        pending.unlink(missing_ok=True)
    return counts
