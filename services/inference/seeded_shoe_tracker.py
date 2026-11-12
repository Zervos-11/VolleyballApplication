"""Seeded shoe-colour candidates for image-space review.

The seed belongs to a player already identified in a source frame. Candidate
centres describe visible colour regions, not sole-floor contact points. This
module intentionally does not project to court metres or emit travel metrics.
"""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np


@dataclass(frozen=True)
class LabShoeProfile:
    l_min: int
    a_min: int
    b_max: int
    l_max: int = 255
    a_max: int = 255
    b_min: int = 0
    min_area_px: int = 18
    max_distance_px: float = 38.0
    suspicious_step_px: float = 8.0
    search_left_px: int = 48
    search_right_px: int = 42
    search_up_px: int = 28
    search_down_px: int = 15


class SeededShoeTracker:
    def __init__(self, seed_px: tuple[float, float], profile: LabShoeProfile):
        self.last_candidate_px = tuple(map(float, seed_px))
        self.profile = profile

    def observe(self, frame: np.ndarray) -> dict:
        """Return an unverified colour candidate or an explicit missing state."""
        x, y = self.last_candidate_px
        p = self.profile
        x0 = max(0, int(round(x)) - p.search_left_px)
        x1 = min(frame.shape[1], int(round(x)) + p.search_right_px)
        y0 = max(0, int(round(y)) - p.search_up_px)
        y1 = min(frame.shape[0], int(round(y)) + p.search_down_px)
        if x1 <= x0 or y1 <= y0:
            return self._missing()
        lab = cv2.cvtColor(frame[y0:y1, x0:x1], cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        mask = ((l >= p.l_min) & (l <= p.l_max) &
                (a >= p.a_min) & (a <= p.a_max) &
                (b >= p.b_min) & (b <= p.b_max)).astype(np.uint8) * 255
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN,
                                cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3)))
        count, _, stats, centroids = cv2.connectedComponentsWithStats(mask)
        components = []
        for index in range(1, count):
            area = int(stats[index, cv2.CC_STAT_AREA])
            if area < p.min_area_px:
                continue
            left, top, width, height = map(int, stats[index, :4])
            centre = (float(centroids[index, 0] + x0),
                      float(centroids[index, 1] + y0))
            distance = float(np.linalg.norm(np.subtract(centre, self.last_candidate_px)))
            if distance <= p.max_distance_px:
                components.append((distance, -area, centre, (left + x0, top + y0,
                                                            left + x0 + width, top + y0 + height), area))
        if not components:
            return self._missing()
        distance, _, centre, bbox, area = min(components, key=lambda row: (row[0], row[1]))
        self.last_candidate_px = centre
        return {
            "state": "unverified_colour_candidate",
            "centre_px": [round(centre[0], 1), round(centre[1], 1)],
            "bbox_px": list(bbox),
            "area_px": area,
            "component_count": len(components),
            "step_px": round(distance, 1),
            "continuity_suspect": distance > p.suspicious_step_px,
            "verified_floor_contact_px": None,
            "court_position_m": None,
        }

    @staticmethod
    def _missing() -> dict:
        return {"state": "no_colour_candidate", "centre_px": None,
                "bbox_px": None, "area_px": None, "component_count": 0,
                "step_px": None, "continuity_suspect": False,
                "verified_floor_contact_px": None, "court_position_m": None}
