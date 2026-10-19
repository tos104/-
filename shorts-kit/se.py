#!/usr/bin/env python3
"""効果音をその場で合成する(外部素材なし・権利フリー)。48kHz mono int16。

  python3 se.py out_dir   # 全SEをwavで書き出す(試聴用)
"""
import os, sys, wave
import numpy as np

SR = 48000
rng = np.random.default_rng(7)


def _t(sec):
    return np.arange(int(sec * SR)) / SR


def _lowpass(x, cutoff):
    """cutoff はスカラーか配列(サンプルごと)。1次IIR。"""
    a = np.exp(-2 * np.pi * np.broadcast_to(cutoff, x.shape) / SR)
    y = np.empty_like(x)
    prev = 0.0
    for i in range(len(x)):
        prev = (1 - a[i]) * x[i] + a[i] * prev
        y[i] = prev
    return y


def _norm(x, peak=0.9):
    m = np.max(np.abs(x)) or 1
    return x / m * peak


def whoosh(dur=0.32):
    t = _t(dur)
    env = np.sin(np.pi * t / dur) ** 2
    cutoff = 300 + 5000 * np.sin(np.pi * t / dur)
    return _norm(_lowpass(rng.standard_normal(len(t)), cutoff) * env, 0.5)


def pop(dur=0.09):
    t = _t(dur)
    f = 950 * np.exp(-t * 18) + 380
    return _norm(np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 45), 0.55)


def impact(dur=0.7):
    t = _t(dur)
    f = 70 * np.exp(-t * 3) + 38
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 6)
    click = _lowpass(rng.standard_normal(len(t)), 2500) * np.exp(-t * 60)
    return _norm(np.tanh(2.2 * (body + 0.8 * click)), 0.95)


def kira(dur=0.9):
    t = _t(dur)
    out = np.zeros_like(t)
    for k, f in enumerate([2093, 2637, 3136, 4186]):
        d = int(k * 0.055 * SR)
        tt = t[: len(t) - d]
        out[d:] += np.sin(2 * np.pi * f * tt) * np.exp(-tt * 7) * (0.8 ** k)
    return _norm(out, 0.4)


def drumroll(dur=0.9):
    t = _t(dur)
    out = np.zeros_like(t)
    pos, gap = 0.0, 0.07
    while pos < dur - 0.03:
        i = int(pos * SR)
        n = int(0.03 * SR)
        hit = _lowpass(rng.standard_normal(n), 1800) * np.exp(-np.arange(n) / SR * 90)
        out[i:i + n] += hit * (0.3 + 0.7 * pos / dur)
        pos += gap
        gap = max(0.028, gap * 0.9)
    return _norm(out, 0.6)


def ding(dur=1.0):
    t = _t(dur)
    x = np.sin(2 * np.pi * 1318.5 * t) + 0.5 * np.sin(2 * np.pi * 2637 * t) + 0.25 * np.sin(2 * np.pi * 3955 * t)
    return _norm(x * np.exp(-t * 4.5), 0.45)


def logo(dur=0.95):
    """サウンドロゴ: 毎回同じ3音(ミ→ソ→ド)。単純接触で『このチャンネルの音』として覚えてもらう。"""
    t = _t(dur)
    out = np.zeros_like(t)
    for k, f in enumerate([1318.5, 1568.0, 2093.0]):
        d = int(k * 0.11 * SR)
        tt = t[: len(t) - d]
        tone = np.sin(2 * np.pi * f * tt) + 0.35 * np.sin(2 * np.pi * 2 * f * tt) + 0.12 * np.sin(2 * np.pi * 3 * f * tt)
        out[d:] += tone * np.exp(-tt * (5 if k == 2 else 9))
    return _norm(out, 0.5)


def riser(dur=1.0):
    """上昇音: クライマックス前の転調・溜め。"""
    t = _t(dur)
    f = 250 * (8 ** (t / dur))
    tone = np.sin(2 * np.pi * np.cumsum(f) / SR)
    air = _lowpass(rng.standard_normal(len(t)), 600 + 6000 * t / dur)
    return _norm((tone * 0.6 + air * 0.5) * (t / dur) ** 2, 0.5)


SOUNDS = {"logo": logo, "riser": riser, "whoosh": whoosh, "pop": pop, "impact": impact, "kira": kira, "drumroll": drumroll, "ding": ding}


def get(name):
    return SOUNDS[name]()


def to_int16(x):
    return (np.clip(x, -1, 1) * 32767).astype(np.int16)


def write_wav(path, x):
    with wave.open(path, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes(to_int16(x).tobytes())


if __name__ == "__main__":
    out = sys.argv[1]
    os.makedirs(out, exist_ok=True)
    demo = []
    for n in SOUNDS:
        x = get(n)
        write_wav(os.path.join(out, f"se_{n}.wav"), x)
        demo += [x, np.zeros(int(0.35 * SR))]
    write_wav(os.path.join(out, "se_all.wav"), np.concatenate(demo))
    print("written:", ", ".join(SOUNDS))
