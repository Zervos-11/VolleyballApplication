"""Render source-frame evidence for S3 P34 boundary and identity review.

All images are navigation aids. Labels are raw tracker IDs, never certified jerseys.
"""

import json
from pathlib import Path

import cv2


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "data/matches/yt_u5HnY2aNW14"
SCREEN = BASE / "screening"
OUT = SCREEN / "s3p34_validation_review"


def main():
    OUT.mkdir(exist_ok=True)
    screen = json.loads((SCREEN / "source_bracketed_30fps_screen.json").read_text())
    point = next(p for p in screen["points"] if (p["set"], p["point_number"]) == (3, 34))
    rows = {r["source_frame"]: r for r in point["rows"]}
    source_frames = sorted(set(range(35982, 36017, 2)) |
                           set(range(35986, 36001)) |
                           set(range(36106, 36131)) |
                           set(range(36130, 36155)) |
                           set(range(36000, 36151, 6)) |
                           {36018, 36030, 36042, 36054, 36066, 36078,
                            36090, 36102, 36114, 36120, 36126, 36138})
    cap = cv2.VideoCapture(str(BASE / "source_720p.mp4"))
    assert cap.isOpened()
    frames = {}
    for number in source_frames:
        cap.set(cv2.CAP_PROP_POS_FRAMES, number)
        ok, image = cap.read()
        assert ok
        frames[number] = image
        if number % 6 == 0 or number in {35990, 36000, 36006, 36012, 36018, 36024, 36030, 36036, 36042,
                      36054, 36066, 36078, 36090, 36096, 36102, 36114, 36120,
                      36126, 36132, 36138, 36144, 36150}:
            assert cv2.imwrite(str(OUT / f"source_{number}.png"), image)
        if number in rows:
            overlay = image.copy()
            for proposal in rows[number]["proposals"]:
                x1, y1, x2, y2 = map(int, proposal["bbox_px"])
                color = ((0, 220, 0) if proposal["net_side_status"] ==
                         "near_floor_side_candidate" else (0, 180, 255))
                cv2.rectangle(overlay, (x1, y1), (x2, y2), color, 2)
                cv2.putText(overlay, f"ID {proposal['raw_track_id']}",
                            (x1, max(18, y1 - 5)), cv2.FONT_HERSHEY_SIMPLEX,
                            .55, (0, 0, 0), 3)
                cv2.putText(overlay, f"ID {proposal['raw_track_id']}",
                            (x1, max(18, y1 - 5)), cv2.FONT_HERSHEY_SIMPLEX,
                            .55, color, 1)
            if number % 6 == 0 or number >= 36106:
                assert cv2.imwrite(str(OUT / f"raw_ids_{number}.jpg"), overlay)
    cap.release()

    def sheet(numbers, label):
        for part in range(0, len(numbers), 12):
            chunk = numbers[part:part + 12]
            tiles = []
            for number in chunk:
                tile = cv2.resize(frames[number], (640, 360))
                cv2.putText(tile, str(number), (10, 32), cv2.FONT_HERSHEY_SIMPLEX,
                            .9, (0, 0, 0), 4)
                cv2.putText(tile, str(number), (10, 32), cv2.FONT_HERSHEY_SIMPLEX,
                            .9, (255, 255, 255), 2)
                tiles.append(tile)
            black = tiles[0] * 0
            tiles.extend([black] * (12 - len(tiles)))
            canvas = cv2.vconcat([cv2.hconcat(tiles[i:i + 3])
                                  for i in range(0, 12, 3)])
            assert cv2.imwrite(str(OUT / f"{label}_{part // 12 + 1}.jpg"), canvas)

    sheet(list(range(35982, 36017, 2)), "serve")
    sheet(list(range(36130, 36155)), "end")
    sheet(list(range(36000, 36151, 6)), "identity")
    sheet(list(range(36106, 36131)), "net_identity")
    for label, numbers, box in (
        ("serve_detail", list(range(35986, 36001)), (680, 330, 1000, 715)),
        ("end_detail", list(range(36132, 36147)), (0, 0, 520, 360)),
    ):
        crops = []
        x1, y1, x2, y2 = box
        for number in numbers:
            crop = frames[number][y1:y2, x1:x2]
            tile = cv2.resize(crop, (x2 - x1, y2 - y1))
            cv2.putText(tile, str(number), (10, 32), cv2.FONT_HERSHEY_SIMPLEX,
                        .9, (0, 0, 0), 4)
            cv2.putText(tile, str(number), (10, 32), cv2.FONT_HERSHEY_SIMPLEX,
                        .9, (255, 255, 255), 2)
            crops.append(tile)
        for part in range(0, len(crops), 9):
            tiles = crops[part:part + 9]
            tiles.extend([tiles[0] * 0] * (9 - len(tiles)))
            canvas = cv2.vconcat([cv2.hconcat(tiles[i:i + 3])
                                  for i in range(0, 9, 3)])
            assert cv2.imwrite(str(OUT / f"{label}_{part // 9 + 1}.jpg"), canvas)
    print(f"Wrote {len(frames)} source frames and review sheets to {OUT}")


if __name__ == "__main__":
    main()
