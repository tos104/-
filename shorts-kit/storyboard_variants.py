#!/usr/bin/env python3
"""同じ素材で、構成とデザインがまったく違う絵コンテを複数案つくる(静止画の見本)。

  python3 storyboard_variants.py plan.json source.mp4 --out-dir output/
plan.json: {"title", "variants": [{"key","name","structure","design","beats":[{"t","cx","zoom","texts":{...},"say"}]}]}
デザインは key ごとに描き分ける(A 全画面 / B 上下分割 / C クイズ / D レシート / E 吹き出し)。
数字・発言は設計図に書いたもの(元動画の声と字幕)だけを描く。
"""
import argparse, json, os, subprocess, tempfile
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
F = {k: os.path.join(HERE, "fonts", v) for k, v in {
    "dela": "DelaGothicOne-Regular.ttf", "black": "MPLUSRounded1c-Black.ttf",
    "xb": "MPLUSRounded1c-ExtraBold.ttf", "bold": "MPLUSRounded1c-Bold.ttf"}.items()}
W, H = 1080, 1920
_cache = {}


def font(k, s):
    return ImageFont.truetype(F[k], s)


def frame(src, t):
    if t not in _cache:
        with tempfile.NamedTemporaryFile(suffix=".png") as f:
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{t:.2f}", "-i", src, "-frames:v", "1", f.name], check=True)
            im = Image.open(f.name).convert("RGB"); im.load()
        _cache[t] = im
    return _cache[t]


def crop(src, t, w, h, cx=320, cy=180, zoom=1.0):
    """元動画(640x360)から w:h の比で切り抜いて拡大。"""
    im = frame(src, t)
    sw, sh = im.size
    ch = sh / zoom
    cw = ch * w / h
    if cw > sw:
        cw = sw; ch = cw * h / w
    x = min(max(cx - cw / 2, 0), sw - cw); y = min(max(cy - ch / 2, 0), sh - ch)
    return im.crop((int(x), int(y), int(x + cw), int(y + ch))).resize((w, h), Image.LANCZOS)


def ctext(d, xy, text, f, fill, stroke=0, sfill=(0, 0, 0), anchor="mm"):
    d.text(xy, text, font=f, fill=fill, anchor=anchor, stroke_width=stroke, stroke_fill=sfill)


# ---- A: 全画面ドキュメント(縦いっぱいの映像+下に大きな字幕+左上に小さな章) ----
def draw_A(src, b):
    tx = b["texts"]
    img = crop(src, b["t"], W, H, b.get("cx", 320), b.get("cy", 180), b.get("zoom", 1.0))
    sh = Image.new("RGBA", (W, H), (0, 0, 0, 0)); sd = ImageDraw.Draw(sh)
    for i in range(700):
        sd.line((0, H - i, W, H - i), fill=(0, 0, 0, int(200 * (1 - i / 700))))
    img = Image.alpha_composite(img.convert("RGBA"), sh).convert("RGB")
    d = ImageDraw.Draw(img)
    if tx.get("chapter"):
        d.rounded_rectangle((60, 120, 60 + d.textlength(tx["chapter"], font=font("bold", 40)) + 50, 190), radius=35, fill=(255, 255, 255))
        d.text((85, 155), tx["chapter"], font=font("bold", 40), fill=(20, 20, 20), anchor="lm")
    y = H - 430
    for k, line in enumerate(tx.get("cap", [])):
        ctext(d, (W / 2, y + k * 120), line, font("black", 92 if k else 78), (255, 230, 0) if k else (255, 255, 255), 6)
    return img


# ---- B: 上下分割 Before / After(上=買った時、下=今。結果から巻き戻す) ----
def draw_B(src, b):
    tx = b["texts"]
    img = Image.new("RGB", (W, H), (16, 16, 18)); d = ImageDraw.Draw(img)
    top = crop(src, b["t"], W, 860, b.get("cx", 320), 180, b.get("zoom", 1.0))
    bt = b.get("t2", b["t"])
    bot = crop(src, bt, W, 860, b.get("cx2", b.get("cx", 320)), 180, b.get("zoom2", b.get("zoom", 1.0)))
    if tx.get("dim_top"):
        top = Image.blend(top, Image.new("RGB", top.size, (0, 0, 0)), 0.55)
    if tx.get("dim_bot"):
        bot = Image.blend(bot, Image.new("RGB", bot.size, (0, 0, 0)), 0.55)
    img.paste(top, (0, 90)); img.paste(bot, (0, 970))
    d.rectangle((0, 950, W, 970), fill=(255, 255, 255))
    for (y, lab, col) in [(90, tx.get("tag_top", "BEFORE"), (90, 90, 96)), (970, tx.get("tag_bot", "AFTER"), (220, 40, 50))]:
        d.rectangle((0, y, 300, y + 80), fill=col)
        d.text((150, y + 40), lab, font=font("dela", 46), fill=(255, 255, 255), anchor="mm")
    if tx.get("top"):
        ctext(d, (W / 2, 90 + 760), tx["top"], font("black", 76), (255, 255, 255), 6)
    if tx.get("bot"):
        ctext(d, (W / 2, 970 + 760), tx["bot"], font("black", 84), (255, 235, 60), 6)
    if tx.get("center"):
        f = font("dela", 120); tw = d.textlength(tx["center"], font=f)
        d.rounded_rectangle((W / 2 - tw / 2 - 40, 880, W / 2 + tw / 2 + 40, 1040), radius=20, fill=(220, 40, 50))
        ctext(d, (W / 2, 960), tx["center"], f, (255, 255, 255))
    return img


