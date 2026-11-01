#!/usr/bin/env python3
"""曲の拍(BPMと1拍目の位置)を検出する。numpyだけ・乱数なし。

  python3 kinetic/beat_detect.py song.mp3   → {"bpm":..., "offset":...}
"""
import json, subprocess, sys
import numpy as np

SR = 22050
HOP = 256


def load(path):
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", path, "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32)


N = 1024


def onset_env(x):
    """全帯域と低音域(〜200Hz=キック)の立ち上がりの強さ。env[i] は時刻 i*HOP/SR に対応させる"""
    frames = np.lib.stride_tricks.sliding_window_view(x, N)[::HOP] * np.hanning(N)
    mag = np.log1p(np.abs(np.fft.rfft(frames, axis=1)) * 10)
    d = np.maximum(0, np.diff(mag, axis=0))
    low = int(200 / (SR / N)) + 1
    out = []
    for flux in (d.sum(1), d[:, :low].sum(1)):
        flux = flux - np.convolve(flux, np.ones(32) / 32, mode="same")  # ゆっくりした変化を除く
        flux = np.concatenate([np.zeros(N // 2 // HOP + 1), np.maximum(flux, 0)])  # 窓の中心に時刻をそろえる
        out.append(flux)
    return out


def detect(path, lo=70, hi=180):
    env, low = onset_env(load(path))
    fps = SR / HOP
    ac = np.correlate(env, env, mode="full")[len(env) - 1:]
    best, bpm = -1, 120.0
    for b in np.arange(lo, hi, 0.25):  # 拍の候補ごとに、その周期(と倍の周期)の相関を見る
        lag = fps * 60 / b
        s = np.interp(lag, np.arange(len(ac)), ac) + 0.5 * np.interp(lag * 2, np.arange(len(ac)), ac)
        s *= np.exp(-0.5 * (np.log2(b / 120) / 0.9) ** 2)  # 120BPM付近を少し優先(半分・倍の取り違え対策)
        if s > best:
            best, bpm = s, b
    period = fps * 60 / bpm
    ph_env = low / (low.max() or 1) + 0.3 * env / (env.max() or 1)  # 1拍目の位置は低音(キック)を重く見る
    scores = [ph_env[np.round(np.arange(ph, len(ph_env) - 1, period)).astype(int)].sum() for ph in np.arange(0, period, 0.5)]
    offset = np.arange(0, period, 0.5)[int(np.argmax(scores))] / fps
    return {"bpm": round(float(bpm), 2), "offset": round(float(offset), 3)}


if __name__ == "__main__":
    print(json.dumps(detect(sys.argv[1])))
