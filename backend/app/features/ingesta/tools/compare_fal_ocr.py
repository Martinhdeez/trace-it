"""Explicit paid GOT-OCR experiment; cached requests avoid repeated charges."""

import argparse
import asyncio
import base64
import hashlib
import io
import json
import time
from pathlib import Path

import fal_client
from dotenv import load_dotenv
from PIL import Image

from app.features.ingesta.config import REPOSITORY_ROOT, Settings
from app.features.ingesta.ocr.preprocessing import prepare_ocr_image
from app.features.ingesta.ocr.transcript import remote_lines, transcript_warnings
from app.features.ingesta.pdf.invoice import parse_invoice
from app.features.ingesta.pdf.native import native_pages, render
from app.features.ingesta.tools.evaluate_scans import compare

MODEL = "fal-ai/got-ocr/v2"


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--files",
        nargs="+",
        default=["scan_021.pdf", "scan_022.pdf", "scan_023.pdf", "scan_025.pdf", "scan_026.pdf"],
    )
    parser.add_argument("--output", type=Path, default=Path("reports/fal-got"))
    parser.add_argument(
        "--input-images",
        type=Path,
        help="Optional directory of file.pdf.png images for a separately identified experiment",
    )
    parser.add_argument("--crop-to-local-evidence", action="store_true")
    parser.add_argument("--formatted", action="store_true")
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Re-evaluate saved responses without network requests",
    )
    parser.add_argument(
        "--local-extractions",
        type=Path,
        help="Local extraction JSONL; required only for evidence crops",
    )
    args = parser.parse_args()
    if args.crop_to_local_evidence and not args.offline and args.local_extractions is None:
        parser.error("--crop-to-local-evidence requires --local-extractions")
    load_dotenv(REPOSITORY_ROOT / ".env")
    args.output.mkdir(parents=True, exist_ok=True)
    refs = {
        r["file_id"]: r
        for r in json.loads(
            (Path(__file__).resolve().parents[1] / "tests/fixtures/scans-reviewed.json").read_text(
                encoding="utf-8"
            )
        )
    }
    local = {
        r["file_id"]: r
        for r in map(
            json.loads,
            args.local_extractions.read_text(encoding="utf-8").splitlines()
            if args.local_extractions
            else [],
        )
    }
    reports = []
    for name in args.files:
        content = (
            (REPOSITORY_ROOT / ".context/500-sombras-de-alberto/facturas") / name
        ).read_bytes()
        size = native_pages(content, Settings())[0]["size"]
        png = (
            (args.output / (name + ".input.png")).read_bytes()
            if args.offline
            else (
                (args.input_images / (name + ".png")).read_bytes()
                if args.input_images
                else render(content, 1, Settings())
            )
        )
        if args.crop_to_local_evidence and not args.offline:
            png, _, _ = prepare_ocr_image(png)
            boxes = [
                c["evidence"]["bbox"]
                for f in local[name]["fields"].values()
                for c in f["candidates"]
                if c["evidence"].get("bbox")
            ]
            if boxes:
                with Image.open(io.BytesIO(png)) as image:
                    sx, sy = image.width / size[0], image.height / size[1]
                    box = (
                        max(0, int(min(b[0] for b in boxes) * sx) - 48),
                        max(0, int(min(b[1] for b in boxes) * sy) - 64),
                        min(image.width, int(max(b[2] for b in boxes) * sx) + 48),
                        min(image.height, int(max(b[3] for b in boxes) * sy) + 64),
                    )
                    stream = io.BytesIO()
                    image.crop(box).save(stream, format="PNG")
                    png = stream.getvalue()
        (args.output / (name + ".input.png")).write_bytes(png)
        fingerprint = hashlib.sha256(png).hexdigest()
        destination = args.output / (name + ".response.json")
        if destination.exists():
            response = json.loads(destination.read_text(encoding="utf-8"))
            if (
                response["input_sha256"] != fingerprint
                or response.get("do_format", False) != args.formatted
            ):
                raise ValueError("Use a new output directory for changed inputs")
            print(name, "cached", flush=True)
        else:
            if args.offline:
                raise ValueError(
                    f"No saved response for {name}; offline mode cannot submit requests"
                )
            started = time.perf_counter()
            request_file = args.output / (name + ".request.json")
            if request_file.exists():
                pending = json.loads(request_file.read_text(encoding="utf-8"))
                if (
                    pending["input_sha256"] != fingerprint
                    or pending.get("do_format", False) != args.formatted
                ):
                    raise ValueError("Pending request belongs to another image")
                request_id = pending["request_id"]
                print(name, "resuming", request_id, flush=True)
            else:
                print(name, "submitting", flush=True)
                handle = await fal_client.submit_async(
                    MODEL,
                    arguments={
                        "input_image_urls": [
                            "data:image/png;base64," + base64.b64encode(png).decode()
                        ],
                        "do_format": args.formatted,
                        "multi_page": False,
                    },
                )
                request_id = handle.request_id
                request_file.write_text(
                    json.dumps(
                        {
                            "model": MODEL,
                            "request_id": request_id,
                            "input_sha256": fingerprint,
                            "do_format": args.formatted,
                        }
                    ),
                    encoding="utf-8",
                )
                print(name, "request", request_id, flush=True)

            async def retrieve(request_id=request_id):
                while not isinstance(
                    await fal_client.status_async(MODEL, request_id), fal_client.Completed
                ):
                    await asyncio.sleep(1)
                return await fal_client.result_async(MODEL, request_id)

            result = await asyncio.wait_for(retrieve(), timeout=180)
            response = {
                "model": MODEL,
                "request_id": request_id,
                "input_sha256": fingerprint,
                "do_format": args.formatted,
                "seconds": round(time.perf_counter() - started, 3),
                "result": result,
            }
            destination.write_text(
                json.dumps(response, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        outputs = response["result"]["outputs"]
        if not isinstance(outputs, list) or not all(isinstance(s, str) for s in outputs):
            raise ValueError("Unexpected GOT output schema")
        transcript = "\n".join(outputs)
        (args.output / (name + ".txt")).write_text(transcript, encoding="utf-8")
        lines = remote_lines(transcript, 1, size)
        fields, warnings = parse_invoice(lines)
        warnings.extend(transcript_warnings(transcript))
        result = {"file_id": name, "fields": {k: v.model_dump() for k, v in fields.items()}}
        compared = compare(result, refs[name])
        local_comparison = compare(local[name], refs[name]) if name in local else None
        report = {
            "file_id": name,
            "seconds": response["seconds"],
            "model": MODEL,
            "request_id": response["request_id"],
            "fields": result["fields"],
            "warnings": warnings,
            "comparison": compared,
            "local_comparison": local_comparison,
        }
        reports.append(report)
        print(
            name,
            "fal_matches",
            sum(c["matches"] for c in compared["checks"].values()),
            "local_matches",
            sum(c["matches"] for c in local_comparison["checks"].values())
            if local_comparison
            else None,
            "seconds",
            response["seconds"],
            flush=True,
        )
    (args.output / "comparison.json").write_text(
        json.dumps(reports, ensure_ascii=False, indent=2), encoding="utf-8"
    )


if __name__ == "__main__":
    asyncio.run(main())
