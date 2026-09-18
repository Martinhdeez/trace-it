import io

import numpy as np
from PIL import Image, ImageDraw
from tracepay.ingestion.ocr.preprocessing import prepare_ocr_image


def png(image):
    stream = io.BytesIO()
    image.save(stream, format="PNG")
    return stream.getvalue()


def test_clean_document_keeps_original_bytes():
    image = Image.new("L", (800, 1100), 255)
    ImageDraw.Draw(image).text((60, 80), "NIF B12345678  TOTAL 121.00 EUR", fill=0)
    source = png(image)
    prepared, operations, _ = prepare_ocr_image(source)
    assert prepared == source
    assert operations == []


def test_vertical_noise_removal_preserves_geometry_and_dark_text():
    data = np.full((1100, 800), 240, dtype=np.uint8)
    data[:, ::4] = 130
    data[100:130, 80:120] = 0
    prepared, operations, _ = prepare_ocr_image(png(Image.fromarray(data)))
    image = Image.open(io.BytesIO(prepared)).convert("L")
    assert operations == ["vertical_background_subtraction"]
    assert image.size == (800, 1100)
    assert image.getpixel((90, 115)) < 140
    assert image.getpixel((400, 500)) == 255


def test_large_shadow_normalizes_brightness_without_moving_text():
    background = np.linspace(60, 230, 800).astype(np.uint8)
    data = np.tile(background, (1100, 1))
    data[100:110, 80:100] = 0
    prepared, operations, _ = prepare_ocr_image(png(Image.fromarray(data)))
    image = Image.open(io.BytesIO(prepared)).convert("L")
    assert operations == ["local_illumination_normalization"]
    assert image.size == (800, 1100)
    assert image.getpixel((85, 105)) == 0
    assert image.getpixel((400, 500)) > 245
