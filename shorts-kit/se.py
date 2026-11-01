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


def bgm(dur, bpm=84, seed=3):
    """控えめな BGM(合成・外部素材なし)。Am7 → Fmaj7 → Cmaj7 → G6 の繰り返し。
    やわらかいパッド + ゆっくりの分散和音 + 低いベース + 小さなキックとシェイカー。最初と最後は音量を絞る。"""
    r = np.random.default_rng(seed)
    t = _t(dur)
    beat = 60 / bpm
    bar = beat * 4
    chords = [[57, 60, 64, 67], [53, 57, 60, 64], [48, 55, 59, 64], [55, 59, 62, 64]]   # MIDI 番号
    hz = lambda m: 440 * 2 ** ((m - 69) / 12)
    out = np.zeros_like(t)
    n_bars = int(np.ceil(dur / bar))
    for b_ in range(n_bars):
        ch = chords[b_ % 4]
        t0 = b_ * bar
        i0, i1 = int(t0 * SR), min(len(t), int((t0 + bar + 0.3) * SR))
        tt = t[i0:i1] - t0
        env = np.minimum(1, tt / 0.5) * np.exp(-np.maximum(0, tt - bar) * 8)
        pad = sum(np.sin(2 * np.pi * hz(m) * tt) + 0.3 * np.sin(2 * np.pi * 2 * hz(m) * tt + 0.3) for m in ch)
        out[i0:i1] += 0.08 * pad * env
        bass = np.sin(2 * np.pi * hz(ch[0] - 12) * tt)   # スマホのスピーカーでも聞こえる高さ * np.minimum(1, tt / 0.05) * np.exp(-tt * 0.9)
        out[i0:i1] += 0.22 * bass
        for k in range(8):                     # 8 分音符の分散和音
            ts = t0 + k * beat / 2
            m = ch[[0, 2, 1, 3, 2, 1, 3, 2][k]] + 12
            j0 = int(ts * SR)
            if j0 >= len(t):
                break
            n = min(int(0.6 * SR), len(t) - j0)
            u = np.arange(n) / SR
            out[j0:j0 + n] += 0.09 * np.sin(2 * np.pi * hz(m) * u) * np.exp(-u * 6) * (0.8 + 0.2 * r.random())
        for k in range(4):                     # キック(1・3 拍)とシェイカー(裏拍)
            ts = t0 + k * beat
            j0 = int(ts * SR)
            if j0 >= len(t):
                break
            if k in (0, 2):
                n = min(int(0.25 * SR), len(t) - j0)
                u = np.arange(n) / SR
                out[j0:j0 + n] += 0.25 * np.sin(2 * np.pi * (45 + 60 * np.exp(-u * 30)) * u) * np.exp(-u * 14)
            j1 = int((ts + beat / 2) * SR)
            if j1 < len(t):
                n = min(int(0.06 * SR), len(t) - j1)
                out[j1:j1 + n] += 0.03 * _lowpass(r.standard_normal(n), 7000) * np.exp(-np.arange(n) / SR * 60)
    fade = np.minimum(1, np.minimum(t / 0.8, (dur - t) / 1.5))
    return _norm(out * np.clip(fade, 0, 1), 0.5)


def _room(x, tail=1.1, wet=0.28, seed=11):
    """小さな部屋の残響(減衰するノイズを畳み込む)。音に厚みと広がりを足す。"""
    r = np.random.default_rng(seed)
    n = int(tail * SR)
    ir = r.standard_normal(n) * np.exp(-np.arange(n) / SR * (6.9 / tail))
    ir = _lowpass(ir, 5000)
    ir /= np.sqrt(np.sum(ir ** 2))
    m = len(x) + n - 1
    size = 1 << (m - 1).bit_length()
    y = np.fft.irfft(np.fft.rfft(x, size) * np.fft.rfft(ir, size), size)[:m]
    out = np.concatenate([x, np.zeros(n - 1)])
    return out * (1 - wet) + y * wet * (np.max(np.abs(x)) / (np.max(np.abs(y)) or 1))


def swish(dur=0.45):
    """ペンで線を引く音(高めの帯域のノイズが通り過ぎる)。線・パターンを描く所。"""
    t = _t(dur)
    env = np.sin(np.pi * np.minimum(1, t / dur)) ** 1.5
    x = _lowpass(rng.standard_normal(len(t)), 1500 + 6500 * t / dur)
    x = x - _lowpass(x, 900)                  # 低い所を削ってこすれる音に
    return _norm(_room(x * env, 0.5, 0.2), 0.42)


