import argparse
from pathlib import Path
import numpy as np


def read_wav(path: Path):
    import wave

    with wave.open(str(path), "rb") as wf:
        nchan = wf.getnchannels()
        sampwidth = wf.getsampwidth()
        fr = wf.getframerate()
        nframes = wf.getnframes()
        raw = wf.readframes(nframes)

    dtype = np.int16 if sampwidth == 2 else np.float32
    y = np.frombuffer(raw, dtype=dtype).astype(np.float32)
    if nchan > 1:
        y = y.reshape(-1, nchan).mean(axis=1)
    if sampwidth == 2:
        y /= 32768.0
    return y, fr


def detect_whistles(
    y,
    sr,
    frame_ms=30.0,
    hop_ms=10.0,
    z_thresh=3.0,
    merge_ms=250.0,
    bp_low_khz=3.0,
    bp_high_khz=5.0,
    ratio_min=0.5,
    hp_cut_khz=None,
):
    win = int(round(sr * frame_ms / 1000.0))
    hop = int(round(sr * hop_ms / 1000.0))
    if win < 16:
        win = 16
    if hop < 1:
        hop = 1
    if len(y) < win:
        return []

    # Pre-emphasis
    y2 = y - 0.97 * np.concatenate([[0.0], y[:-1]])

    if hp_cut_khz and hp_cut_khz > 0:
        fc = float(hp_cut_khz) * 1000.0
        dt = 1.0 / sr
        rc = 1.0 / (2.0 * np.pi * fc)
        alpha = rc / (rc + dt)
        hp = np.empty_like(y2)
        prev_y = 0.0
        prev_x = y2[0]
        for i in range(len(y2)):
            x = y2[i]
            prev_y = alpha * (prev_y + x - prev_x)
            hp[i] = prev_y
            prev_x = x
        y2 = hp

    frames = []
    for start in range(0, len(y2) - win + 1, hop):
        frames.append(y2[start : start + win])
    F = np.stack(frames, axis=0)
    F *= np.hanning(win).astype(np.float32)[None, :]

    X = np.fft.rfft(F, axis=1)
    mag = (X.real ** 2 + X.imag ** 2)

    freqs = np.fft.rfftfreq(win, d=1.0 / sr)
    lo = bp_low_khz * 1000.0
    hi = bp_high_khz * 1000.0
    band = (freqs >= lo) & (freqs <= hi)
    band_energy = mag[:, band].sum(axis=1)
    total_energy = np.maximum(1e-12, mag.sum(axis=1))
    ratio = band_energy / total_energy

    mu = float(np.mean(ratio))
    sd = float(np.std(ratio) + 1e-6)
    z = (ratio - mu) / sd

    idx = np.where((z >= z_thresh) & (ratio >= ratio_min))[0]
    if idx.size == 0:
        return []
    times = idx * (hop / sr)
    merged = []
    cur_start = times[0]
    last = times[0]
    max_gap = merge_ms / 1000.0
    for t in times[1:]:
        if t - last <= max_gap:
            last = t
        else:
            merged.append((cur_start + last) * 0.5)
            cur_start = last = t
    merged.append((cur_start + last) * 0.5)
    return merged


def main():
    ap = argparse.ArgumentParser(description="Debug whistle detection by printing detected times.")
    ap.add_argument("wav", help="Path to WAV file")
    ap.add_argument("--frame_ms", type=float, default=30.0)
    ap.add_argument("--hop_ms", type=float, default=10.0)
    ap.add_argument("--z_thresh", type=float, default=3.0)
    ap.add_argument("--merge_ms", type=float, default=250.0)
    ap.add_argument("--bp_low_khz", type=float, default=3.0)
    ap.add_argument("--bp_high_khz", type=float, default=5.0)
    ap.add_argument("--ratio_min", type=float, default=0.5)
    ap.add_argument("--hp_cut_khz", type=float, default=0.0)
    args = ap.parse_args()

    wav_path = Path(args.wav)
    y, sr = read_wav(wav_path)
    times = detect_whistles(
        y,
        sr,
        frame_ms=args.frame_ms,
        hop_ms=args.hop_ms,
        z_thresh=args.z_thresh,
        merge_ms=args.merge_ms,
        bp_low_khz=args.bp_low_khz,
        bp_high_khz=args.bp_high_khz,
        ratio_min=args.ratio_min,
        hp_cut_khz=args.hp_cut_khz if args.hp_cut_khz > 0 else None,
    )
    if not times:
        print("No whistles detected.")
    else:
        print("Whistle times (s):", ", ".join(f"{t:.3f}" for t in times))


if __name__ == "__main__":
    main()
