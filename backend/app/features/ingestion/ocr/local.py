import io
import threading
from dataclasses import replace
from pathlib import Path

import yaml
from PIL import Image

from app.common.extraction import TextLine
from app.common.normalization import clean_text
from app.features.ingestion.cache import (
    cached_read,
    file_identity,
    package_version,
    source_identity,
)
from app.features.ingestion.config import Settings
from app.features.ingestion.ocr.preprocessing import prepare_ocr_image

from .errors import ProviderUnavailable


class LocalOCR:
    """One lazily loaded CPU/CUDA session. Explicit local files; no request-time downloads."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.lock = threading.Lock()
        self.engine = None
        self.verifier = None
        self.engine_identity = None

    def signature(self):
        return {
            "primary": self._model_signature(self.settings.model_dir),
            "verification": self._model_signature(
                self.settings.verification_model_dir or self.settings.model_dir / "verify"
            ),
        }

    @staticmethod
    def _model_signature(directory):
        return {
            name: file_identity(directory / name)
            for name in (
                "manifest.json",
                "det/inference.onnx",
                "det/inference.yml",
                "rec/inference.onnx",
                "rec/keys.txt",
            )
        }

    def reader_signature(self):
        return {
            "models": self._model_signature(self.settings.model_dir),
            "implementation": source_identity(
                __file__,
                Path(__file__).with_name("preprocessing.py"),
                Path(__file__).resolve().parents[3] / "common/normalization.py",
                Path(__file__).resolve().parents[3] / "common/extraction.py",
            ),
            "runtime": {
                name: package_version(name)
                for name in (
                    "rapidocr",
                    "onnxruntime",
                    "onnxruntime-gpu",
                    "opencv-python",
                    "numpy",
                    "pillow",
                )
            },
            "cuda": self.settings.ocr_use_cuda,
        }

    def verify(self, png: bytes, page: int, point_size: tuple[float, float]):
        signatures = self.signature()
        primary = signatures["primary"]["rec/inference.onnx"]
        secondary = signatures["verification"]["rec/inference.onnx"]
        if primary is not None and primary == secondary:
            raise ProviderUnavailable("Verification requires different recognition weights")
        with self.lock:
            if self.verifier is None:
                self.verifier = LocalOCR(
                    replace(
                        self.settings,
                        model_dir=self.settings.verification_model_dir
                        or self.settings.model_dir / "verify",
                    )
                )
        lines = self.verifier.recognize(png, page, point_size)
        return [
            line.model_copy(update={"id": line.id.replace(":ocr:", ":ocr-verify:")})
            for line in lines
        ]

    def recognize(self, png: bytes, page: int, point_size: tuple[float, float]):
        import hashlib

        signature = self.reader_signature()
        identity = {
            "reader": signature,
            "image": hashlib.sha256(png).hexdigest(),
            "page": page,
            "point_size": list(point_size),
        }
        result = cached_read(
            self.settings.data_dir / "reader-cache" / "local",
            identity,
            lambda: [
                line.model_dump() for line in self._recognize(png, page, point_size, signature)
            ],
            validate=lambda values: [TextLine.model_validate(line).model_dump() for line in values],
            force=self.settings.ocr_force_recompute,
        )
        return [TextLine.model_validate(line) for line in result]

    def _recognize(self, png, page, point_size, signature):
        png, preprocessing, _ = prepare_ocr_image(png)
        # Remove blank margins before detector resizing. Sparse scans otherwise lose
        # small characters when an A4-sized canvas is downsampled. Keep coordinates.
        with Image.open(io.BytesIO(png)) as source:
            sx, sy = point_size[0] / source.width, point_size[1] / source.height
            ink = source.convert("L").point(lambda p: 255 if p < 180 else 0)
            bounds = ink.getbbox()
            if bounds:
                left, top, right, bottom = bounds
                left, top = max(0, left - 32), max(0, top - 32)
                right, bottom = min(source.width, right + 32), min(source.height, bottom + 32)
                prepared = source.crop((left, top, right, bottom))
            else:
                return []
            buffer = io.BytesIO()
            prepared.save(buffer, format="PNG")
        with self.lock:
            if self.engine is None or self.engine_identity != signature:
                self._load()
                self.engine_identity = signature
            result = self.engine(buffer.getvalue(), use_cls=False)
        if not result.txts:
            return []
        entries = []
        for box, text, confidence in zip(result.boxes, result.txts, result.scores, strict=True):
            x0, y0 = box.min(axis=0)
            x1, y1 = box.max(axis=0)
            x0, x1, y0, y1 = x0 + left, x1 + left, y0 + top, y1 + top
            entries.append(
                (
                    float(y0),
                    float(x0),
                    str(text),
                    float(confidence),
                    [float(x0) * sx, float(y0) * sy, float(x1) * sx, float(y1) * sy],
                )
            )
        entries.sort(key=lambda e: (e[0], e[1]))
        # Join boxes on the same baseline: OCR often separates labels and amounts.
        groups = []
        for item in entries:
            target = next(
                (
                    g
                    for g in reversed(groups[-3:])
                    if abs(g[0][0] - item[0]) * sy <= max(3, (item[4][3] - item[4][1]) * 0.45)
                ),
                None,
            )
            if target is None:
                groups.append([item])
            else:
                target.append(item)
        lines = []
        for index, group in enumerate(groups):
            group.sort(key=lambda e: e[1])
            text = "   ".join(e[2] for e in group)
            bbox = [
                min(e[4][0] for e in group),
                min(e[4][1] for e in group),
                max(e[4][2] for e in group),
                max(e[4][3] for e in group),
            ]
            lines.append(
                TextLine(
                    id=f"p{page}:ocr:{index}",
                    page=page,
                    raw=text,
                    text=clean_text(text),
                    bbox=bbox,
                    method="ocr",
                    confidence=min(e[3] for e in group),
                    preprocessing=preprocessing,
                )
            )
        return lines

    def _load(self):
        paths = {
            "Det.model_path": self.settings.model_dir / "det/inference.onnx",
            "Rec.model_path": self.settings.model_dir / "rec/inference.onnx",
            "Rec.rec_keys_path": self.settings.model_dir / "rec/keys.txt",
        }
        if any(not p.exists() for p in paths.values()):
            raise ProviderUnavailable(
                "OCR models missing; run python -m app.features.ingestion.tools.download_models"
            )
        import onnxruntime as ort
        from rapidocr import OCRVersion, RapidOCR

        if (
            self.settings.ocr_use_cuda
            and "CUDAExecutionProvider" not in ort.get_available_providers()
        ):
            raise ProviderUnavailable("CUDA requested but onnxruntime CUDA provider is unavailable")
        params = {key: str(path.resolve()) for key, path in paths.items()}
        metadata = yaml.safe_load(
            (self.settings.model_dir / "det/inference.yml").read_text(encoding="utf-8")
        )
        normalize = next(
            t["NormalizeImage"]
            for t in metadata["PreProcess"]["transform_ops"]
            if "NormalizeImage" in t
        )
        post = metadata["PostProcess"]
        version = (
            OCRVersion.PPOCRV6 if "v6" in metadata["Global"]["model_name"] else OCRVersion.PPOCRV5
        )
        params.update(
            {
                "Global.use_cls": False,
                "Global.log_level": "warning",
                "Global.max_side_len": 3400,
                "Det.ocr_version": version,
                "Rec.ocr_version": version,
                "Det.mean": normalize["mean"],
                "Det.std": normalize["std"],
                "Det.thresh": post["thresh"],
                "Det.box_thresh": post["box_thresh"],
                "Det.unclip_ratio": post["unclip_ratio"],
                "Det.limit_side_len": 2048,
                "Det.limit_type": "max",
                "Rec.rec_batch_num": 16,
                "EngineConfig.onnxruntime.intra_op_num_threads": self.settings.ocr_threads,
                "EngineConfig.onnxruntime.inter_op_num_threads": 1,
                "EngineConfig.onnxruntime.use_cuda": self.settings.ocr_use_cuda,
            }
        )
        self.engine = RapidOCR(params=params)
