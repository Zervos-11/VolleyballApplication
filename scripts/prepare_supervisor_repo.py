"""Create a GitHub-ready, media-free supervisor review snapshot."""

from __future__ import annotations

import hashlib
import json
import shutil
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "SUPERVISOR_GITHUB_READY_2026-11-12"
PRIMARY = ROOT / "data/matches/yt_u5HnY2aNW14"
CODE_SUFFIXES = {".py", ".html", ".js", ".css", ".yaml", ".yml", ".toml"}
RECORD_SUFFIXES = {".json", ".csv", ".md"}
FORBIDDEN_SUFFIXES = {".mp4", ".mov", ".mkv", ".avi", ".webm", ".jpg", ".jpeg",
                      ".webp", ".gif", ".wav", ".mp3", ".pt", ".onnx", ".part"}


def selected_files() -> list[Path]:
    files = {ROOT / name for name in ("requirements.txt", "requirements-research.txt")}
    for folder in ("scripts", "src", "services", "web", "tests"):
        files.update(path for path in (ROOT / folder).rglob("*")
                     if path.is_file() and path.suffix.lower() in CODE_SUFFIXES
                     and "__pycache__" not in path.parts
                     and path.name != "render_u5_thesis_preview.py")
    files.update(path for path in (ROOT / "annotations").rglob("*")
                 if path.is_file() and path.suffix.lower() in RECORD_SUFFIXES)
    excluded_docs = {"README.md", "CHATGPT_THESIS_HANDOFF.md", "HONOURS_METHODS_RESULTS_DRAFT.md",
                     "HONOURS_U5_PRIMARY_MANUSCRIPT_DRAFT.md", "HONOURS_U5_THESIS_COMPLETION_GUIDE.md",
                     "HONOURS_U5_THESIS_FINAL_DRAFT.md", "HONOURS_U5_THESIS_WORKING_DRAFT.md"}
    files.update(path for path in (ROOT / "DELIVERABLES").glob("*.md")
                 if path.is_file() and path.name not in excluded_docs)
    files.update(path for path in (ROOT / "DELIVERABLES/figures").rglob("*")
                 if path.is_file() and path.suffix.lower() in {".png", ".pdf"})
    files.add(PRIMARY / "primary_source_manifest.json")
    files.update(path for path in (PRIMARY / "screening").rglob("*")
                 if path.is_file() and path.suffix.lower() in RECORD_SUFFIXES)
    for folder in ("elevated_transfer_review", "usc_byu_sideout_review"):
        base = ROOT / "data/processed/source_view_screen" / folder
        files.update(path for path in base.rglob("*")
                     if path.is_file() and path.suffix.lower() in RECORD_SUFFIXES)
    transition = ROOT / "data/processed/receive_to_attack_transition"
    files.update(path for path in transition.rglob("*")
                 if path.is_file() and path.suffix.lower() in RECORD_SUFFIXES)
    files.add(ROOT / "data/processed/source_view_screen/transfer_source_only_selection_2026-11-06_v2.json")
    result = sorted(files, key=lambda path: path.relative_to(ROOT).as_posix())
    assert all(path.is_file() and path.resolve().is_relative_to(ROOT) for path in result)
    assert not any(path.suffix.lower() in FORBIDDEN_SUFFIXES for path in result)
    return result


