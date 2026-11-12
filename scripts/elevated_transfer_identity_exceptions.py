"""Source-reviewed identity exceptions for transfer scoring.

The saved human rows remain immutable; unresolved decisions do not count as accepted.
"""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "data/processed/source_view_screen/elevated_transfer_review/pepperdine_p3_p4_identity_exception_2026-11-06.json"


def unresolved_swap(match_id: str, frame: int, row: dict) -> bool:
    if match_id != "yt__BOwnLLVaPs":
        return False
    data = json.loads(LEDGER.read_text(encoding="utf-8"))
    return any(item["excerpt_frame"] == frame and item["slot"] == row["slot"]
               and item["unresolved_raw_id"] == row["candidate_raw_track_id"]
               for item in data["affected_saved_rows"])
