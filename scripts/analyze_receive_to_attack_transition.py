"""Calculate reviewed serve-reception to first-attack elapsed time.

This deliberately refuses to produce a metric from the blank event template.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "data/processed/receive_to_attack_transition"
TEMPLATE = PACK / "protocol.json"
COMPLETED = PACK / "completed.json"
OUTPUT = PACK / "result.json"
REPORT = ROOT / "DELIVERABLES/HONOURS_RECEIVE_TO_ATTACK_TRANSITION_RESULT.md"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def setup() -> None:
    PACK.mkdir(parents=True, exist_ok=True)
    cases = []
    for match, rally_id in (("yt_AoEP-YiWRvc", "point_21m"),
                            ("yt_FqE5pTJqx8g", "r3")):
        base = ROOT / "data/matches" / match
        record_path = base / "source_record.json"
        selection_path = base / "pilot/selection.json"
        record = json.loads(record_path.read_text(encoding="utf-8"))
        selection = json.loads(selection_path.read_text(encoding="utf-8"))
        rally = next(r for r in selection["rallies"] if r["rally_id"] == rally_id)
        cases.append({"match_id": match, "rally_id": rally_id,
                      "source_sha256": record["sha256"],
                      "source_record_sha256": sha(record_path),
                      "selection_sha256": sha(selection_path),
                      "fps": record["camera"]["fps"],
                      "provisional_interval_inclusive": [rally["start_frame"],
                                                         rally["end_frame_exclusive"] - 1],
                      "phase_review": {
                          "near_side_receives": None,
                          "reception_contact_frame_interval": None,
                          "first_near_side_attack_contact_frame_interval": None,
                          "attack_absent": None,
                          "reviewer_code": "",
                          "source_only_before_metric": None,
                          "note": ""}})
    data = {"status": "frozen_blank_source_event_template",
            "definition": "Elapsed seconds from first near-side serve-reception contact to first subsequent near-side attack contact; null if either contact is unavailable or the near side does not receive",
            "event_frame_rule": "inclusive [first_possible_frame,last_possible_frame]; use [f,f] when exact",
            "case_selection": "source-selected/proposed before this metric calculation; event brackets remain unverified",
            "cases": cases}
    if TEMPLATE.exists():
        assert json.loads(TEMPLATE.read_text(encoding="utf-8")) == data, "Frozen template differs"
    else:
        TEMPLATE.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    setup()
    if not COMPLETED.exists():
        print(f"Blank event template ready: {TEMPLATE.relative_to(ROOT)}; no metric calculated")
        return
    template = json.loads(TEMPLATE.read_text(encoding="utf-8"))
    submitted = json.loads(COMPLETED.read_text(encoding="utf-8"))
    assert set(submitted) == {"protocol_sha256", "cases"}
    assert submitted["protocol_sha256"] == sha(TEMPLATE)
    assert len(submitted["cases"]) == len(template["cases"])
    result = []
    for frozen, row in zip(template["cases"], submitted["cases"]):
        assert (row["match_id"], row["rally_id"]) == (frozen["match_id"], frozen["rally_id"])
        assert set(row) == {"match_id", "rally_id", "near_side_receives",
                            "reception_contact_frame_interval", "first_near_side_attack_contact_frame_interval",
                            "attack_absent", "reviewer_code", "source_only_before_metric", "note"}
        assert row["reviewer_code"].strip() and row["source_only_before_metric"] is True
        start, end = frozen["provisional_interval_inclusive"]
        if row["attack_absent"] is True:
            seconds = None
            reason = "no_near_side_attack"
        elif row["near_side_receives"] is False:
            seconds = None
            reason = "near_side_did_not_receive"
        elif row["near_side_receives"] is not True:
            seconds = None
            reason = "near_side_receive_uncertain"
        else:
            reception = row["reception_contact_frame_interval"]
            attack = row["first_near_side_attack_contact_frame_interval"]
            if reception is None or attack is None:
                seconds = None
                reason = "contact_unobservable"
            else:
                assert (len(reception) == len(attack) == 2 and
                        all(isinstance(v, int) and start <= v <= end for v in reception + attack) and
                        reception[0] <= reception[1] < attack[0] <= attack[1])
                fps = float(frozen["fps"])
                seconds = [round((attack[0] - reception[1]) / fps, 4),
                           round((attack[1] - reception[0]) / fps, 4)]
                reason = "reviewed_event_interval"
        result.append({"match_id": frozen["match_id"], "rally_id": frozen["rally_id"],
                       "receive_to_first_attack_seconds_interval": seconds,
                       "status": reason, "reviewer_code": row["reviewer_code"],
                       "note": row["note"]})
    output = {"status": "single_reviewer_source_event_transition_metric",
              "protocol_sha256": sha(TEMPLATE), "completed_sha256": sha(COMPLETED),
              "cases": result,
              "limitations": ["Event times depend on single-reviewer visual brackets.",
                              "Two selected points do not establish an outcome association or generalisability."]}
    OUTPUT.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    lines = ["# Receive-to-first-attack transition result", "",
             "The measure is elapsed time from first near-side serve-reception contact to first subsequent near-side attack contact. Intervals reflect uncertain event frames. Null means the contacts were not both observed. This source-event measure is separate from floor-coordinate tracking.", "",
             "| Match | Point | Elapsed time interval (s) | Status |", "| --- | --- | ---: | --- |"]
    for item in result:
        value = item["receive_to_first_attack_seconds_interval"]
        lines.append(f"| {item['match_id']} | {item['rally_id']} | {value if value is not None else 'null'} | {item['status']} |")
    lines += ["", "The first point's reception was bracketed at frames 75088–75090 and attack contact at frame 75266. The second point's no-attack verdict was reported by the student in chat on 7 November 2026; its receive status and reception contact were not separately specified. These selected, single-reviewer events do not support a winner-effect claim.\n"]
    REPORT.write_text("\n".join(lines), encoding="utf-8")
    print(f"Calculated {sum(r['receive_to_first_attack_seconds_interval'] is not None for r in result)} transition intervals")


if __name__ == "__main__":
    main()