def tape(dur=1.8):
    """早送り(チャートを流す所)。細かいカチカチが速くなり、空気の音が上がっていく。"""
    t = _t(dur)
    out = np.zeros_like(t)
    pos, gap = 0.0, 0.09
    while pos < dur - 0.02:
        i, n = int(pos * SR), int(0.012 * SR)
        out[i:i + n] += np.sin(2 * np.pi * 3200 * np.arange(n) / SR) * np.exp(-np.arange(n) / SR * 400) * 0.5
        pos += gap
        gap = max(0.03, gap * 0.93)
    air = _lowpass(rng.standard_normal(len(t)), 400 + 5000 * (t / dur) ** 1.5) * (t / dur) * 0.6
    fade = np.minimum(1, (dur - t) / 0.08)
    return _norm(_room((out + air) * fade, 0.6, 0.18), 0.5)


def boom(dur=0.9):
    """重い衝撃(ネックラインを抜けて落ちる所)。低い沈み込み + 割れる音 + 残響。"""
    t = _t(dur)
    f = 90 * np.exp(-t * 5) + 34
    sub = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 4)
    crack = _lowpass(rng.standard_normal(len(t)), 3500) * np.exp(-t * 35)
    x = np.tanh(2.5 * (sub + 0.6 * crack))
    return _norm(_room(x, 1.2, 0.3), 0.95)


def fail(dur=0.5):
    """だめ(× の所)。低い 2 音が下がる、こもった音。"""
    t = _t(dur)
    out = np.zeros_like(t)
    for k, f in enumerate([233.1, 174.6]):
        d = int(k * 0.16 * SR)
        tt = t[: len(t) - d]
        sq = np.tanh(4 * np.sin(2 * np.pi * f * tt))
        out[d:] += _lowpass(sq, 1400) * np.exp(-tt * 9)
    return _norm(_room(out, 0.5, 0.15), 0.6)


def chime(dur=1.2):
    """エントリーの合図。鐘のような倍音(整数倍からずらす)+ 残響。"""
    t = _t(dur)
    x = np.zeros_like(t)
    for f, a, dk in [(1760, 1.0, 3.5), (1760 * 2.76, 0.45, 6), (1760 * 5.4, 0.2, 9), (880, 0.35, 3)]:
        x += a * np.sin(2 * np.pi * f * t) * np.exp(-t * dk)
    x *= np.minimum(1, t / 0.003)
    return _norm(_room(x, 1.0, 0.3), 0.5)


def tick(dur=0.06):
    """段階が変わる・文字が出る所の小さな音。"""
    t = _t(dur)
    x = np.sin(2 * np.pi * 2400 * t) * np.exp(-t * 120) + 0.4 * _lowpass(rng.standard_normal(len(t)), 6000) * np.exp(-t * 200)
    return _norm(_room(x, 0.3, 0.15), 0.4)


def sparkle(dur=1.4):
    """きらっ(3段目に届いた所・まとめの最後)。上がっていく高い音の粒 + 残響。"""
    t = _t(dur)
    out = np.zeros_like(t)
    for k, f in enumerate([1568, 2093, 2637, 3136, 4186, 5274]):
        d = int(k * 0.045 * SR)
        tt = t[: len(t) - d]
        out[d:] += np.sin(2 * np.pi * f * tt) * np.exp(-tt * 6) * (0.85 ** k)
    return _norm(_room(out, 1.2, 0.35), 0.42)


def dive(dur=2.4):
    """下へ加速していく音(3段目まで落ちる所)。下がる音程 + 強くなる空気の音。"""
    t = _t(dur)
    f = 900 * (0.18 ** (t / dur))
    tone = np.sin(2 * np.pi * np.cumsum(f) / SR)
    air = _lowpass(rng.standard_normal(len(t)), 300 + 3000 * t / dur)
    env = (t / dur) ** 1.2 * np.minimum(1, (dur - t) / 0.05)
    return _norm(_room((0.5 * tone + 0.6 * air) * env, 0.6, 0.2), 0.45)


SOUNDS = {"logo": logo, "riser": riser, "whoosh": whoosh, "pop": pop, "impact": impact, "kira": kira, "drumroll": drumroll,
          "ding": ding, "swish": swish, "tape": tape, "boom": boom, "fail": fail, "chime": chime, "tick": tick,
          "sparkle": sparkle, "dive": dive}


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
