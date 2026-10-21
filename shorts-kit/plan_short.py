#!/usr/bin/env python3
"""カット割り設計図(JSON)どおりにショートを作る。全画面 9:16・本人の声・倍速・ジェットカット。

設計図の形式:
{
  "header": "240万の青眼と交換する生贄",   # 上部の黒帯に常時表示({}は強調色)
  "speed": 1.25,
  "cuts": [
    {"a": ["02:22.5", "02:26.5"],          # 声(元動画の秒)
     "v": "05:55.0",                       # 映像だけ別の位置から(省略すると声と同じ位置)
     "cx": 280, "pan": [200, 330],         # 切り取りの横中心(元動画の px)。pan は左→右
     "z": 1.0,                             # 1.0 = 元動画の高さいっぱい
     "cap": "240万円する|PSA10のレリーフ",   # | で改行、{} で強調
     "se": "kira"}                          # se.py の名前(省略で無音)
  ]
}
  python3 plan_short.py plan.json source.mp4 --out out.mp4
"""
import argparse, json, os, re, subprocess, tempfile
import numpy as np
import se
import rich_short as rs
from make_short import to_sec, ass_time

SR = rs.SR
W, H = 1080, 1920
BAND_TOP = 390           # 上の黒帯(元動画の上テロップとロゴを隠す)
GLASS_TOP = 1300         # 下のすりガラス帯(元動画の下テロップを隠す)
CAP_Y = 1470
JET_MIN, JET_PAD = 0.15, 0.03  # 0.15 秒以上の間を詰める。声の前後に 0.03 秒残す


def crop_filter(src_w, src_h, cx, z, pan, dur):
    ch = int(src_h / z) // 2 * 2
    cw = int(ch * 9 / 16) // 2 * 2
    lo, hi = cw / 2, src_w - cw / 2
    if pan:
        x0, x1 = (min(max(p, lo), hi) - cw / 2 for p in pan)
        x = f"{x0:.1f}+({x1 - x0:.1f})*t/{dur:.3f}"
    else:
        x = f"{min(max(cx, lo), hi) - cw / 2:.1f}"
    y = (src_h - ch) / 2
    return f"crop={cw}:{ch}:'{x}':{y:.0f},scale={W}:{H}:flags=lanczos,unsharp=5:5:0.5"


