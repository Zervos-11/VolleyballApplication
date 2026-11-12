"""Exercise the review save path without touching researcher annotations."""

import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from services.api import elevated_transfer_review as review


class ElevatedReviewSaveTest(unittest.TestCase):
    def test_save_and_revision_conflict(self):
        match_id = "yt_-siJXMXKcbo"
        with tempfile.TemporaryDirectory(dir=review.BASE) as temp_name:
            temp = Path(temp_name)
            shutil.copy2(review.BASE / "elevated_transfer_review" / f"{match_id}_suggestions.json",
                         temp / f"{match_id}_suggestions.json")
            review.case_data.cache_clear()
            try:
                with patch.object(review, "PACK", temp):
                    client = TestClient(review.app)
                    data = client.get(f"/api/cases/{match_id}").json()
                    first = data["suggestions"]["rows"][0]
                    frame = first["excerpt_frame"]
                    rows = []
                    for slot in first["slots"]:
                        candidate = slot["suggested_raw_track_id"]
                        rows.append({"slot": slot["slot"], "identity_status": "sequence_consistent",
                                     "physical_state": "grounded", "candidate_raw_track_id": candidate,
                                     "box_alignment": "same_player" if candidate is not None else "no_box",
                                     "floor_alignment": "plausible" if candidate is not None else "not_applicable",
                                     "note": ""})
                    payload = {"expected_revision": 0, "reviewer_code": "test",
                               "checked_all_six_in_source": True, "rows": rows}
                    endpoint = f"/api/cases/{match_id}/frame/{frame}"
                    saved = client.put(endpoint, json=payload)
                    self.assertEqual(saved.status_code, 200, saved.text)
                    self.assertEqual(saved.json()["draft"]["revision"], 1)
                    draft = json.loads((temp / f"{match_id}_review_draft.json").read_text())
                    self.assertEqual(draft["frames"][str(frame)]["rows"], rows)
                    self.assertEqual(client.put(endpoint, json=payload).status_code, 409)
                    payload["expected_revision"] = 1
                    payload["unexpected"] = "rejected"
                    self.assertEqual(client.put(endpoint, json=payload).status_code, 422)

                    court = client.get(f"/api/cases/{match_id}/calibration")
                    self.assertEqual(court.status_code, 200)
                    landmarks = []
                    positions = {"net_left": (0, 0), "net_right": (100, 0),
                                 "baseline_left": (0, 100), "baseline_right": (100, 100),
                                 "attack_left": (0, 100 / 3), "attack_right": (100, 100 / 3)}
                    for code, (x, y) in positions.items():
                        landmarks.append({"code": code, "x_px": x, "y_px": y,
                                          "status": "clicked", "note": ""})
                    saved_court = client.put(f"/api/cases/{match_id}/calibration",
                                             json={"expected_revision": 0, "reviewer_code": "test",
                                                   "checked_unboxed_source": True,
                                                   "landmarks": landmarks})
                    self.assertEqual(saved_court.status_code, 200, saved_court.text)
                    self.assertLess(saved_court.json()["draft"]["check"]["held_out_attack_errors_m"]["attack_left"], 0.001)

                    reference = client.get(f"/api/cases/{match_id}/position-reference")
                    self.assertEqual(reference.status_code, 200)
                    chosen_frame = reference.json()["reference_frames"][0]
                    ref_rows = [{"slot": i, "state": "uncertain", "shoe_x_px": None,
                                 "shoe_y_px": None, "note": "test"} for i in range(1, 7)]
                    ref_rows[0].update(state="grounded", shoe_x_px=250, shoe_y_px=400)
                    saved_ref = client.put(f"/api/cases/{match_id}/position-reference/{chosen_frame}",
                                           json={"expected_revision": 0, "reviewer_code": "test",
                                                 "checked_unboxed_source": True,
                                                 "identity_guide_seen": False, "rows": ref_rows})
                    self.assertEqual(saved_ref.status_code, 200, saved_ref.text)
                    self.assertEqual(saved_ref.json()["draft"]["frames"][str(chosen_frame)]["rows"], ref_rows)
            finally:
                review.case_data.cache_clear()


if __name__ == "__main__":
    unittest.main()
