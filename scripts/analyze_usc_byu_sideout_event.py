"""Calculate the post hoc USC–BYU receive-to-first-attack event interval.

Only a saved source-frame review can produce a numeric result. This event
measure is separate from court-coordinate player tracking.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "data/processed/source_view_screen/usc_byu_sideout_review"
PROTOCOL = PACK / "event_protocol.json"
DRAFT = PACK / "event_review_draft.json"
OUTPUT = PACK / "event_result.json"
REPORT = ROOT / "DELIVERABLES/HONOURS_USC_BYU_SIDEOUT_EVENT_RESULT.md"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    source = ROOT / protocol["source_clip"]
    if sha256(source) != protocol["source_clip_sha256"]:
        raise ValueError("Side-out source clip hash changed")
    if not DRAFT.exists():
        print("Source-event review pending; no result written")
        return
    review = json.loads(DRAFT.read_text(encoding="utf-8"))
    row = review.get("verdict")
    if row is None or row.get("checked_unboxed_source") is not True:
        print("Completed source-event verdict pending; no result written")
        return
    lo, hi = protocol["review_frame_interval_inclusive"]
    sequence = [row.get(k) for k in ("serve", "reception", "set", "attack", "point_end")]
    for interval in sequence:
        if interval is not None and (len(interval) != 2 or
                not all(isinstance(n, int) and not isinstance(n, bool) and lo <= n <= hi
                        for n in interval) or interval[0] > interval[1]):
            raise ValueError("Invalid saved event bracket")
    observed = [interval for interval in sequence if interval is not None]
    if any(left[1] >= right[0] for left, right in zip(observed, observed[1:])):
        raise ValueError("Saved events are not in time order")
    reception, attack = row.get("reception"), row.get("attack")
    complete_sideout = (row.get("usc_served") is True and row.get("byu_won") is True
                        and all(event is not None for event in sequence))
    seconds = None
    if complete_sideout and reception and attack:
        fps = protocol["fps"]
        seconds = [round((attack[0] - reception[1]) / fps, 4),
                   round((attack[1] - reception[0]) / fps, 4)]
    output = {
        "status": "single_reviewer_source_event_exemplar" if complete_sideout else "source_event_review_incomplete_or_not_sideout",
        "case_id": protocol["case_id"],
        "source_clip_sha256": protocol["source_clip_sha256"],
        "protocol_sha256": sha256(PROTOCOL),
        "review_sha256": sha256(DRAFT),
        "reviewer_code": row["reviewer_code"],
        "usc_served": row["usc_served"],
        "byu_won": row["byu_won"],
        "score_before_byu_usc": row["score_before"],
        "score_after_byu_usc": row["score_after"],
        "score_review_status": ("entered_by_reviewer" if row["score_before"] and row["score_after"]
                                else "not_entered_by_reviewer"),
        "event_clip_frame_intervals": {k: row.get(k) for k in
                                       ("serve", "reception", "set", "attack", "point_end")},
        "receive_to_first_attack_seconds_interval": seconds,
        "selection_kind": "post_hoc_source_selected_after_outcome_inspection",
        "limitation": "One source-selected, single-reviewer event example; no validated six-player floor trajectory or outcome association.",
    }
    OUTPUT.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    lines = ["# USC–BYU side-out source-event result", "",
             "This is a post hoc, single-reviewer source-video exemplar outside the frozen outcome sample.", "",
             f"- Review status: **{output['status']}**",
             f"- USC served / BYU won: **{row['usc_served']} / {row['byu_won']}**",
             f"- Score before / after (BYU–USC): **{row['score_before'] or 'not entered'} / {row['score_after'] or 'not entered'}**",
             f"- Saved event clip frames: serve {row['serve']}, reception {row['reception']}, set {row['set']}, first attack {row['attack']}, ending {row['point_end']}",
             f"- Reception-to-first-attack time: **{f'{seconds[0]:.3f}' if seconds is not None and seconds[0] == seconds[1] else seconds if seconds is not None else 'null'} s**", "",
             "The marked contacts are single clip frames; the time is (first attack frame - reception frame) / 30 fps. The score fields were not entered by the reviewer when blank; the earlier source-screening score read remains separate. The saved serve, set, ending, serve team and winner support the side-out sequence. This is one source-selected event example and does not certify player identities, floor positions, a team formation transition or an outcome effect.\n"]
    REPORT.write_text("\n".join(lines), encoding="utf-8")
    print(f"Side-out status: {output['status']}; receive-to-attack: {seconds}")


if __name__ == "__main__":
    main()
