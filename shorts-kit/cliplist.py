#!/usr/bin/env python3
"""切り抜き候補のリスト(JSON)を、1枚の縦長画像にする。

  python3 cliplist.py cliplists/<id>.json --thumbs <サムネ画像のフォルダ> --out out.png
JSON: title, source, note, clips[{rank, thumb, range, len, hook("|"で改行・{}で強調), facts[], why}]
"""
import argparse, json, os, re
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
HEAD = os.path.join(HERE, "fonts", "DelaGothicOne-Regular.ttf")
BODY = os.path.join(HERE, "fonts", "MPLUSRounded1c-Black.ttf")
W, PAD, ROW_H, TH_W = 1600, 48, 400, 448
BG, CARD, INK, SUB, LINE = "#F8F5EE", "#FFFFFF", "#2F3437", "#6B716E", "#E2DDD3"
ACCENT, YELLOW = "#E0402F", "#F2B705"
RANK = {"S": "#E0402F", "A": "#E07B2F", "B": "#3E7A63", "C": "#8A8F8C"}


def font(path, size):
    return ImageFont.truetype(path, size)


def draw_rich(d, xy, text, f, base, accent):
    """{...} を強調色で描く。1行分。"""
    x, y = xy
    for part in re.split(r"(\{.+?\})", text):
        if not part:
            continue
        color = accent if part.startswith("{") else base
        part = part.strip("{}")
        d.text((x, y), part, font=f, fill=color)
        x += d.textlength(part, font=f)


def wrap(d, text, f, width):
    """幅に収まるように1文字ずつ折り返す(日本語用)。"""
    out, cur = [], ""
    for ch in text:
        if d.textlength(cur + ch, font=f) > width:
            out.append(cur); cur = ch
        else:
            cur += ch
    return out + ([cur] if cur else [])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("plan")
    ap.add_argument("--thumbs", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    p = json.load(open(a.plan, encoding="utf-8"))
    clips = p["clips"]
    top = 290
    H = top + len(clips) * (ROW_H + 24) + 90
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    for k, l in enumerate(wrap(d, p["title"], font(HEAD, 46), W - 2 * PAD)[:2]):
        d.text((PAD, 30 + k * 58), l, font=font(HEAD, 46), fill=INK)
    d.text((PAD, 160), "元動画 " + p["source"], font=font(BODY, 28), fill=SUB)
    d.text((PAD, 204), p["note"], font=font(BODY, 26), fill=SUB)
    d.line((PAD, 256, W - PAD, 256), fill=LINE, width=3)

    f_hook, f_meta, f_fact, f_why = font(HEAD, 44), font(BODY, 28), font(BODY, 27), font(BODY, 26)
    for i, c in enumerate(clips):
        y = top + i * (ROW_H + 24)
        d.rounded_rectangle((PAD, y, W - PAD, y + ROW_H), radius=18, fill=CARD, outline=LINE, width=2)
        # 順位バッジ
        r = RANK.get(c["rank"], SUB)
        d.ellipse((PAD + 24, y + 24, PAD + 104, y + 104), fill=r)
        d.text((PAD + 64, y + 64), c["rank"], font=font(HEAD, 46), fill="white", anchor="mm")
        d.text((PAD + 64, y + 134), f"#{i + 1}", font=f_meta, fill=SUB, anchor="mm")
        # サムネイル
        th = Image.open(os.path.join(a.thumbs, c["thumb"])).convert("RGB").resize((TH_W, 252))
        tx = PAD + 130
        img.paste(th, (tx, y + 24))
        d.rounded_rectangle((tx, y + 24 + 252 - 44, tx + TH_W, y + 24 + 252), radius=0, fill="#000000")
        d.text((tx + 14, y + 24 + 252 - 38), c["range"], font=font(BODY, 24), fill="white")
        d.text((tx + 14, y + 24 + 262), "長さ " + c["len"], font=f_meta, fill=SUB)
        # 文字
        x0 = tx + TH_W + 36
        lines = c["hook"].split("|")
        for k, l in enumerate(lines):
            draw_rich(d, (x0, y + 24 + k * 56), l, f_hook, INK, ACCENT)
        fy = y + 36 + len(lines) * 56
        for fct in c["facts"]:
            d.text((x0, fy), "・" + fct, font=f_fact, fill=INK)
            fy += 36
        wl = wrap(d, "狙い  " + c["why"], f_why, W - PAD - 40 - x0)
        by = y + ROW_H - 22 - 34 * len(wl)
        d.rounded_rectangle((x0 - 8, by - 8, W - PAD - 24, y + ROW_H - 14), radius=10, fill="#FFF4D6")
        for k, l in enumerate(wl):
            d.text((x0 + 6, by + k * 34), l, font=f_why, fill="#6A4B00")
    d.text((PAD, H - 64), "S＝最優先  A＝おすすめ  B＝余裕があれば  C＝ネタ枠", font=font(BODY, 26), fill=SUB)
    img.save(a.out)
    print(a.out, img.size)


if __name__ == "__main__":
    main()
