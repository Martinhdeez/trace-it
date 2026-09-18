"""Download pinned small OCR weights from the official PaddlePaddle Hugging Face org."""

import argparse
import hashlib
import json
from pathlib import Path

import yaml
from huggingface_hub import hf_hub_download
from tracepay.ingestion.config import Settings

PROFILES = {
    "v6-small": {
        "det": ("PaddlePaddle/PP-OCRv6_small_det_onnx", "28fe5895c24fd108c19eb3e8479f4ab385fbfc62"),
        "rec": ("PaddlePaddle/PP-OCRv6_small_rec_onnx", "b8f84f0b80c529de40b4fbb3544b84fa7233a513"),
    },
    "v5-latin": {
        "det": ("PaddlePaddle/PP-OCRv5_mobile_det_onnx", "df0bd9dee2bc627e80a2a1798ccab35a332e22d6"),
        "rec": ("PaddlePaddle/latin_PP-OCRv5_mobile_rec_onnx", "89d3a50e2c27e2e7cceeab0e944c25c807d5db4f"),
    },
    "v5-server": {
        "det": ("PaddlePaddle/PP-OCRv5_mobile_det_onnx", "df0bd9dee2bc627e80a2a1798ccab35a332e22d6"),
        "rec": ("PaddlePaddle/PP-OCRv5_server_rec_onnx", "b70df217f4fd99d14f970bad092cebe7d74cc4d1"),
    },
}


def download(profile, target):
    manifest = {}
    for role, (repo, revision) in PROFILES[profile].items():
        directory = target / role
        for filename in ("inference.onnx", "inference.yml"):
            hf_hub_download(repo, filename, revision=revision, local_dir=directory)
        manifest[role] = {
            "repo": repo,
            "revision": revision,
            "sha256": hashlib.sha256((directory / "inference.onnx").read_bytes()).hexdigest(),
        }
    metadata = yaml.safe_load((target / "rec/inference.yml").read_text(encoding="utf-8"))
    characters = metadata["PostProcess"]["character_dict"]
    (target / "rec/keys.txt").write_text("\n".join(characters) + "\n", encoding="utf-8")
    manifest["keys_sha256"] = hashlib.sha256((target / "rec/keys.txt").read_bytes()).hexdigest()
    (target / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", choices=PROFILES, default="v5-latin")
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--no-verifier", action="store_true", help="Download only the candidate profile for experiments"
    )
    args = parser.parse_args()
    target = args.output or Settings().model_dir
    manifest = download(args.profile, target)
    if not args.no_verifier:
        manifest["verification"] = download("v5-server", target / "verify")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
