"""Render source-frame overlays for provisional six-player sample candidates."""
import json
from pathlib import Path

import cv2


ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / 'data/processed/honours_completed_sample_audit.json'
SOURCE = ROOT / 'data/matches/yt_FqE5pTJqx8g/source_record.json'
OUT = ROOT / 'data/processed/honours_annotation_workspace/qc_sheets'


def render():
    audit = json.loads(AUDIT.read_text(encoding='utf-8'))
    source = json.loads(SOURCE.read_text(encoding='utf-8'))
    cap = cv2.VideoCapture(str(ROOT / source['video_file']))
    if not cap.isOpened():
        raise RuntimeError('Source video is unavailable')
    OUT.mkdir(parents=True, exist_ok=True)
    try:
        for set_number in (1, 2, 3):
            images = []
            for point in audit['points']:
                if point['set'] != set_number:
                    continue
                labels = json.loads((ROOT / point['label_file']).read_text(encoding='utf-8'))
                for row in point['frame_rows']:
                    if not row['projection_in_court']:
                        continue
                    index = row['frame']
                    cap.set(cv2.CAP_PROP_POS_FRAMES, index)
                    ok, frame = cap.read()
                    if not ok or round(cap.get(cv2.CAP_PROP_POS_FRAMES)) != index + 1:
                        raise RuntimeError(f'Could not decode exact source frame {index}')
                    for player in labels['frames'][str(index)]['players']:
                        box = player['bbox']
                        if box:
                            x1, y1, x2, y2 = map(round, box)
                            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 220, 80), 3)
                            cv2.putText(frame, f"{player['player_id']} {player['team_id']}",
                                        (x1, max(30, y1 - 8)), cv2.FONT_HERSHEY_SIMPLEX, .8,
                                        (0, 0, 0), 5, cv2.LINE_AA)
                            cv2.putText(frame, f"{player['player_id']} {player['team_id']}",
                                        (x1, max(30, y1 - 8)), cv2.FONT_HERSHEY_SIMPLEX, .8,
                                        (255, 255, 255), 2, cv2.LINE_AA)
                        foot = player['footpoint']
                        if foot:
                            cv2.circle(frame, tuple(map(round, foot)), 10, (0, 0, 255), -1)
                    cv2.putText(frame, f"S{set_number} P{point['point_number']} frame {index}",
                                (25, 55), cv2.FONT_HERSHEY_SIMPLEX, 1.4, (0, 0, 0), 6, cv2.LINE_AA)
                    cv2.putText(frame, f"S{set_number} P{point['point_number']} frame {index}",
                                (25, 55), cv2.FONT_HERSHEY_SIMPLEX, 1.4, (255, 255, 255), 3, cv2.LINE_AA)
                    images.append(frame)
            # One original-resolution frame per file keeps feet and IDs inspectable.
            frame_rows = [(p, r) for p in audit['points'] if p['set'] == set_number
                          for r in p['frame_rows'] if r['projection_in_court']]
            for (point, row), frame in zip(frame_rows, images):
                path = OUT / f"s{set_number}_p{point['point_number']}_f{row['frame']}.jpg"
                cv2.imwrite(str(path), frame, [cv2.IMWRITE_JPEG_QUALITY, 92])
    finally:
        cap.release()
    print(f'Wrote source overlays to {OUT.relative_to(ROOT)}')


if __name__ == '__main__':
    render()
