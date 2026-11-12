"""Create source-only crops to inspect the ambiguous blue player in window B."""

from pathlib import Path

import cv2

root = Path('data/matches/yt_em6zFUxfYpc/pilot')
video = cv2.VideoCapture(str(root.parent / 'heldout_source_cfr.mp4'))
frames = [754, 758, 762, 766, 770, 774, 778]
rows = []
for frame in frames:
    video.set(cv2.CAP_PROP_POS_FRAMES, frame)
    ok, image = video.read()
    if not ok:
        raise RuntimeError(frame)
    crop = image[525:835, 880:1190].copy()
    cv2.putText(crop, str(frame), (8, 35), cv2.FONT_HERSHEY_SIMPLEX,
                1.1, (0, 255, 255), 3)
    rows.append(cv2.resize(crop, (620, 620)))
video.release()
cv2.imwrite(str(root / 'cross_b_middle_source.jpg'), cv2.vconcat(rows))
