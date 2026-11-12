import os
from pathlib import Path

DATA_DIR = Path(os.getenv("DATA_DIR", "./data"))
ARTIFACTS_SUBDIR = os.getenv("ARTIFACTS_SUBDIR", "matches")

BASE_MATCH_DIR = DATA_DIR / ARTIFACTS_SUBDIR
BASE_MATCH_DIR.mkdir(parents=True, exist_ok=True)

def match_dir(match_id: str) -> Path:
    d = BASE_MATCH_DIR / match_id
    d.mkdir(parents=True, exist_ok=True)
    return d

def save_video_chunk(match_id: str, filename: str, content: bytes) -> Path:
    d = match_dir(match_id)
    path = d / filename
    with open(path, "ab") as f:
        f.write(content)
    return path

def save_json(match_id: str, name: str, content: str) -> Path:
    d = match_dir(match_id)
    path = d / name
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return path

def artifact_path(match_id: str, name: str) -> Path:
    d = match_dir(match_id)
    return d / name
