"""Compare saved AoEP floor clicks with saved-box bottom-centre proxies."""

import hashlib
import json
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DIR = ROOT / "data/processed/aoep_new_source"
FOOT = DIR / "saved_floor_contact_audit.json"
BOX = DIR / "saved_bbox_floor_proxy.json"
OUTPUT = DIR / "saved_floor_proxy_discrepancy.json"


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    foot = json.loads(FOOT.read_text(encoding="utf-8"))
    box = json.loads(BOX.read_text(encoding="utf-8"))
    if foot["source_sha256"] != box["source_sha256"] or foot["calibration_sha256"] != box["calibration_sha256"]:
        raise ValueError("source or calibration snapshot mismatch")
    rows = {(item["frame_index"], item["player_id"]): item for item in box["rows"]}
    comparisons = []
    for item in foot["observations"]:
        key = item["frame_index"], item["player_id"]
        candidate = rows.get(key)
        if candidate is None:
            continue
        comparisons.append({
            "frame_index": item["frame_index"],
            "player_id": item["player_id"],
            "saved_contact_review_state": item["source_visual_review"],
            "box_proxy_provisional_eligible": candidate["provisional_ground_proxy_eligible"],
            "pixel_discrepancy": round(math.dist(item["footpoint_px"], candidate["box_bottom_centre_px"]), 1),
            "projected_discrepancy_m": round(math.dist(item["court_position_m_diagnostic"], candidate["court_position_m_diagnostic"]), 2),
            "interpretation": "Disagreement between two provisional markings on the same source frame; neither is established ground truth.",
        })
    result = {
        "status": "single_frame_proxy_discrepancy_not_accuracy_validation",
        "source_sha256": foot["source_sha256"],
        "calibration_sha256": foot["calibration_sha256"],
        "saved_annotations_sha256": foot["annotations_sha256"],
        "floor_audit_sha256": sha256(FOOT),
        "box_audit_sha256": sha256(BOX),
        "frame_index": 75180,
        "comparisons": comparisons,
        "limit": "Only one saved click per player is available. The saved clicks were not independently verified; the setter click conflicts with visible airborne posture. These discrepancies are a scale warning, not a bias correction or uncertainty interval for accumulated distance.",
    }
    OUTPUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(OUTPUT)
    for item in comparisons:
        print(item["player_id"], item["projected_discrepancy_m"])


if __name__ == "__main__":
    main()