def main() -> None:
    if DEST.exists():
        raise SystemExit(f"Refusing to overwrite existing snapshot: {DEST}")
    files = selected_files()
    DEST.mkdir()
    records = []
    for source in files:
        relative = source.relative_to(ROOT)
        target = DEST / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        if relative.as_posix() == "DELIVERABLES/HONOURS_SHAREABLE_RESEARCH_HANDOFF_2026-11-11.md":
            handoff = target.read_text(encoding="utf-8")
            note = ("> **Repository note, 12 November 2026:** This is the earlier ZIP handoff retained "
                    "for methods, provenance and disclosure context. The private GitHub repository "
                    "omits the thesis manuscript and its PDF at the student's request. References "
                    "below to a ZIP or thesis draft describe that earlier package; the current "
                    "repository contains code and numerical evidence only.\n\n")
            target.write_text(handoff.replace("\n\n", "\n\n" + note, 1), encoding="utf-8")
        records.append({"path": relative.as_posix(), "bytes": target.stat().st_size,
                        "sha256": hashlib.sha256(target.read_bytes()).hexdigest()})
    (DEST / ".gitignore").write_text(
        ".venv/\n__pycache__/\n.pytest_cache/\n*.pyc\n.env\n.env.*\n"
        "*.mp4\n*.mov\n*.mkv\n*.avi\n*.webm\n*.jpg\n*.jpeg\n*.webp\n"
        "*.wav\n*.mp3\n*.pt\n*.onnx\n*.part\n"
        "data/**/*.png\ndata/**/*.pdf\ndata/**/*.gif\n", encoding="utf-8")
    (DEST / ".gitattributes").write_text(
        "* text=auto eol=lf\n*.png binary\n*.pdf binary\n", encoding="utf-8")
    (DEST / "README.md").write_text(
        "# Volleyball analytics research code and evidence\n\n"
        "This private repository contains code, numerical review records and result reports for "
        "Michael Zervos's honours research prototype. **The thesis manuscript is provided "
        "separately and is not stored in this repository.**\n\n"
        "Start with [the supervisor review guide](SUPERVISOR_REVIEW.md), "
        "[primary feasibility result](DELIVERABLES/HONOURS_U5_PRIMARY_FEASIBILITY_RESULT.md), "
        "[S3 P34 interval result](DELIVERABLES/HONOURS_U5_S3P34_REPORTED_LIVE_INTERVAL_RESULT.md), "
        "and [data management record](DELIVERABLES/DATA_MANAGEMENT.md). "
        "The dated research handoff describes an earlier ZIP package; its thesis references are "
        "historical and the manuscript is not included here.\n\n"
        "Run `python scripts/check_honours_evidence_package.py --code-review-snapshot` "
        "to verify included primary-match numerical records. Source videos, identifiable frames, "
        "model weights and local caches are omitted.\n", encoding="utf-8")
    (DEST / "SUPERVISOR_REVIEW.md").write_text(
        "# Supervisor review guide\n\n"
        "The thesis manuscript is supplied separately. This repository provides the implementation "
        "and source-linked numerical evidence. Start with the "
        "[primary feasibility result](DELIVERABLES/HONOURS_U5_PRIMARY_FEASIBILITY_RESULT.md), "
        "[reported-live interval result](DELIVERABLES/HONOURS_U5_S3P34_REPORTED_LIVE_INTERVAL_RESULT.md), "
        "[transfer review](DELIVERABLES/HONOURS_ELEVATED_TRANSFER_REVIEW_STATUS_2026-11-06.md), "
        "and [research handoff](DELIVERABLES/HONOURS_SHAREABLE_RESEARCH_HANDOFF_2026-11-11.md). "
        "Older result reports are retained as research history and may use earlier denominators.\n\n"
        "Run `python scripts/check_honours_evidence_package.py --code-review-snapshot` for the "
        "included primary-match numerical records. The full 93-test suite passed in the local "
        "source workspace; some tests require source images intentionally omitted here. "
        "Run `python -m unittest discover -s tests -p 'test_honours_team_metrics.py' -q` "
        "for a four-test code-only smoke check in this snapshot. "
        "Research dependencies are in `requirements-research.txt`; the handoff records the actual environment.\n\n"
        "This snapshot contains code, numerical annotations and report figures. It omits source videos, "
        "identifiable frame images, model weights and local caches. Some historical report links point "
        "to omitted source images and cannot open here. Reproducing detection runs requires the exact "
        "source video and model weights identified by hash in the handoff. Do not overwrite manual review records.\n\n"
        "The repository should remain private pending a documented ethics and source-use decision. "
        "The student must confirm the AI-use disclosure and final thesis text before submission. "
        "This snapshot is for supervisor review, not a final university submission.\n",
        encoding="utf-8")
    manifest = {"snapshot_date": date.today().isoformat(),
                "scope": "code_numerical_records_reports_no_video_or_identifiable_frames",
                "file_count": len(records), "files": records}
    (DEST / "SNAPSHOT_MANIFEST_SHA256.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"{DEST}: {len(records)} source files; {sum(r['bytes'] for r in records):,} source bytes")


if __name__ == "__main__":
    main()
