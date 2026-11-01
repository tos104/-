#!/usr/bin/env python3
"""参考動画を実測する(スタイルガイドに書く前の数値)。

  python3 measure_ref.py video.mp4 [...] --sheet-dir out/ [--json out.json]

測るもの: 尺・解像度・fps / カット数と平均ショット長(ffmpeg scdet) / 動きの量(隣のコマとの差の平均)
/ 主な色5つ(k-means・乱数固定) / 明るさの平均 / ラウドネス LUFS・トゥルーピーク / 音の立ち上がりの数(毎秒)
/ 1秒ごとのコンタクトシート
"""
import argparse, json, os, re, subprocess
import numpy as np

W, H = 96, 96  # 色と動きは縮小して測る


def probe(p):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,width,height,r_frame_rate:format=duration",
                          "-of", "json", p], capture_output=True, text=True).stdout
    d = json.loads(out)
    v = next(s for s in d["streams"] if s["codec_type"] == "video")
    n, den = map(int, v["r_frame_rate"].split("/"))
    return float(d["format"]["duration"]), v["width"], v["height"], round(n / den, 2), any(s["codec_type"] == "audio" for s in d["streams"])


def frames(p, fps=10):
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", p, "-vf", f"fps={fps},scale={W}:{H}", "-f", "rawvideo",
                          "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(-1, H, W, 3).astype(np.float32)


def cuts(p, thr=0.1, merge=0.4):
    """thr=0.1: 18-hanazi(目視で4カット)で合わせた値。0.4秒以内の連続検出は1つにまとめる"""
    err = subprocess.run(["ffmpeg", "-i", p, "-vf", f"scdet=threshold={thr*100}", "-an", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    out = []
    for t in (float(x) for x in re.findall(r"lavfi\.scd\.time:\s*([\d.]+)", err)):
        if t > 0.1 and (not out or t - out[-1] > merge):
            out.append(t)
    return out


def palette(f, k=5):
    px = f[::2].reshape(-1, 3)
    rng = np.random.default_rng(0)
    c = px[rng.choice(len(px), k, replace=False)]
    for _ in range(15):
        lab = np.argmin(((px[:, None] - c[None]) ** 2).sum(2), 1)
        c = np.array([px[lab == i].mean(0) if (lab == i).any() else c[i] for i in range(k)])
    share = np.bincount(lab, minlength=k) / len(lab)
    o = np.argsort(-share)
    return [("#%02x%02x%02x" % tuple(int(v) for v in c[i]), round(float(share[i]), 2)) for i in o]


def loud(p):
    err = subprocess.run(["ffmpeg", "-i", p, "-af", "ebur128=peak=true", "-f", "null", "-"], capture_output=True, text=True).stderr
    i = re.findall(r"I:\s*(-?[\d.]+) LUFS", err)
    tp = re.findall(r"Peak:\s*(-?[\d.]+) dBFS", err)
    return (float(i[-1]) if i else None, float(tp[-1]) if tp else None)


def onsets(p, sr=22050, hop=512):
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", p, "-ac", "1", "-ar", str(sr), "-f", "f32le", "-"], capture_output=True).stdout
    x = np.frombuffer(raw, np.float32)
    if len(x) < sr:
        return 0
    e = np.sqrt(np.convolve(x ** 2, np.ones(hop) / hop, mode="valid")[::hop])
    d = np.maximum(0, np.diff(np.log1p(e * 50)))
    thr = d.mean() + 2 * d.std()
    peaks = [i for i in range(1, len(d) - 1) if d[i] > thr and d[i] >= d[i - 1] and d[i] >= d[i + 1]]
    return len(peaks) / (len(x) / sr)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("videos", nargs="+")
    ap.add_argument("--sheet-dir")
    ap.add_argument("--json")
    a = ap.parse_args()
    res = []
    for p in a.videos:
        dur, w, h, fps, has_a = probe(p)
        f = frames(p)
        motion = float(np.abs(np.diff(f, axis=0)).mean()) if len(f) > 1 else 0
        c = cuts(p)
        lufs, tp = loud(p) if has_a else (None, None)
        r = {"name": os.path.basename(p), "sec": round(dur, 2), "size": f"{w}x{h}", "fps": fps,
             "cuts": len(c), "shot_sec": round(dur / (len(c) + 1), 2), "motion": round(motion, 1),
             "bright": round(float(f.mean()), 0), "palette": palette(f), "lufs": lufs, "true_peak": tp,
             "onsets_per_sec": round(onsets(p), 1) if has_a else None}
        res.append(r)
        print(json.dumps(r, ensure_ascii=False))
        if a.sheet_dir:
            os.makedirs(a.sheet_dir, exist_ok=True)
            n = int(dur) or 1
            cols = min(n, 10)
            sw = 192 if w >= h else 108
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", p, "-vf",
                            f"fps=1,scale={sw}:-2,tile={cols}x{-(-n // cols)}", "-frames:v", "1",
                            os.path.join(a.sheet_dir, os.path.splitext(r["name"])[0] + ".jpg")], check=True)
    if a.json:
        json.dump(res, open(a.json, "w"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
