"""Inspect a short, audio-enabled FqE match excerpt for tonal whistle cues."""
from pathlib import Path
import sys
import wave

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from scipy.signal import stft


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / (sys.argv[1] if len(sys.argv) > 1 else 'data/processed/fqe_serve_audio_probe.wav')
START = float(sys.argv[2]) if len(sys.argv) > 2 else 155.0
OUTPUT = SOURCE.with_name(SOURCE.stem + '_spectrogram.jpg')

with wave.open(str(SOURCE)) as wav:
    sr = wav.getframerate()
    signal = np.frombuffer(wav.readframes(wav.getnframes()), dtype=np.int16).astype(np.float32) / 32768

frequency, time, spectrum = stft(signal, sr, nperseg=1024, noverlap=768)
power = np.abs(spectrum)
mask = (frequency >= 1200) & (frequency <= 7000)
fig, ax = plt.subplots(figsize=(17, 6))
ax.pcolormesh(time + START, frequency[mask] / 1000, 20 * np.log10(power[mask] + 1e-6),
              shading='auto', vmin=-85, vmax=-25, cmap='magma')
ax.set(xlabel='Source video time (seconds)', ylabel='Frequency (kHz)',
       title='FqE audio excerpt: narrow tones can indicate whistles but require source review',
       xlim=(START, START + len(signal) / sr))
ax.set_xticks(np.arange(START, START + len(signal) / sr + 1, 2))
ax.grid(axis='x', alpha=.25)
fig.tight_layout()
fig.savefig(OUTPUT, dpi=140)
print(OUTPUT)
