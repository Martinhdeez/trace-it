"""Compare deterministic image preprocessing against visual development labels."""

import argparse
import io
import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from app.features.ingesta.config import REPOSITORY_ROOT, Settings
from app.features.ingesta.ocr.local import LocalOCR
from app.features.ingesta.pdf.invoice import parse_invoice
from app.features.ingesta.pdf.native import native_pages, render
from app.features.ingesta.tools.evaluate_scans import compare


def variants(png):
    gray = np.array(Image.open(io.BytesIO(png)).convert("L"))
    # Closing estimates local paper brightness without filling in document text.
    background = cv2.morphologyEx(gray, cv2.MORPH_CLOSE, np.ones((45, 45), np.uint8))
    flat = cv2.divide(gray, np.maximum(background, 1), scale=255)
    column = np.median(gray, axis=0).astype(np.float32)
    vertical = np.clip(gray.astype(np.float32) + 255 - column[None, :], 0, 255).astype(np.uint8)
    row = np.median(gray, axis=1).astype(np.float32)
    horizontal = np.clip(gray.astype(np.float32) + 255 - row[:, None], 0, 255).astype(np.uint8)
    return {
        "original": gray,
        "flat": flat,
        "flat_threshold": cv2.threshold(flat, 160, 255, cv2.THRESH_BINARY)[1],
        "threshold": cv2.threshold(gray, 115, 255, cv2.THRESH_BINARY)[1],
        "vertical": vertical,
        "horizontal": horizontal,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--files",
        nargs="+",
        default=["scan_021.pdf", "scan_022.pdf", "scan_023.pdf", "scan_025.pdf", "scan_026.pdf"],
    )
    parser.add_argument("--output", type=Path, default=Path("reports/preprocessing"))
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    settings = Settings()
    engine = LocalOCR(settings)
    refs = {
        r["file_id"]: r
        for r in json.loads(
            (Path(__file__).resolve().parents[1] / "tests/fixtures/scans-reviewed.json").read_text(
                encoding="utf-8"
            )
        )
    }
    reports = []
    for name in args.files:
        content = ((REPOSITORY_ROOT / ".context/500-sombras-de-alberto/facturas") / name).read_bytes()
        size = native_pages(content, settings)[0]["size"]
        for variant, pixels in variants(render(content, 1, settings)).items():
            stream = io.BytesIO()
            Image.fromarray(pixels).convert("RGB").save(stream, format="PNG")
            lines = engine.recognize(stream.getvalue(), 1, size)
            fields, warnings = parse_invoice(lines)
            result = {
                "file_id": name,
                "variant": variant,
                "fields": {k: v.model_dump() for k, v in fields.items()},
                "warnings": warnings,
                "lines": [line.model_dump() for line in lines],
            }
            comparison = compare(result, refs[name])
            result["comparison"] = comparison
            reports.append(result)
            checks = comparison["checks"].values()
            print(
                name,
                variant,
                "match",
                sum(c["matches"] for c in checks),
                "wrong",
                [
                    (k, c["value"])
                    for k, c in comparison["checks"].items()
                    if not c["matches"] and c["value"] is not None
                ],
                flush=True,
            )
            (args.output / (name + "." + variant + ".png")).write_bytes(stream.getvalue())
    (args.output / "results.json").write_text(
        json.dumps(reports, ensure_ascii=False, indent=2), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