# ---- C: クイズ(問題文+映像の窓+選択肢2つ+残り時間の棒) ----
def draw_C(src, b):
    tx = b["texts"]
    img = Image.new("RGB", (W, H), (24, 28, 70)); d = ImageDraw.Draw(img)
    for i in range(0, H, 6):
        d.line((0, i, W, i), fill=(28, 33, 82))
    d.rounded_rectangle((60, 120, W - 60, 380), radius=30, fill=(255, 255, 255))
    ctext(d, (W / 2, 190), tx.get("q1", ""), font("xb", 56), (40, 40, 60))
    ctext(d, (W / 2, 300), tx.get("q2", ""), font("dela", 84), (230, 50, 60))
    win = crop(src, b["t"], W - 160, 620, b.get("cx", 320), 180, b.get("zoom", 1.0))
    img.paste(win, (80, 430)); d.rectangle((80, 430, W - 80, 1050), outline=(255, 215, 0), width=8)
    for k, (lab, val) in enumerate(tx.get("choices", [])):
        x0 = 80 + k * 470; y0 = 1120
        hi = tx.get("answer") == k; lo = tx.get("answer") is not None and not hi
        col = (255, 215, 0) if hi else ((90, 90, 110) if lo else (255, 255, 255))
        d.rounded_rectangle((x0, y0, x0 + 440, y0 + 230), radius=28, fill=col)
        d.ellipse((x0 + 25, y0 + 65, x0 + 125, y0 + 165), fill=(230, 50, 60))
        ctext(d, (x0 + 75, y0 + 115), lab, font("dela", 60), (255, 255, 255))
        ctext(d, (x0 + 285, y0 + 115), val, font("dela", 96), (30, 30, 50))
    if tx.get("bar") is not None:
        d.rounded_rectangle((80, 1420, W - 80, 1460), radius=20, fill=(60, 66, 120))
        d.rounded_rectangle((80, 1420, 80 + (W - 160) * tx["bar"], 1460), radius=20, fill=(255, 215, 0))
    for k, line in enumerate(tx.get("hint", [])):
        ctext(d, (W / 2, 1540 + k * 90), line, font("xb", 58 if k else 50), (255, 255, 255) if k else (180, 190, 255))
    return img


# ---- D: レシート(ぼかした映像の上に紙。行が上から増える) ----
def draw_D(src, b):
    tx = b["texts"]
    bg = crop(src, b["t"], W, H, b.get("cx", 320), 180, b.get("zoom", 1.0)).filter(ImageFilter.GaussianBlur(14))
    bg = Image.blend(bg, Image.new("RGB", bg.size, (20, 20, 20)), 0.35)
    img = bg.copy(); d = ImageDraw.Draw(img)
    win = crop(src, b["t"], 760, 560, b.get("cx", 320), 180, b.get("zoom", 1.0))
    img.paste(win, (160, 110))
    px0, px1, py0 = 140, W - 140, 720
    rows = tx.get("rows", [])
    py1 = py0 + 240 + 96 * len(rows) + (170 if tx.get("total") else 0)
    d.rectangle((px0, py0, px1, py1), fill=(252, 251, 246))
    for x in range(px0, px1, 30):  # ギザギザの下端
        d.polygon([(x, py1), (x + 15, py1 + 22), (x + 30, py1)], fill=(252, 251, 246))
    ctext(d, (W / 2, py0 + 70), tx.get("head", "RECEIPT"), font("dela", 54), (30, 30, 30))
    ctext(d, (W / 2, py0 + 130), tx.get("sub", ""), font("bold", 32), (120, 120, 120))
    d.line((px0 + 40, py0 + 175, px1 - 40, py0 + 175), fill=(150, 150, 150), width=3)
    for k, (a, v) in enumerate(rows):
        y = py0 + 230 + 96 * k
        d.text((px0 + 50, y), a, font=font("xb", 46), fill=(40, 40, 40), anchor="lm")
        d.text((px1 - 50, y), v, font=font("dela", 52), fill=(200, 40, 50) if v.startswith("ARS") else (40, 40, 40), anchor="rm")
    if tx.get("total"):
        y = py1 - 110
        d.line((px0 + 40, y - 60, px1 - 40, y - 60), fill=(40, 40, 40), width=4)
        d.text((px0 + 50, y), tx["total"][0], font=font("dela", 56), fill=(40, 40, 40), anchor="lm")
        d.text((px1 - 50, y), tx["total"][1], font=font("dela", 70), fill=(200, 40, 50), anchor="rm")
    if tx.get("cap"):
        ctext(d, (W / 2, 1800), tx["cap"], font("black", 64), (255, 255, 255), 6)
    return img


