#!/usr/bin/env python3
"""キネティック・タイポ(言葉を拍に置く映像)を、Webページ1枚から書き出す。

  python3 kinetic/render_kinetic.py kinetic/sample.json --out out.mp4 [--sheet sheet.png] [--bgm bgm.wav] [--music song.mp3]

--music: 曲の拍(BPM・1拍目)を検出し、言葉をその拍に合わせる。台本の bpm は上書きされる。
        曲は人が用意したもの(Suno で作って書き出した mp3 など)。検出結果は出力に表示する

台本(JSON):
  {"bpm": 120, "fps": 30, "hud": "右上の小さな文字(省略可)",
   "palette": [{"bg":"#ff3b1f","fg":"#111","accent":"#fff"}, ...],
   "beats": [{"text":"1〜2語", "len":1, "style":"slam|pop|tilt3d|slide|type",
              "pal":0, "cam":"push|pull|roll|whip|none", "burst":true, "stack":true,
              "ghost":"背景の大きな文字", "sub":"下の小さな字幕", "se":"tap", "why":"なぜこの拍があるか"}]}
映像と効果音は同じ拍の時刻から作る(ずれない)。乱数は使わない。
"""
import argparse, json, os, subprocess, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import se  # noqa: E402

SR = se.SR


def beat_times(s):
    beat, t, out = 60 / s["bpm"], s.get("offset", 0.0), []
    for b in s["beats"]:
        out.append(t)
        t += b.get("len", 1) * beat
    return out


def build_audio(s, total, path, bgm=None):
    mix = np.zeros(int(total * SR) + SR)
    for t, b in zip(beat_times(s), s["beats"]):
        name = b.get("se", s.get("default_se", "tap"))
        if not name:
            continue
        x = se.get(name) * b.get("se_gain", 0.6)
        i = int(t * SR)
        mix[i:i + len(x)] += x[:len(mix) - i]
    if bgm:
        raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", bgm, "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                             capture_output=True, check=True).stdout
        d = np.frombuffer(raw, np.float32).astype(float)
        n = min(len(d), len(mix))
        mix[:n] += d[:n] * 0.5
    mix = mix[:int(total * SR)]
    mix /= max(1.0, np.max(np.abs(mix)) / 0.95)  # 割れないよう全体を下げる
    se.write_wav(path, mix)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("script")
    ap.add_argument("--out", required=True)
    ap.add_argument("--sheet")
    ap.add_argument("--bgm")
    ap.add_argument("--music", help="拍を合わせる曲(--bgm を兼ねる)")
    a = ap.parse_args()
    s = json.load(open(a.script))
    s.setdefault("fps", 30)
    missing = [i for i, b in enumerate(s["beats"]) if not b.get("why")]
    if missing:
        sys.exit(f"why(なぜこの拍があるか)が無い拍: {missing}。言えない拍は削る")

    if a.music:
        sys.path.insert(0, HERE)
        from beat_detect import detect
        d = detect(a.music)
        s["bpm"], s["offset"] = d["bpm"], d["offset"]
        a.bgm = a.music
        print(f"拍の検出: {d['bpm']} BPM / 1拍目 {d['offset']}秒")
    total = s.get("offset", 0.0) + sum(b.get("len", 1) for b in s["beats"]) * 60 / s["bpm"] + s.get("tail", 0.6)  # kinetic.html の totalSec と同じ式
    n = int(round(total * s["fps"]))
    wav = a.out + ".se.wav"
    build_audio(s, total, wav, a.bgm)
    tmp = a.out + ".script.json"
    json.dump(s, open(tmp, "w"), ensure_ascii=False)
    env = dict(os.environ, NODE_PATH=os.environ.get("NODE_PATH") or subprocess.run(["npm", "root", "-g"], capture_output=True, text=True).stdout.strip())
    cap = subprocess.Popen(["node", os.path.join(HERE, "capture.js"), tmp, str(n)], stdout=subprocess.PIPE, env=env)
    ff = subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "image2pipe", "-framerate", str(s["fps"]),
         "-i", "-", "-i", wav, "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18",
         "-c:a", "aac", "-b:a", "192k", "-shortest", a.out], stdin=cap.stdout)
    rc = cap.wait() or ff.returncode
    os.remove(tmp)
    os.remove(wav)
    if rc:
        sys.exit(f"ffmpeg 失敗 rc={rc}")
    if a.sheet:  # 各拍の中ほどを1枚ずつ並べる
        mids = [t + 60 / s["bpm"] * b.get("len", 1) * 0.5 for t, b in zip(beat_times(s), s["beats"])]
        sel = "+".join(f"eq(n\\,{int(m * s['fps'])})" for m in mids)
        cols = min(6, len(mids))
        rows = -(-len(mids) // cols)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", a.out, "-vf",
                        f"select='{sel}',scale=270:480,tile={cols}x{rows}", "-frames:v", "1", a.sheet], check=True)
    print(f"{a.out}  {total:.2f}s  {n}frames  拍{len(s['beats'])}")


if __name__ == "__main__":
    main()
