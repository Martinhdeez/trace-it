"""Compare explicit Gemini calls with provisional scan references, without answer leakage."""

import argparse
import hashlib
import json
import os
import time
from pathlib import Path

import httpx
from dotenv import load_dotenv

from app.features.ingestion.config import REPOSITORY_ROOT, Settings
from app.features.ingestion.ocr.errors import ProviderUnavailable
from app.features.ingestion.ocr.gemini import GENERATION, PROMPT, generate, output_text
from app.features.ingestion.ocr.preprocessing import prepare_ocr_image
from app.features.ingestion.ocr.transcript import remote_lines, transcript_warnings
from app.features.ingestion.pdf.invoice import parse_invoice
from app.features.ingestion.pdf.native import native_pages, render
from app.features.ingestion.tools.evaluate_scans import compare

FILES = [f"scan_{number:03}.pdf" for number in (21, 22, 23, 25, 26)]


def cached_call(client, model, key, images, path, offline):
    identity = {
        "model": model,
        "prompt": PROMPT,
        "generation": GENERATION,
        "images": [hashlib.sha256(image).hexdigest() for image in images],
    }
    fingerprint = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
    record_path = path / f"{fingerprint}.json"
    if record_path.exists():
        record = json.loads(record_path.read_text(encoding="utf-8"))
        if record["state"] != "complete":
            raise RuntimeError(
                "Previous attempt incomplete; inspect its journal before resubmitting"
            )
        return record
    if offline:
        raise FileNotFoundError(
            "No cached Gemini response for this image/prompt/model configuration"
        )
    if not key:
        raise ValueError("Set GEMINI_API_KEY in the repository .env")
    record = {"identity": identity, "state": "started", "started_at": time.time()}
    record_path.write_text(json.dumps(record, indent=2), encoding="utf-8")
    started = time.perf_counter()
    try:
        record["response"] = generate(client, model, key, images)
        record["state"] = "complete"
    except Exception as error:
        # A timeout does not prove the server stopped. Never retry automatically.
        record.update(state="uncertain_or_failed", error_type=type(error).__name__)
        if isinstance(error, ProviderUnavailable):
            record["provider_error"] = str(error)
        raise
    finally:
        record["seconds"] = round(time.perf_counter() - started, 3)
        record_path.write_text(json.dumps(record, indent=2), encoding="utf-8")
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True)
    parser.add_argument("--files", nargs="+", default=FILES)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--input-images", type=Path, help="Directory of file.pdf.png region images")
    parser.add_argument("--preprocessed", action="store_true")
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    load_dotenv(REPOSITORY_ROOT / ".env")
    labels = Path(__file__).resolve().parents[1] / "tests/fixtures/scans-reviewed.json"
    references = {r["file_id"]: r for r in json.loads(labels.read_text(encoding="utf-8"))}
    reports = []
    with httpx.Client(timeout=120, follow_redirects=False) as client:
        for name in args.files:
            content = (
                REPOSITORY_ROOT / ".context/500-sombras-de-alberto/facturas" / name
            ).read_bytes()
            if hashlib.sha256(content).hexdigest() != references[name]["sha256"]:
                raise ValueError(f"Reference does not match source: {name}")
            size = native_pages(content, Settings())[0]["size"]
            image = (
                (args.input_images / f"{name}.png").read_bytes()
                if args.input_images
                else render(content, 1, Settings())
            )
            transforms = []
            if args.preprocessed:
                image, transforms, _ = prepare_ocr_image(image)
            (args.output / f"{name}.input.png").write_bytes(image)
            record = cached_call(
                client, args.model, os.getenv("GEMINI_API_KEY"), [image], args.output, args.offline
            )
            response = record["response"]
            transcript = output_text(response)
            (args.output / f"{name}.txt").write_text(transcript, encoding="utf-8")
            lines = remote_lines(transcript, 1, size)
            if args.input_images:
                # The experiment may use manually cropped images. Do not fabricate PDF coordinates.
                for line in lines:
                    line.bbox = []
            fields, warnings = parse_invoice(lines)
            warnings.extend(transcript_warnings(transcript))
            result = {"file_id": name, "fields": {k: v.model_dump() for k, v in fields.items()}}
            comparison = compare(result, references[name])
            checks = list(comparison["checks"].values())
            report = {
                **result,
                "comparison": comparison,
                "warnings": warnings,
                "image_sha256": record["identity"]["images"][0],
                "preprocessing": transforms,
                "input_kind": "external_region" if args.input_images else "full_page",
                "model": args.model,
                "model_version": response.get("modelVersion"),
                "response_id": response.get("responseId"),
                "usage": response.get("usageMetadata", {}),
                "seconds": record["seconds"],
                "matching_values": sum(c["matches"] for c in checks),
                "wrong_nonnull_values": sum(
                    not c["matches"] and c["value"] is not None for c in checks
                ),
            }
            reports.append(report)
            (args.output / "comparison.json").write_text(
                json.dumps(reports, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            print(name, report["matching_values"], "/", len(checks), record["seconds"], flush=True)


if __name__ == "__main__":
    main()
