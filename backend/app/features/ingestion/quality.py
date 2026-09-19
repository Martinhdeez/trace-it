"""Pin the evaluated OCR committee; experiments require an explicit opt-out."""

from app.features.ingestion.cache import file_identity
from app.features.ingestion.config import Settings

# Hashes of the weights and dictionaries used in the evaluated Latin/server committee.
MODEL_FILES = {
    "det/inference.yml": "98069072e1b6b37d727fd9d9f11725faa46d6ea0de012f2ed26caea011c37699",
    "det/inference.onnx": "a431985659dc921974177a95adcfbb90fd9e51989a5e04d70d0b75f597b6e61d",
    "rec/inference.onnx": "7888113072263cb471b93f66dd5e2ad70548dc526fa1ace760d0d973dd121498",
    "rec/keys.txt": "5ddc5c6086d61db3e1485f1237e059b89df9a228cebdac40a54406c6005bca67",
    "verify/det/inference.onnx": "a431985659dc921974177a95adcfbb90fd9e51989a5e04d70d0b75f597b6e61d",
    "verify/det/inference.yml": "98069072e1b6b37d727fd9d9f11725faa46d6ea0de012f2ed26caea011c37699",
    "verify/rec/inference.onnx": "d9dc333c9c7b042c6dffb8e33d72b6f65c9c1d463d0a3c2f78174fea55e94752",
    "verify/rec/keys.txt": "1ea29636956177e400af712d9782e7693f3fb25f98617bed10479d2965a836fd",
}
VISUAL_MODEL = "gemini-3.1-flash-lite"
JUDGE_MODEL = "jev-1.13.0"


def validate_quality_profile(settings: Settings) -> dict:
    """Fail before serving requests if the default committee is incomplete or changed.

    This verifies configuration and local bytes, not remote availability or accuracy.
    Provider failures during extraction still preserve uncertainty and evidence.
    """
    if settings.ocr_profile == "experimental":
        return {"profile": "experimental", "verified": False}
    problems = []
    hashes = {}
    for name, expected in MODEL_FILES.items():
        hashes[name] = file_identity(settings.model_dir / name)
        if hashes[name] != expected:
            problems.append(f"missing or different OCR file: {name}")
    if settings.vlm_url and settings.vlm_model:
        problems.append("custom visual providers require the experimental profile")
    if settings.gemini_model != VISUAL_MODEL or not settings.gemini_api_key:
        problems.append(f"configure GEMINI_API_KEY and TRACEPAY_GEMINI_MODEL={VISUAL_MODEL}")
    if settings.jev_model != JUDGE_MODEL or not settings.jev_api_key:
        problems.append(f"configure TYPESAFE_API_KEY and TRACEPAY_JEV_MODEL={JUDGE_MODEL}")
    if problems:
        raise RuntimeError(
            "Verified OCR profile is unavailable: "
            + "; ".join(problems)
            + ". See docs/ingestion/setup.md. For explicit local-only experiments, set "
            "TRACEPAY_OCR_PROFILE=experimental."
        )
    return {
        "profile": "verified",
        "verified": True,
        "model_sha256": hashes,
        "visual_model": VISUAL_MODEL,
        "text_judge_model": JUDGE_MODEL,
    }


if __name__ == "__main__":
    import json

    print(json.dumps(validate_quality_profile(Settings()), indent=2))
