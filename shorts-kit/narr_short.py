#!/usr/bin/env python3
"""台本(JSON)から、既存映像 + 合成ナレーション + 字幕のショートを作る。

台本の形式:
{
  "header": "240万の|青眼トレード",          # 上部に固定表示("|"で改行)
  "lines": [
    {"src": "01:30", "say": "読み上げ文", "cap": "画面の字幕", "hl": "赤くする語"},
    ...
  ]
}
各行の映像は src から読み上げの長さぶん切り出して順につなぐ。元音声は使わない。
例: python3 narr_short.py script.json source.mp4 --out out/demo.mp4
"""
import argparse, json, os, subprocess, tempfile, wave
import numpy as np
import pyopenjtalk
from make_short import to_sec, ass_time, FONT

SR = 48000
GAP = 0.12  # 行間の無音(秒)


def tts(text, speed):
    x, sr = pyopenjtalk.tts(text, speed=speed, half_tone=1)
    assert sr == SR
    return np.clip(x, -32768, 32767).astype(np.int16)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("script")
    ap.add_argument("source")
    ap.add_argument("--out", required=True)
    ap.add_argument("--speed", type=float, default=1.3)
    a = ap.parse_args()
    sc = json.load(open(a.script, encoding="utf-8"))

    src_w, src_h = map(int, subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
         "-of", "csv=p=0", a.source], check=True, capture_output=True, text=True).stdout.strip().split(","))
    fg_w = 1080
    fg_h = int(fg_w * src_h / src_w) // 2 * 2
    fg_top = 330
    cap_top = fg_top + fg_h + 50

    with tempfile.TemporaryDirectory() as td:
        audio, events, parts, t = [], [], [], 0.0
        for i, ln in enumerate(sc["lines"]):
            v = tts(ln["say"], a.speed)
            v = np.concatenate([v, np.zeros(int(GAP * SR), np.int16)])
            dur = len(v) / SR
            audio.append(v)
            cap = ln.get("cap", ln["say"])
            if ln.get("hl"):
                cap = cap.replace(ln["hl"], "{\\c&H0030FF&\\fscx115\\fscy115}" + ln["hl"] + "{\\r}")
            events.append(f"Dialogue: 0,{ass_time(t)},{ass_time(t + dur)},Cap,,0,0,0,,{cap.replace('|', chr(92) + 'N')}")
            p = os.path.join(td, f"p{i:02d}.mp4")
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", str(to_sec(ln["src"])), "-t", f"{dur:.3f}",
                            "-i", a.source, "-an", "-vf", "fps=30,format=yuv420p", "-c:v", "libx264", "-crf", "16", p],
                           check=True)
            parts.append(p)
            t += dur

        wav = os.path.join(td, "narr.wav")
        with wave.open(wav, "wb") as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
            w.writeframes(np.concatenate(audio).tobytes())
        lst = os.path.join(td, "list.txt")
        open(lst, "w").write("".join(f"file '{p}'\n" for p in parts))

        ass = os.path.join(td, "sub.ass")
        header = sc.get("header", "").replace("|", "\\N")
        with open(ass, "w", encoding="utf-8") as f:
            f.write(f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Head,{FONT},104,&H0000E8FF,&H000000FF,&H00000000,&H00000000,1,0,0,0,100,100,0,0,1,9,0,8,30,30,70,1
Style: Cap,{FONT},88,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,1,0,0,0,100,100,0,0,1,8,0,8,40,40,{cap_top},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,{ass_time(0)},{ass_time(t)},Head,,0,0,0,,{header}
""" + "\n".join(events) + "\n")

        vf = (f"[0:v]split[a][b];"
              f"[a]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=30:2,eq=brightness=-0.25[bg];"
              f"[b]scale={fg_w}:{fg_h}:flags=lanczos,unsharp=5:5:0.6[fg];"
              f"[bg][fg]overlay=0:{fg_top},ass='{ass}',format=yuv420p[v]")
        os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst, "-i", wav,
                        "-filter_complex", vf, "-map", "[v]", "-map", "1:a", "-c:v", "libx264", "-crf", "20",
                        "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", a.out], check=True)
    print(f"{a.out} ({t:.1f}s)")


if __name__ == "__main__":
    main()
