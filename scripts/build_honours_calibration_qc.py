"""Bound court-line geometry QC to source-reviewed live candidate frames."""
import hashlib
import json
from pathlib import Path

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'data/matches/yt_FqE5pTJqx8g/pilot/calibration'
PHASE = ROOT / 'data/processed/honours_candidate_phase_qc.json'
STABILITY = ROOT / 'data/processed/honours_camera_stability_audit.json'
SHEETS = ROOT / 'data/processed/honours_court_alignment_sheets/manifest.json'
DIAGNOSTIC = ROOT / 'data/processed/honours_image_alignment_diagnostic/diagnostic.json'
OUT = ROOT / 'data/processed/honours_calibration_qc.json'
REPORT = ROOT / 'DELIVERABLES/HONOURS_CALIBRATION_QC.md'


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def map_line_residual(camera, heldout):
    forward = cv2.getPerspectiveTransform(
        np.float32(camera['points_px']), np.float32(camera['points_court_m']))
    x1, y1, x2, y2 = heldout
    endpoints = cv2.perspectiveTransform(
        np.float32([[[x1, y1]], [[x2, y2]]]), forward)[:, 0, :]
    xs, ys = endpoints[:, 0], endpoints[:, 1]
    if not xs[0] < 0 < 9 < xs[1]:
        raise ValueError('Held-out net line does not span 0..9 m in court x')
    return {str(x): round(float(np.interp(x, xs, ys) - 9), 4) for x in (0, 2.25, 4.5, 6.75, 9)}


