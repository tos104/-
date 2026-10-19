#!/usr/bin/env python3
"""横長動画の一部を 1080x1920 のショートに変換する。

レイアウト: 上=タイトル帯 / 中央=元映像(横幅いっぱい) / 背景=元映像をぼかして拡大 / 下寄り=字幕
例:
  python3 make_short.py in.mp4 --start 03:12 --end 03:58 \
      --title "240万円のトレード|結果は…？" --srt in.srt --out out/clip01.mp4
タイトルの "|" は改行。--srt は元動画全体の字幕(タイムコードは元動画基準)を渡す。
"""
import argparse, os, re, subprocess, tempfile

FONT = "IPAGothic"


def to_sec(t):
    t = str(t).replace(",", ".")
    sec = 0.0
    for p in t.split(":"):
        sec = sec * 60 + float(p)
    return sec


def ass_time(s):
    s = max(s, 0)
    h, rem = divmod(s, 3600)
    m, sec = divmod(rem, 60)
    return f"{int(h)}:{int(m):02d}:{sec:05.2f}"


def parse_srt(path):
    blocks = re.split(r"\n\s*\n", open(path, encoding="utf-8-sig").read().strip())
    for b in blocks:
        lines = b.strip().splitlines()
        for i, ln in enumerate(lines):
            m = re.match(r"(\S+)\s*-->\s*(\S+)", ln)
            if m:
                yield to_sec(m.group(1)), to_sec(m.group(2)), "\\N".join(lines[i + 1:])
                break


def build_ass(path, dur, title, srt, start, end, fg_top, fg_h):
    head = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Title,{FONT},96,&H0000F0FF,&H000000FF,&H00000000,&H00000000,1,0,0,0,100,100,0,0,1,8,0,8,40,40,170,1
Style: Cap,{FONT},80,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,1,0,0,0,100,100,0,0,1,7,0,8,50,50,{fg_top + fg_h + 60},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    ev = []
    if title:
        ev.append(f"Dialogue: 0,{ass_time(0)},{ass_time(dur)},Title,,0,0,0,,{title.replace('|', chr(92) + 'N')}")
    if srt:
        for s, e, text in parse_srt(srt):
            if e <= start or s >= end:
                continue
            ev.append(f"Dialogue: 0,{ass_time(s - start)},{ass_time(min(e, end) - start)},Cap,,0,0,0,,{text}")
    with open(path, "w", encoding="utf-8") as f:
        f.write(head + "\n".join(ev) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input")
    ap.add_argument("--start", required=True)
    ap.add_argument("--end", required=True)
    ap.add_argument("--title", default="")
    ap.add_argument("--srt")
    ap.add_argument("--zoom", type=float, default=1.0, help="中央映像の拡大率(1.0=横幅ぴったり、左右を切って大きく見せるなら1.3など)")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    start, end = to_sec(a.start), to_sec(a.end)
    dur = end - start
    fg_w = int(1080 * a.zoom) // 2 * 2
    fg_h = int(fg_w * 9 / 16) // 2 * 2
    fg_top = (1920 - fg_h) // 2 - 80

    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with tempfile.TemporaryDirectory() as td:
        ass = os.path.join(td, "sub.ass")
        build_ass(ass, dur, a.title, a.srt, start, end, fg_top, fg_h)
        vf = (
            f"[0:v]split[a][b];"
            f"[a]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=30:2,eq=brightness=-0.15[bg];"
            f"[b]scale={fg_w}:-2,crop=min(iw\\,1080):ih[fg];"
            f"[bg][fg]overlay=(W-w)/2:{fg_top},ass='{ass}',format=yuv420p[v]"
        )
        cmd = ["ffmpeg", "-y", "-loglevel", "error", "-ss", str(start), "-t", str(dur), "-i", a.input,
               "-filter_complex", vf, "-map", "[v]", "-map", "0:a?",
               "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-r", "30",
               "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", a.out]
        subprocess.run(cmd, check=True)
    print(a.out)


if __name__ == "__main__":
    main()
