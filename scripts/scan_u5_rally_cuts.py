"""Bind the edited U5 rally clips to visible scoreboard point changes.

The video has one hard cut immediately before each new displayed score. A clip
between two cuts contains the preceding rally and may include serve preparation
or post-point footage, so clip bounds are not asserted as live-ball bounds.
"""
import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'data/matches/yt_u5HnY2aNW14'
VIDEO = BASE / 'source_720p.mp4'
REGISTER = BASE / 'screening/point_register_candidate.json'
SAMPLE = BASE / 'screening/rally_sample_score_only.json'
OUT = BASE / 'screening/rally_cut_clip_register.json'
SCENE_THRESHOLD = 0.04
FPS = 30


def digest(path):
    sha = hashlib.sha256()
    with path.open('rb') as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b''):
            sha.update(chunk)
    return sha.hexdigest()


def detect_cuts():
    executable = shutil.which('ffmpeg')
    if executable is None:
        raise RuntimeError('ffmpeg is required for scene detection')
    command = [executable, '-nostdin', '-hide_banner', '-loglevel', 'info',
               '-i', str(VIDEO), '-vf', f"select='gt(scene,{SCENE_THRESHOLD})',showinfo",
               '-an', '-f', 'null', '-']
    run = subprocess.run(command, capture_output=True, text=True,
                         encoding='utf-8', errors='replace', check=False)
    if run.returncode:
        raise RuntimeError(f'ffmpeg scene scan failed: {run.stderr[-1200:]}')
    times = [float(match.group(1)) for line in run.stderr.splitlines()
             if 'Parsed_showinfo' in line
             for match in [re.search(r'pts_time:([0-9.]+)', line)] if match]
    frames = [round(t * FPS) for t in times]
    if frames != sorted(set(frames)):
        raise ValueError('Scene-cut frame sequence has duplicates or is unordered')
    version = subprocess.run([executable, '-version'], capture_output=True, text=True,
                             encoding='utf-8', errors='replace', check=True).stdout.splitlines()[0]
    return frames, version


def main():
    register = json.loads(REGISTER.read_text(encoding='utf-8'))
    sample = json.loads(SAMPLE.read_text(encoding='utf-8'))
    source_sha256 = digest(VIDEO)
    if not (source_sha256 == register['source_sha256'] == sample['source_sha256']):
        raise ValueError('Source video differs from score register or sample')
    cuts, ffmpeg_version = detect_cuts()
    events = register['events']
    expected = {e['score_change_previous_sample_second'] * FPS + 1:
                (e['set'], e['point_number']) for e in events}
    if len(expected) != len(events) or not set(expected) <= set(cuts):
        missing = sorted(set(expected) - set(cuts))
        raise ValueError(f'Score-event cuts missing or duplicated: {missing[:12]}')
    reset_cuts = [r['first_zero_second'] * FPS - FPS + 1
                  for r in register['set_resets']]
    extras = sorted(set(cuts) - set(expected))
    if extras != reset_cuts:
        raise ValueError(f'Unexpected scene cuts: {extras}; expected reset cuts: {reset_cuts}')
    selected = {(e['set'], e['point_number']) for e in sample['selected_events']}
    if len(selected) != 18:
        raise ValueError('Frozen sample does not have 18 unique events')
    rows = []
    for event in events:
        key = event['set'], event['point_number']
        end = event['score_change_previous_sample_second'] * FPS + 1
        index = cuts.index(end)
        start = cuts[index - 1] if index else 0
        if end <= start:
            raise ValueError(f'Empty point clip: {key}')
        rows.append({'set': key[0], 'point_number': key[1],
                     'winner_scoreboard_side': event['winner_scoreboard_side'],
                     'score_change_first_sample_second': event['score_change_first_sample_second'],
                     'clip_start_frame_inclusive': start,
                     'clip_end_frame_exclusive': end,
                     'clip_start_second': round(start / FPS, 3),
                     'clip_end_second': round(end / FPS, 3),
                     'clip_duration_seconds': round((end - start) / FPS, 3),
                     'in_frozen_sample': key in selected,
                     'boundary_status': 'score_aligned_hard_cuts_not_live_ball_boundaries'})
    selected_rows = [r for r in rows if r['in_frozen_sample']]
    if {(r['set'], r['point_number']) for r in selected_rows} != selected:
        raise ValueError('Selected clip set differs from frozen sample')
    result = {
        'status': 'score_aligned_edited_rally_clip_boundaries',
        'source_sha256': source_sha256,
        'point_register_sha256': digest(REGISTER),
        'frozen_sample_sha256': digest(SAMPLE),
        'ffmpeg_version': ffmpeg_version,
        'method': f'ffmpeg select=gt(scene,{SCENE_THRESHOLD}) at {FPS} fps; require one cut exactly one frame after the previous sampled score second for each visible +1 event; require two remaining cuts at set resets',
        'scene_threshold': SCENE_THRESHOLD,
        'fps': FPS,
        'summary': {'detected_cuts': len(cuts), 'point_change_cuts': len(events),
                    'set_reset_cuts': len(reset_cuts), 'frozen_sample_clips': len(selected_rows),
                    'score_events_without_matching_cut': 0, 'unexpected_cuts': 0},
        'set_reset_cut_frames': reset_cuts,
        'cut_frames': cuts,
        'selected_clips': selected_rows,
        'all_visible_point_clips': rows,
        'limitations': [
            'A hard cut separates edited rally clips, but it does not identify serve contact or dead-ball frame inside the clip.',
            'The match recording may omit the last point of a set; only the 122 visible +1 events are mapped.',
            'Score reading and cut interpretation were reviewed by one analyst, not an independent observer.',
            'The cut threshold is source-specific and must be rescanned if the video file changes.'
        ]
    }
    OUT.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(result['summary'])
    for row in selected_rows:
        print(f"S{row['set']} P{row['point_number']}: "
              f"[{row['clip_start_second']:.3f}, {row['clip_end_second']:.3f}) s")


if __name__ == '__main__':
    main()
