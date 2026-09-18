"""Conservative, coordinate-preserving corrections for measured scanning defects."""

import io

import cv2
import numpy as np
from PIL import Image

# ONNX already owns a bounded thread pool. Prevent a second 32-thread OpenCV
# pool from multiplying threads for the many small detector/recognizer crops.
cv2.setNumThreads(1)


def prepare_ocr_image(png: bytes):
    with Image.open(io.BytesIO(png)) as source:
        gray = np.array(source.convert("L"))
    thumbnail = cv2.resize(gray, (496, 702)).astype(np.float32)
    column = np.median(thumbnail, axis=0).reshape(-1, 1)
    row = np.median(thumbnail, axis=1).reshape(-1, 1)
    vertical = float(np.std(column - cv2.GaussianBlur(column, (1, 31), 0)))
    horizontal = float(np.std(row - cv2.GaussianBlur(row, (1, 31), 0)))
    paper = cv2.morphologyEx(thumbnail, cv2.MORPH_CLOSE, np.ones((15, 15), np.uint8))
    dark_paper_ratio = float(np.mean(paper < 190))
    stats = {
        "vertical_stripe_score": round(vertical, 3),
        "horizontal_band_score": round(horizontal, 3),
        "dark_paper_ratio": round(dark_paper_ratio, 4),
    }
    operations = []
    # Require strong defects, so ordinary text and mild background noise keep
    # their original pixels. These thresholds are development heuristics.
    if vertical > 10 and vertical > 3 * horizontal:
        background = np.median(gray, axis=0)[None, :]
        gray = np.clip(gray.astype(np.float32) + 255 - background, 0, 255).astype(np.uint8)
        operations.append("vertical_background_subtraction")
    elif horizontal > 25 and horizontal > 3 * vertical:
        background = np.median(gray, axis=1)[:, None]
        gray = np.clip(gray.astype(np.float32) + 255 - background, 0, 255).astype(np.uint8)
        operations.append("horizontal_background_subtraction")
    elif dark_paper_ratio > 0.15:
        background = cv2.morphologyEx(gray, cv2.MORPH_CLOSE, np.ones((45, 45), np.uint8))
        gray = cv2.divide(gray, np.maximum(background, 1), scale=255)
        operations.append("local_illumination_normalization")
    if not operations:
        return png, operations, stats
    stream = io.BytesIO()
    Image.fromarray(gray).convert("RGB").save(stream, format="PNG")
    return stream.getvalue(), operations, stats
