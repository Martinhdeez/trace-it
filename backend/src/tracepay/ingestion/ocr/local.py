import io
import json
import threading
from dataclasses import replace

import yaml
from PIL import Image

from tracepay.ingestion.config import Settings
from tracepay.ingestion.models import TextLine
from tracepay.ingestion.normalize import clean_text
from tracepay.ingestion.ocr.preprocessing import prepare_ocr_image

from .errors import ProviderUnavailable


class LocalOCR:
    """One lazily loaded CPU/CUDA session. Explicit local files; no request-time downloads."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.lock = threading.Lock()
        self.engine = None
        self.verifier = None

    def signature(self):
        manifest = self.settings.model_dir / "manifest.json"
        signature = json.loads(manifest.read_text()) if manifest.exists() else {"available": False}
        verification = self.settings.model_dir / "verify/manifest.json"
        signature["verification"] = (
            json.loads(verification.read_text()) if verification.exists() else {"available": False}
        )
        return signature

    def verify(self, png: bytes, page: int, point_size: tuple[float, float]):
        with self.lock:
            if self.verifier is None:
                self.verifier = LocalOCR(replace(self.settings, model_dir=self.settings.model_dir / "verify"))
        lines = self.verifier.recognize(png, page, point_size)
        return [line.model_copy(update={"id": line.id.replace(":ocr:", ":ocr-verify:")}) for line in lines]

    def recognize(self, png: bytes, page: int, point_size: tuple[float, float]):
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
            if self.engine is None:
                self._load()
            result = self.engine(buffer.getvalue(), use_cls=False)
        if not result.txts:
            return []
        entries = []
        for box, text, confidence in zip(result.boxes, result.txts, result.scores):
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
            raise ProviderUnavailable("OCR models missing; run python -m scripts.ingestion.download_models")
        import onnxruntime as ort
        from rapidocr import OCRVersion, RapidOCR

        if self.settings.ocr_use_cuda and "CUDAExecutionProvider" not in ort.get_available_providers():
            raise ProviderUnavailable("CUDA requested but onnxruntime CUDA provider is unavailable")
        params = {key: str(path.resolve()) for key, path in paths.items()}
        metadata = yaml.safe_load((self.settings.model_dir / "det/inference.yml").read_text(encoding="utf-8"))
        normalize = next(
            t["NormalizeImage"] for t in metadata["PreProcess"]["transform_ops"] if "NormalizeImage" in t
        )
        post = metadata["PostProcess"]
        version = OCRVersion.PPOCRV6 if "v6" in metadata["Global"]["model_name"] else OCRVersion.PPOCRV5
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
