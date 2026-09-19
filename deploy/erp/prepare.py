"""Prepare a reviewable ERP installation bundle from the pinned challenge submodule."""

import argparse
import hashlib
import shutil
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--update", type=Path, help="Reviewed incremental ERP CSV")
    parser.add_argument(
        "--workbook", type=Path, help="Reviewed cumulative reference workbook"
    )
    args = parser.parse_args()
    here = Path(__file__).resolve().parent
    challenge = here.parents[1] / ".context/500-sombras-de-alberto"
    files = {
        name: here / name
        for name in (
            "Dockerfile",
            "compose.yml",
            "compose.update.yml",
            "server.py",
            "install.sh",
            "bootstrap_sources.py",
            "switch_reader.py",
            "README.md",
        )
    }
    files.update(
        {
            "alberto_erp.py": challenge / "alberto_erp.py",
            "reference.xlsx": args.workbook
            or challenge / "FINAL_v7_DEFINITIVO_ahorasi.xlsx",
            "activate-route.py": here.parent / "activate-route.py",
        }
    )
    if args.update:
        files["erp_export_lote2.csv"] = args.update
    if any(not path.is_file() for path in files.values()):
        parser.error(
            "Initialize the pinned challenge submodule before preparing the bundle"
        )
    args.output.mkdir(parents=True, exist_ok=False)
    hashes = []
    for name, source in files.items():
        target = args.output / name
        shutil.copyfile(source, target)
        hashes.append(f"{hashlib.sha256(target.read_bytes()).hexdigest()}  {name}\n")
    (args.output / "SHA256SUMS").write_text("".join(hashes), encoding="ascii")
    print(args.output.resolve())


if __name__ == "__main__":
    main()
