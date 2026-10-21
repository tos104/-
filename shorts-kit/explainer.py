#!/usr/bin/env python3
"""本人の声 + 数字のグラフだけで見せる解説ショート。数字は元動画で本人が言ったものだけを使う。

設計図(JSON):
{
  "header": "青眼の旧レリーフ|今いくら？",
  "audio": ["01:41.6", "01:59.8"], "speed": 1.25,
  "bg": "05:55.0",                          # 背景にぼかして敷く元動画の位置
  "bars": [["ARS10", 140, "140万円", "01:45.0"], ...],   # ラベル, 値, 表示, 声で言った時刻(元動画)
  "caps": [["01:41.6", "01:47.0", "字幕"], ...],
  "finale": ["01:56.4", "1年前は|{100万円}を切っていた"]
}
  python3 explainer.py plan.json source.mp4 --out out.mp4
"""
import argparse, json, os, subprocess, tempfile
import rich_short as rs
from make_short import to_sec, ass_time
from plan_short import colorize

W, H = 1080, 1920
BAR_X, BAR_W, BAR_TOP, BAR_GAP = 90, 900, 640, 230


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("plan")
    ap.add_argument("source")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    p = json.load(open(a.plan, encoding="utf-8"))
    sp = p.get("speed", 1.0)
    a0, a1 = map(to_sec, p["audio"])
    total = (a1 - a0) / sp
    T = lambda s: max(0.0, (to_sec(s) - a0) / sp)  # 元動画の時刻 → 完成動画の時刻

    ev = [f"Dialogue: 0,{ass_time(0)},{ass_time(total)},Box,,0,0,0,,{{\\an7\\pos(0,0)\\1c{rs.BLACK}\\p1}}"
          f"{rs.rect(0, 0, W, 360)}{{\\p0}}",
          f"Dialogue: 1,{ass_time(0)},{ass_time(total)},Head,,0,0,0,,{{\\an5\\pos(540,190)}}{colorize(p['header'])}"]
    vmax = max(b[1] for b in p["bars"])
    for k, (label, value, shown, at) in enumerate(p["bars"]):
        s, y = T(at), BAR_TOP + k * BAR_GAP
        w = int(BAR_W * value / vmax)
        color = rs.YELLOW if value == vmax else rs.WHITE
        ev.append(f"Dialogue: 2,{ass_time(s)},{ass_time(total)},Label,,0,0,0,,{{\\an1\\pos({BAR_X},{y})\\fad(120,0)}}{label}")
        ev.append(f"Dialogue: 2,{ass_time(s)},{ass_time(total)},Box,,0,0,0,,{{\\an7\\pos(0,0)\\1c{color}"
                  f"\\clip({BAR_X},{y + 20},{BAR_X},{y + 110})\\t(0,600,0.5,\\clip({BAR_X},{y + 20},{BAR_X + w},{y + 110}))\\p1}}"
                  f"{rs.rect(BAR_X, y + 20, BAR_X + w, y + 110)}{{\\p0}}")
        steps = 12  # 数字のカウントアップ(0.6 秒)
        for j in range(steps + 1):
            t0 = s + 0.6 * j / steps
            t1 = total if j == steps else s + 0.6 * (j + 1) / steps
            txt = shown if j == steps else f"{round(value * j / steps)}万円"
            ev.append(f"Dialogue: 3,{ass_time(t0)},{ass_time(t1)},Num,,0,0,0,,{{\\an6\\pos({BAR_X + max(w, 330) - 16},{y + 65})}}{txt}")
    for s, e, text in p.get("caps", []):
        ev.append(f"Dialogue: 4,{ass_time(T(s))},{ass_time(T(e))},Cap,,0,0,0,,{{\\an5\\pos(540,1470)\\fad(80,0)}}{colorize(text)}")
    if p.get("finale"):
        s = T(p["finale"][0])
        ev.append(f"Dialogue: 5,{ass_time(s)},{ass_time(total)},Box,,0,0,0,,{{\\an7\\pos(0,0)\\1c{rs.BLACK}\\1a&H00&\\fad(150,0)\\p1}}"
                  f"{rs.rect(0, 360, W, H)}{{\\p0}}")
        ev.append(f"Dialogue: 6,{ass_time(s + 0.1)},{ass_time(total)},Fin,,0,0,0,,{{\\an5\\pos(540,1000)\\fad(150,0)}}{colorize(p['finale'][1])}")

    with tempfile.TemporaryDirectory() as td:
        ass = os.path.join(td, "e.ass")
        with open(ass, "w", encoding="utf-8") as f:
            f.write(f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 2

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Head,{rs.HEAD_FONT},104,{rs.WHITE},{rs.WHITE},{rs.BLACK},&H00000000&,0,0,0,0,100,100,-6,0,1,6,0,5,20,20,0,1
Style: Label,{rs.CAP_FONT},64,{rs.WHITE},{rs.WHITE},{rs.BLACK},&H00000000&,0,0,0,0,100,100,0,0,1,6,0,1,0,0,0,1
Style: Num,{rs.HEAD_FONT},62,{rs.BLACK},{rs.BLACK},{rs.WHITE},&H00000000&,0,0,0,0,100,100,-2,0,1,0,0,6,0,0,0,1
Style: Cap,{rs.CAP_FONT},70,{rs.WHITE},{rs.WHITE},{rs.BLACK},&H00000000&,0,0,0,0,100,100,0,0,1,8,0,5,40,40,0,1
Style: Fin,{rs.HEAD_FONT},120,{rs.WHITE},{rs.WHITE},{rs.BLACK},&H00000000&,0,0,0,0,100,100,-6,0,1,10,0,5,40,40,0,1
Style: Box,Arial,10,{rs.WHITE},{rs.WHITE},{rs.BLACK},&H00000000&,0,0,0,0,100,100,0,0,1,0,0,7,0,0,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
""" + "\n".join(ev) + "\n")
        bg0 = to_sec(p["bg"])
        vf = (f"[0:v]setpts=PTS/{sp},crop=202:360:173:0,scale={W}:{H},boxblur=40:3,eq=brightness=-0.35:saturation=0.8,"
              f"fps=30,ass='{ass}':fontsdir='{rs.FONTS}',format=yuv420p[v]")
        os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error",
                        "-ss", f"{bg0:.3f}", "-t", f"{(a1 - a0) + 0.5:.3f}", "-i", a.source,
                        "-ss", f"{a0:.3f}", "-t", f"{a1 - a0:.3f}", "-i", a.source,
                        "-filter_complex", vf + f";[1:a]highpass=f=90,afftdn=nf=-25,atempo={sp},loudnorm=I=-13:TP=-1.0[a]",
                        "-map", "[v]", "-map", "[a]", "-t", f"{total:.3f}",
                        "-c:v", "libx264", "-crf", "19", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", a.out],
                       check=True)
    print(f"{a.out} ({total:.1f}s)")


if __name__ == "__main__":
    main()