def main():
    phase, stability, sheets, diagnostic = read(PHASE), read(STABILITY), read(SHEETS), read(DIAGNOSTIC)
    manifest = read(BASE / 'calibration_manifest.json')
    if len(sheets['rows']) != 12 or not (
            phase['source_sha256'] == stability['source_sha256'] == sheets['source_sha256'] == diagnostic['source_sha256']):
        raise ValueError('QC records are not bound to the same source')
    camera_info = {}
    for key in ('camera_r1', 'camera_r2_r5'):
        path = BASE / f'{key}.json'
        residuals = map_line_residual(read(path), manifest['camera_segments'][key]['heldout_net_line_px'])
        camera_info[key] = {'calibration_sha256': sha(path), 'heldout_net_line_depth_residual_m': residuals,
                            'max_abs_heldout_residual_m': max(abs(v) for v in residuals.values())}
    rows = {r['frame']: r for r in stability['rows']}
    live = []
    for item in phase['rows']:
        if item['phase'] != 'live_play':
            continue
        row = rows[item['frame']]
        if row['status'] != 'registered':
            raise ValueError(f'Live frame {item["frame"]} has no registration')
        camera_key = 'camera_r1' if item['set'] == 1 else 'camera_r2_r5'
        camera = read(BASE / f'{camera_key}.json')
        court_points = np.float32(camera['points_px'] + [
            [(camera['points_px'][0][0] + camera['points_px'][1][0]) / 2,
             (camera['points_px'][0][1] + camera['points_px'][1][1]) / 2]])
        affine = np.float32(row['affine_ref_to_target'])
        displacement = np.linalg.norm(court_points @ affine[:, :2].T + affine[:, 2] - court_points,
                                      axis=1)
        live.append({'set': item['set'], 'point_number': item['point_number'],
                     'frame': item['frame'], 'camera_key': camera_key,
                     'static_wall_inliers': row['inliers'],
                     'median_static_wall_residual_px': row['median_inlier_residual_px'],
                     'max_fitted_court_point_displacement_px': round(float(displacement.max()), 3)})
    max_displacement = max(r['max_fitted_court_point_displacement_px'] for r in live)
    max_heldout = max(v['max_abs_heldout_residual_m'] for v in camera_info.values())
    result = {'status': 'bounded_court_geometry_check_passed_for_eight_live_snapshots_not_floor_contact_validation',
              'source_sha256': phase['source_sha256'], 'phase_qc_sha256': sha(PHASE),
              'stability_audit_sha256': sha(STABILITY), 'sheet_manifest_sha256': sha(SHEETS),
              'independent_image_alignment_diagnostic_sha256': sha(DIAGNOSTIC),
              'calibration_manifest_sha256': sha(BASE / 'calibration_manifest.json'),
              'camera_groups': camera_info, 'live_frames': live,
              'max_live_court_point_displacement_px': max_displacement,
              'max_abs_heldout_net_depth_residual_m': max_heldout,
              'screening_rule': 'For this bounded snapshot screen, keep the staged geometry when each live frame registers and its fitted court-point displacement is under 2 px, and the independently marked net floor line differs by under 0.2 m from court y=9 at x=0..9 m.',
              'screening_rule_passed': len(live) == 8 and max_displacement < 2 and max_heldout < .2,
              'limitations': ['A single held-out net line is not an independent whole-court reprojection error distribution.',
                              'The thresholds are operational screening criteria, not a measured uncertainty interval.',
                              'Wall registration and visual court overlays cannot validate individual shoe-floor clicks.',
                              'Set 3 inherits the set 2 transform because the static scene remains aligned, but has no new independently marked net line.',
                              'Set 1 point 39 has a real encoded-image alignment offset; physical camera motion is unproven. Its pre-serve snapshot is excluded and later metrics cannot reuse the uncorrected transform.']}
    if not result['screening_rule_passed']:
        result['status'] = 'bounded_court_geometry_check_failed'
    OUT.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    lines = '\n'.join(f"| {r['set']} | {r['point_number']} | {r['frame']} | "
                      f"{r['max_fitted_court_point_displacement_px']:.3f} | {r['static_wall_inliers']} |"
                      for r in live)
    REPORT.write_text(f'''# ProVolley court calibration quality check

The staged [set-one transform](../data/matches/yt_FqE5pTJqx8g/pilot/calibration/camera_r1.json) and [set-two/three transform](../data/matches/yt_FqE5pTJqx8g/pilot/calibration/camera_r2_r5.json) map the near baseline to y=0 m, the attack line to y=6 m, and extrapolate to the net floor at y=9 m. The court is 9 m wide. The four fitted landmarks come from the baseline and attack-line intersections with the sidelines.

An independently marked net-floor line is the available held-out floor landmark. Its depth residual is **{camera_info['camera_r1']['heldout_net_line_depth_residual_m']['0']:+.3f} to {camera_info['camera_r1']['heldout_net_line_depth_residual_m']['9']:+.3f} m** across set one's court width and **{camera_info['camera_r2_r5']['heldout_net_line_depth_residual_m']['0']:+.3f} to {camera_info['camera_r2_r5']['heldout_net_line_depth_residual_m']['9']:+.3f} m** for the set-two/three transform. These are line residuals, not errors in player positions.

The [61-frame static-background check](HONOURS_CAMERA_STABILITY_AUDIT.md) registered all saved sample frames. For the [eight live-play court candidates](HONOURS_CANDIDATE_PHASE_QC.md), the largest fitted court-point movement relative to its reference was **{max_displacement:.3f} px**. The representative [exact-frame overlays](../data/processed/honours_court_alignment_sheets/manifest.json) show the staged lines on source frames in all three sets.

| Set | Point | Live frame | Maximum fitted court-point displacement (px) | Static-wall inliers |
| ---: | ---: | ---: | ---: | ---: |
{lines}

**Bounded geometry decision:** {'Pass' if result['screening_rule_passed'] else 'Fail'} the operational screen of under 2 px camera displacement on each live frame and under 0.2 m held-out net-line depth residual over x=0..9 m. This supports using the existing transforms as *staged court geometry for these eight snapshots*. It does not approve an individual foot click or a final metre-valued team metric. Set 3 shares the set-two transform because its wall registration remains within the observed small movements; it has no separately marked held-out net line.

**Exception:** At set-one point 39, static wall features appear about 12 px left of their earlier pixel positions. This agrees across [SIFT registration](../data/processed/honours_camera_stability_audit.json), [phase correlation and ECC](../data/processed/honours_image_alignment_diagnostic/diagnostic.json), and the [direct source crop](../data/processed/honours_image_alignment_diagnostic/wall_checker_65656.jpg). **No physical camera movement is established.** Its only nominal six-player snapshot is [before the serve](HONOURS_CANDIDATE_PHASE_QC.md) and is excluded from live-play measurement. If a later frame from that point is analysed, it needs a source-frame-specific court transform or exclusion because its pixels differ from the calibration reference. The original calibration and player labels have not been altered.

**Remaining measurement gate:** Confirm the near-side team and six identities, check shoe-floor contacts against the source, and choose comparable live phases. The current strict metric calculator still has zero final eligible frames. No outcome association follows from this calibration screen.
''', encoding='utf-8')
    print(result['status'], max_displacement, max_heldout)


if __name__ == '__main__':
    main()