# ---- E: 心の声(上に丸いワイプ、下にチャットの吹き出しが積み上がる) ----
def draw_E(src, b):
    tx = b["texts"]
    img = Image.new("RGB", (W, H), (236, 229, 221)); d = ImageDraw.Draw(img)
    d.rectangle((0, 0, W, 150), fill=(70, 120, 90))
    ctext(d, (W / 2, 85), tx.get("title", ""), font("xb", 48), (255, 255, 255))
    r = 380
    circ = crop(src, b["t"], 2 * r, 2 * r, b.get("cx", 320), 180, b.get("zoom", 1.0))
    m = Image.new("L", (2 * r, 2 * r), 0); ImageDraw.Draw(m).ellipse((0, 0, 2 * r, 2 * r), fill=255)
    img.paste(circ, (W // 2 - r, 200), m)
    d.ellipse((W // 2 - r, 200, W // 2 + r, 200 + 2 * r), outline=(255, 255, 255), width=10)
    y = 1060
    for side, msg in tx.get("bubbles", []):
        f = font("dela", 64) if side == "sys" else font("xb", 58)
        lines = msg.split("|")
        bw = max(d.textlength(l, font=f) for l in lines) + 80; bh = 78 * len(lines) + 50
        if side == "me":
            x0 = W - 60 - bw; col = (140, 220, 120)
        elif side == "sys":
            x0 = (W - bw) / 2; col = (220, 40, 50)
        else:
            x0 = 60; col = (255, 255, 255)
        d.rounded_rectangle((x0, y, x0 + bw, y + bh), radius=36, fill=col)
        for k, l in enumerate(lines):
            d.text((x0 + 40, y + 25 + 78 * k), l, font=f, fill=(255, 255, 255) if side == "sys" else (30, 30, 30))
        y += bh + 30
    return img


DRAW = {"A": draw_A, "B": draw_B, "C": draw_C, "D": draw_D, "E": draw_E}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("plan"); ap.add_argument("source"); ap.add_argument("--out-dir", required=True)
    a = ap.parse_args()
    p = json.load(open(a.plan, encoding="utf-8"))
    os.makedirs(a.out_dir, exist_ok=True)
    tiles = []
    for v in p["variants"]:
        frames = [DRAW[v["key"]](a.source, b).resize((W // 3, H // 3), Image.LANCZOS) for b in v["beats"]]
        tw, th = frames[0].size
        n = len(frames)
        sheet = Image.new("RGB", (16 + n * (tw + 16), th + 330), "white")
        d = ImageDraw.Draw(sheet)
        d.text((20, 18), f"案{v['key']}  {v['name']}", font=font("dela", 44), fill=(30, 30, 30))
        d.text((20, 80), "構成: " + v["structure"], font=font("bold", 26), fill=(60, 60, 60))
        d.text((20, 118), "デザイン: " + v["design"], font=font("bold", 26), fill=(60, 60, 60))
        for k, (fr, b) in enumerate(zip(frames, v["beats"])):
            x = 16 + k * (tw + 16)
            sheet.paste(fr, (x, 170))
            line, yy = "", 170 + th + 10
            for ch in f"{k + 1}. 声: " + b.get("say", ""):
                if d.textlength(line + ch, font=font("bold", 21)) > tw:
                    d.text((x, yy), line, font=font("bold", 21), fill=(70, 70, 70)); yy += 27; line = ch
                else:
                    line += ch
            d.text((x, yy), line, font=font("bold", 21), fill=(70, 70, 70))
        out = os.path.join(a.out_dir, f"variant_{p['name']}_{v['key']}.png")
        sheet.save(out); tiles.append(out); print(out, sheet.size)


if __name__ == "__main__":
    main()