def colorize(text):
    return re.sub(r"\{(.+?)\}", lambda m: f"{{\\c{rs.YELLOW}}}{m.group(1)}{{\\c{rs.WHITE}}}", text.replace("|", "\\N"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("plan")
    ap.add_argument("source")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    plan = json.load(open(a.plan, encoding="utf-8"))
    speed = plan.get("speed", 1.0)
    src_w, src_h = rs.probe(a.source)
    rs.JET_MIN, rs.JET_PAD = JET_MIN, JET_PAD

    with tempfile.TemporaryDirectory() as td:
        parts, audio, events, t = [], [], [], 0.0
        for i, c in enumerate(plan["cuts"]):
            a0, a1 = to_sec(c["a"][0]), to_sec(c["a"][1])
            spans = rs.speech_spans(a.source, a0, a1) if c.get("jet", True) else [(a0, a1)]
            voice = np.concatenate([rs.source_audio(a.source, s0, s1) for s0, s1 in spans])
            src_len = len(voice) / SR
            # 映像: 別の位置を被せるときは連続した映像、そうでなければ声と同じ区間(ジャンプカット)
            vsegs = [(to_sec(c["v"]), to_sec(c["v"]) + src_len)] if c.get("v") else spans
            frames = 0  # 長さはコマ数で数える(秒のまま足すと端数がたまり、字幕と映像がずれる)
            for k, (v0, v1) in enumerate(vsegs):
                d = v1 - v0
                n = max(1, round(d / speed * 30))
                p = os.path.join(td, f"p{i:02d}_{k:02d}.mp4")
                vf = (f"{crop_filter(src_w, src_h, c.get('cx', src_w / 2), c.get('z', 1.0), c.get('pan'), d)},"
                      f"setpts=PTS/{speed},fps=30,tpad=stop_mode=clone:stop_duration=1,format=yuv420p")
                subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{v0:.3f}", "-t", f"{d + 0.2:.3f}",
                                "-i", a.source, "-an", "-vf", vf, "-frames:v", str(n),
                                "-c:v", "libx264", "-crf", "16", p], check=True)
                parts.append(p)
                frames += n
            dur = frames / 30
            audio.append((t, voice, c.get("se")))
            events.append((t, t + dur, c.get("cap", "")))
            t += dur
        total = t
        # 読み切れる時間の確認: 日本語は 1 秒 8 文字 + 認識に 0.3 秒(目安)
        for s_, e_, cap in events:
            n = len(re.sub(r"[{}|]", "", cap))
            need = n / 8 + 0.3
            if cap and e_ - s_ < need:
                print(f"[READ] {s_:.1f}-{e_:.1f}秒 {n}字: 表示 {e_ - s_:.2f}秒 < 必要 {need:.2f}秒 「{re.sub(r'[{}]', '', cap)}」")

        # 音: 声を倍速(音程はそのまま)にして並べ、効果音は各カットの頭に
        mix = np.zeros(int((total + 0.5) * SR), np.float32)
        for at, v, name in audio:
            raw = os.path.join(td, "v.wav"); fast = os.path.join(td, "f.raw")
            se.write_wav(raw, v)
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", raw, "-af", f"atempo={speed}",
                            "-ac", "1", "-ar", str(SR), "-f", "s16le", fast], check=True)
            x = np.fromfile(fast, np.int16).astype(np.float32) / 32768
            i0 = int(at * SR); mix[i0:i0 + len(x)] += x[: len(mix) - i0]
            if name:
                s_ = se.get(name) * 0.35
                mix[i0:i0 + len(s_)] += s_[: len(mix) - i0]
        mix = mix[: int(total * SR)]
        mix /= max(1.0, np.abs(mix).max() / 0.95)
        wav = os.path.join(td, "mix.wav"); se.write_wav(wav, mix)

        lst = os.path.join(td, "list.txt")
        open(lst, "w").write("".join(f"file '{p}'\n" for p in parts))

        ass = os.path.join(td, "t.ass")
        ev = [f"Dialogue: 0,{ass_time(0)},{ass_time(total)},Box,,0,0,0,,{{\\an7\\pos(0,0)\\1c{rs.BLACK}\\p1}}"
              f"{rs.rect(0, 0, W, BAND_TOP)}{{\\p0}}",
              f"Dialogue: 1,{ass_time(0)},{ass_time(total)},Head,,0,0,0,,{{\\an5\\pos(540,{BAND_TOP // 2 + 20})}}"
              f"{plan['header']}"]
        ev += [f"Dialogue: 2,{ass_time(s)},{ass_time(e)},Cap,,0,0,0,,{{\\an5\\pos(540,{CAP_Y})}}{colorize(cap)}"
               for s, e, cap in events if cap]
        with open(ass, "w", encoding="utf-8") as f:
            f.write(f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 2

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Head,{rs.HEAD_FONT},108,{rs.RED},{rs.RED},{rs.WHITE},&H00000000&,0,0,0,0,100,100,-6,0,1,6,0,5,20,20,0,1
Style: Cap,{rs.CAP_FONT},70,{rs.WHITE},{rs.WHITE},{rs.BLACK},&H00000000&,0,0,0,0,100,100,0,0,1,8,0,5,40,40,0,1
Style: Box,Arial,10,{rs.WHITE},{rs.WHITE},{rs.BLACK},&H00000000&,0,0,0,0,100,100,0,0,1,0,0,7,0,0,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
""" + "\n".join(ev) + "\n")

        vf = (f"[0:v]split[a][b];[b]crop={W}:{H - GLASS_TOP}:0:{GLASS_TOP},boxblur=22:3,eq=brightness=-0.3:saturation=0.4[g];"
              f"[a][g]overlay=0:{GLASS_TOP},ass='{ass}':fontsdir='{rs.FONTS}',format=yuv420p[v]")
        os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst, "-i", wav,
                        "-filter_complex", vf, "-map", "[v]", "-map", "1:a", "-c:v", "libx264", "-crf", "19",
                        "-af", "loudnorm=I=-13:TP=-1.0:LRA=11", "-c:a", "aac", "-b:a", "192k", "-shortest",
                        "-movflags", "+faststart", a.out], check=True)
    print(f"{a.out} ({total:.1f}s)")


if __name__ == "__main__":
    main()
