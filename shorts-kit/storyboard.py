#!/usr/bin/env python3
"""台本(JSON)から絵コンテ画像を作る。動画を書き出す前の確認用。

各カットについて、完成時と同じレイアウトの1コマ + 秒数 + 読み上げ文 + 演出メモを並べる。
例: python3 storyboard.py script.json source.mp4 --out out/storyboard.png
"""
import argparse, json, os, subprocess, tempfile, textwrap
from PIL import Image, ImageDraw, ImageFont
from make_short import to_sec
from narr_short import SR, tts, probe, caption, write_ass, layout_filter

FONT_PATH = subprocess.run(["fc-match", "-f", "%{file}", "IPAGothic"], capture_output=True, text=True).stdout
PW, PH = 324, 576   # 1コマの縮小サイズ(9:16)
TEXT_H = 300
COLS = 4


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("script")
    ap.add_argument("source")
    ap.add_argument("--out", required=True)
    ap.add_argument("--speed", type=float, default=1.3)
    a = ap.parse_args()
    sc = json.load(open(a.script, encoding="utf-8"))
    src_w, src_h = probe(a.source)
    font = ImageFont.truetype(FONT_PATH, 19)
    big = ImageFont.truetype(FONT_PATH, 26)

    cuts, t, chars = [], 0.0, 0
    with tempfile.TemporaryDirectory() as td:
        for i, ln in enumerate(sc["lines"]):
            dur = len(tts(ln["say"], a.speed)) / SR
            ass = os.path.join(td, f"c{i}.ass")
            vf, cap_top = layout_filter(ass, src_w, src_h)
            write_ass(ass, sc.get("header", ""), [(0, dur, caption(ln))], dur, cap_top)
            png = os.path.join(td, f"c{i}.png")
            mid = to_sec(ln["src"]) + dur / 2
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", str(mid), "-i", a.source,
                            "-frames:v", "1", "-filter_complex", vf, "-map", "[v]", png], check=True)
            cuts.append((Image.open(png).resize((PW, PH)), t, t + dur, ln))
            chars += len(ln["say"])
            t += dur

        rows = (len(cuts) + COLS - 1) // COLS
        head_h = 70
        sheet = Image.new("RGB", (COLS * (PW + 20) + 20, head_h + rows * (PH + TEXT_H + 20)), "white")
        d = ImageDraw.Draw(sheet)
        d.text((20, 18), f"{os.path.basename(a.script)}   全{t:.1f}秒 / {len(cuts)}カット / 読み上げ {chars / t:.1f}字/秒",
               font=big, fill="black")
        for i, (img, s, e, ln) in enumerate(cuts):
            x = 20 + (i % COLS) * (PW + 20)
            y = head_h + (i // COLS) * (PH + TEXT_H + 20)
            sheet.paste(img, (x, y))
            ty = y + PH + 8
            d.text((x, ty), f"#{i + 1}  {s:.1f}–{e:.1f}秒", font=big, fill="#c00000")
            d.text((x, ty + 32), f"素材 {ln['src']}〜", font=font, fill="#555555")
            ty += 62
            body = "【声】" + ln["say"] + ("\n【演出】" + ln["note"] if ln.get("note") else "")
            for para in body.split("\n"):
                for wl in textwrap.wrap(para, 16):
                    d.text((x, ty), wl, font=font, fill="black")
                    ty += 25
        os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
        sheet.save(a.out)
    print(f"{a.out} ({t:.1f}s, {len(cuts)} cuts)")


if __name__ == "__main__":
    main()
