"""Build a source-and-evidence ZIP without third-party footage or frame images."""

from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "DELIVERABLES/HONOURS_VOLLEY_ANALYTICS_REVIEW_PACKAGE_2026-11-11.zip"
PRIMARY = ROOT / "data/matches/yt_u5HnY2aNW14"
CODE_SUFFIXES = {".py", ".html", ".js", ".css", ".yaml", ".yml", ".toml"}
DATA_SUFFIXES = {".json", ".csv", ".md"}


def sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def main() -> None:
    files: set[Path] = {ROOT / name for name in
                        ("README.md", "requirements.txt", "requirements-research.txt")}
    for folder in ("scripts", "src", "services", "web", "tests"):
        for path in (ROOT / folder).rglob("*"):
            if path.is_file() and path.suffix.lower() in CODE_SUFFIXES and "__pycache__" not in path.parts:
                files.add(path)
    for path in (ROOT / "annotations").rglob("*"):
        if path.is_file() and path.suffix.lower() in DATA_SUFFIXES:
            files.add(path)
    for path in (ROOT / "DELIVERABLES").glob("*.md"):
        files.add(path)
    for name in ("HONOURS_SHAREABLE_RESEARCH_HANDOFF_2026-11-11.pdf",
                 "HONOURS_U5_THESIS_PRINT_PREVIEW.pdf"):
        files.add(ROOT / "DELIVERABLES" / name)
    for path in (ROOT / "DELIVERABLES/figures").rglob("*"):
        if path.is_file() and path.suffix.lower() in {".png", ".pdf"}:
            files.add(path)
    files.add(PRIMARY / "primary_source_manifest.json")
    for path in (PRIMARY / "screening").rglob("*"):
        if path.is_file() and path.suffix.lower() in DATA_SUFFIXES:
            files.add(path)
    assert all(path.exists() and path.is_file() and path.resolve().is_relative_to(ROOT.resolve()) for path in files)
    forbidden = {".mp4", ".mov", ".jpg", ".jpeg", ".webp", ".pt", ".onnx"}
    assert not any(path.suffix.lower() in forbidden for path in files)
    assert ROOT / "DELIVERABLES/figures/u5_s3p34_reported_live_geometry.png" in files
    readme = (
        "# Honours volleyball analytics review package\n\n"
        "Open `DELIVERABLES/HONOURS_SHAREABLE_RESEARCH_HANDOFF_2026-11-11.pdf` first. "
        "Its editable Markdown version is beside it. The thesis draft and print preview are included.\n\n"
        "This is a source-code and numerical-evidence snapshot. It omits raw match videos, "
        "identifiable source frames, contact sheets, Python virtual environments, model weights "
        "and local browser caches. The required primary video and YOLOv8n model hashes are in "
        "the handoff. Without those identical inputs the saved numerical results cannot be reproduced.\n\n"
        "`PACKAGE_MANIFEST_SHA256.json` lists every included file and its SHA-256. Files in "
        "`data/matches/yt_u5HnY2aNW14/screening/` are original machine-readable primary-match "
        "records and reviewer annotations; do not regenerate or overwrite manual annotations. "
        "Some historical DELIVERABLES reports predate later reviews; use the dated handoff and final thesis "
        "draft for current claims. No ethics approval or source redistribution permission is implied.\n"
    ).encode("utf-8")
    records = []
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(OUT, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=8) as archive:
        archive.writestr("README_SHARE_PACKAGE.md", readme)
        for path in sorted(files, key=lambda x: x.relative_to(ROOT).as_posix()):
            name = path.relative_to(ROOT).as_posix()
            data = path.read_bytes()
            archive.writestr(name, data)
            records.append({"path": name, "bytes": len(data), "sha256": sha_bytes(data)})
        manifest = {"package_date": "2026-11-11", "scope": "source_code_and_numerical_evidence_no_video_or_identifiable_frames",
                    "file_count": len(records), "files": records}
        archive.writestr("PACKAGE_MANIFEST_SHA256.json", json.dumps(manifest, indent=2) + "\n")
    print(f"{OUT}: {len(records)} files, {OUT.stat().st_size:,} bytes")


if __name__ == "__main__":
    main()
