"""Recover measurable column displacement from coherent periodic scanner bands."""

import io

import cv2
import numpy as np
from PIL import Image


def flatten_periodic_bands(png):
    with Image.open(io.BytesIO(png)) as source:
        source = source.convert("L")
        source.thumbnail((3000, 3000))
        gray = np.array(source)
    height, width = gray.shape
    if height < 200 or width < 200:
        return None
    sample = gray[int(height * 0.45) : int(height * 0.85)].astype(np.float32)
    sample -= sample.mean(axis=0)
    spectrum = np.fft.rfft(sample, axis=0)
    frequency = np.fft.rfftfreq(sample.shape[0])
    power = np.median(abs(spectrum) ** 2, axis=1)
    total = power.sum()
    power[(frequency < 0.03) | (frequency > 0.3)] = 0
    peak = int(np.argmax(power))
    if total <= 0 or power[peak] / total < 0.2:
        return None
    phase = np.unwrap(np.angle(spectrum[peak]))
    shift = -(phase - phase[0]) / (2 * np.pi * frequency[peak])
    amplitude = float(np.ptp(shift))
    if not 2 < amplitude < height * 0.08 or np.quantile(abs(np.diff(shift)), 0.99) > 1.5:
        return None
    # Only resample existing pixels; the transform knows no labels or identifiers.
    map_x = np.broadcast_to(np.arange(width, dtype=np.float32), (height, width))
    map_y = np.arange(height, dtype=np.float32)[:, None] + shift.astype(np.float32)
    corrected = cv2.remap(
        gray, map_x, map_y, cv2.INTER_CUBIC, borderMode=cv2.BORDER_CONSTANT, borderValue=255
    )
    stream = io.BytesIO()
    Image.fromarray(corrected).convert("RGB").save(stream, format="PNG")
    return stream.getvalue(), {
        "operation": "periodic_band_dewarp",
        "peak_fraction": float(power[peak] / total),
        "max_displacement_px": amplitude,
        "frequency": float(frequency[peak]),
    }
