import argparse, json, itertools, math
from pathlib import Path
import numpy as np
import cv2


def main():
    ap = argparse.ArgumentParser(description="Fix homography point order and target (half/full court)")
    ap.add_argument("--match_id", default="M1", help="Match id under data/matches/<match_id>")
    ap.add_argument("--path", default=None, help="Optional explicit homography.json path")
    args = ap.parse_args()

    jpath = Path(args.path) if args.path else Path(f"data/matches/{args.match_id}/homography.json")
    if not jpath.exists():
        raise SystemExit(f"Not found: {jpath}")

    j = json.loads(jpath.read_text(encoding="utf-8-sig"))
    pts_px = np.array(j["points_px"], dtype=np.float32)  # as clicked (unknown order)
    image_size = j.get("image_size")  # preserve if present

    # Targets (LB, RB, RF, LF) for half-court and full-court
    half = np.array([[0, 0], [9, 0], [9, 9], [0, 9]], dtype=np.float32)
    full = np.array([[0, 0], [18, 0], [18, 9], [0, 9]], dtype=np.float32)

    def side_metrics(coords):
        # coords: LB,RB,RF,LF in meters after projection
        a = float(np.linalg.norm(coords[1] - coords[0]))  # LB->RB
        b = float(np.linalg.norm(coords[2] - coords[1]))  # RB->RF
        c = float(np.linalg.norm(coords[3] - coords[2]))  # RF->LF
        d = float(np.linalg.norm(coords[0] - coords[3]))  # LF->LB
        diag = float(np.linalg.norm(coords[2] - coords[0]))  # LB->RF
        return a, b, c, d, diag

    def score_to(target_w, target_h, a, b, c, d, diag):
        # both sides should be close to target_w/target_h; diag ~= sqrt(w^2 + h^2)
        diag_target = math.hypot(target_w, target_h)
        return (
            abs(a - target_w)
            + abs(b - target_h)
            + abs(c - target_w)
            + abs(d - target_h)
            + abs(diag - diag_target)
        )

    best = None
    best_record = None

    for perm in itertools.permutations(range(4)):  # reorder clicked points to LB,RB,RF,LF
        ordered_px = pts_px[list(perm)]
        for name, target in [("half", half), ("full", full)]:
            try:
                H = cv2.getPerspectiveTransform(ordered_px, target)
                proj = cv2.perspectiveTransform(ordered_px.reshape(-1, 1, 2), H).reshape(-1, 2)
            except Exception:
                continue
            a, b, c, d, diag = side_metrics(proj)
            if name == "half":
                sc = score_to(9.0, 9.0, a, b, c, d, diag)
            else:
                # 18m sideline span for full court
                sc = score_to(9.0, 18.0, a, b, c, d, diag)

            rec = (sc, name, perm, (a, b, c, d, diag))
            if best is None or sc < best:
                best = sc
                best_record = rec

    if best_record is None:
        raise SystemExit("Could not compute a valid homography for any permutation.")

    sc, which, perm, mets = best_record
    ordered_px = pts_px[list(perm)]
    target = half if which == "half" else full

    print("Best fit:", which, "perm", perm, "score", round(sc, 3))
    print(
        "Projected sides (m): LB->RB={:.3f}  RB->RF={:.3f}  RF->LF={:.3f}  LF->LB={:.3f}  diag={:.3f}".format(
            *mets
        )
    )

    # Write corrected file (preserve image_size if present)
    fixed = {
        "schema_version": "v1",
        "points_px": [[float(x), float(y)] for x, y in ordered_px.tolist()],
        "points_court_m": target.tolist(),
    }
    if image_size and isinstance(image_size, (list, tuple)) and len(image_size) == 2:
        fixed["image_size"] = [int(image_size[0]), int(image_size[1])]

    jpath.write_text(json.dumps(fixed, indent=2), encoding="utf-8")
    print("Wrote corrected homography to", jpath)


if __name__ == "__main__":
    main()

