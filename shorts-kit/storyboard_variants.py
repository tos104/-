#!/usr/bin/env python3
"""同じ素材で、構成とデザインがまったく違う絵コンテ・動画を複数案つくる。

  python3 storyboard_variants.py plan.json source.mp4 --out-dir output/            # 絵コンテ(静止画の見本)
  python3 storyboard_variants.py plan.json source.mp4 --out-dir output/ --video A B # 動画も書き出す
plan.json: {"name", "variants": [{"key","name","structure","design",
            "beats":[{"t","cx","cy","zoom","cuts":[{"a":[開始,終了],"jet","se"}],"texts":{...},"say"}]}]}
各案は「上に重ねる絵(RGBA)」と「元動画を流す枠(slot)」に分けて描く。静止画は枠に1コマを貼り、動画は枠に元動画を流す。
デザインは key ごと(A 全画面 / B 上下分割 / C クイズ / D レシート / E 吹き出し)。数字・発言は設計図に書いたものだけ。
"""
import argparse, json, math, os, subprocess, tempfile
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
import se
import rich_short as rs
import panel_short as ps
from make_short import to_sec

HERE = os.path.dirname(os.path.abspath(__file__))
F = {k: os.path.join(HERE, "fonts", v) for k, v in {
    "dela": "DelaGothicOne-Regular.ttf", "black": "MPLUSRounded1c-Black.ttf",
    "xb": "MPLUSRounded1c-ExtraBold.ttf", "bold": "MPLUSRounded1c-Bold.ttf",
    "min": "ShipporiMincho-ExtraBold.ttf", "minm": "ShipporiMincho-Medium.ttf"}.items()}
W, H = 1080, 1920
SR = rs.SR
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


def crop_box(sw, sh, w, h, cx=320, cy=180, zoom=1.0):
    """元動画(sw x sh)から w:h の比で切り抜く範囲(x, y, cw, ch)。"""
    ch = sh / zoom
    cw = ch * w / h
    if cw > sw:
        cw = sw; ch = cw * h / w
    x = min(max(cx - cw / 2, 0), sw - cw); y = min(max(cy - ch / 2, 0), sh - ch)
    return int(x), int(y), int(cw) // 2 * 2, int(ch) // 2 * 2


def slot(t, x, y, w, h, b, **kw):
    """元動画を流す枠。kw: cx, cy, zoom, blur, dim(0〜1)。"""
    s = {"t": t, "x": x, "y": y, "w": w, "h": h, "cx": b.get("cx", 320), "cy": b.get("cy", 180), "zoom": b.get("zoom", 1.0)}
    s.update(kw)
    return s


def ctext(d, xy, text, f, fill, stroke=0, sfill=(0, 0, 0), anchor="mm"):
    d.text(xy, text, font=f, fill=fill, anchor=anchor, stroke_width=stroke, stroke_fill=sfill)


def hole(img, box, shape="rect"):
    """不透明な絵に、元動画が見える穴をあける。"""
    m = Image.new("L", img.size, 255)
    md = ImageDraw.Draw(m)
    (md.ellipse if shape == "circle" else md.rectangle)(box, fill=0)
    img.putalpha(Image.fromarray(np.minimum(np.array(img.getchannel("A")), np.array(m))))


# ---- A: 全画面ドキュメント(縦いっぱいの映像+下に大きな字幕+左上に小さな章) ----
def layer_A(b):
    tx = b["texts"]
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    for i in range(700):
        d.line((0, H - i, W, H - i), fill=(0, 0, 0, int(200 * (1 - i / 700))))
    if tx.get("chapter"):
        d.rounded_rectangle((60, 120, 60 + d.textlength(tx["chapter"], font=font("bold", 40)) + 50, 190), radius=35, fill=(255, 255, 255))
        d.text((85, 155), tx["chapter"], font=font("bold", 40), fill=(20, 20, 20), anchor="lm")
    for k, line in enumerate(tx.get("cap", [])):
        ctext(d, (W / 2, H - 430 + k * 120), line, font("black", 92 if k else 78), (255, 230, 0) if k else (255, 255, 255), 6)
    return img, [slot(b["t"], 0, 0, W, H, b)]


# ---- B: 上下分割(上=過去、下=今。結果から巻き戻す) ----
def layer_B(b):
    tx = b["texts"]
    img = Image.new("RGBA", (W, H), (16, 16, 18, 255))
    hole(img, (0, 90, W - 1, 949)); hole(img, (0, 970, W - 1, 1829))
    d = ImageDraw.Draw(img)
    for (y0, flag) in [(90, tx.get("dim_top")), (970, tx.get("dim_bot"))]:
        if flag:
            d.rectangle((0, y0, W, y0 + 860), fill=(0, 0, 0, 140))
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
    bot = {"cx": b.get("cx2", b.get("cx", 320)), "cy": b.get("cy2", 180), "zoom": b.get("zoom2", b.get("zoom", 1.0))}
    return img, [slot(b["t"], 0, 90, W, 860, b), slot(b.get("t2", b["t"]), 0, 970, W, 860, bot)]


# ---- C: クイズ(問題文+映像の窓+選択肢2つ+残り時間の棒) ----
def layer_C(b):
    tx = b["texts"]
    img = Image.new("RGBA", (W, H), (24, 28, 70, 255)); d = ImageDraw.Draw(img)
    for i in range(0, H, 6):
        d.line((0, i, W, i), fill=(28, 33, 82))
    hole(img, (80, 430, W - 81, 1049)); d = ImageDraw.Draw(img)
    d.rounded_rectangle((60, 120, W - 60, 380), radius=30, fill=(255, 255, 255))
    ctext(d, (W / 2, 190), tx.get("q1", ""), font("xb", 56), (40, 40, 60))
    ctext(d, (W / 2, 300), tx.get("q2", ""), font("dela", 84), (230, 50, 60))
    d.rectangle((80, 430, W - 80, 1050), outline=(255, 215, 0), width=8)
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
    return img, [slot(b["t"], 80, 430, W - 160, 620, b)]


# ---- D: レシート(ぼかした映像の上に紙。行が上から増える) ----
def layer_D(b):
    tx = b["texts"]
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
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
    win = {"cx": b.get("cx", 320), "cy": b.get("wcy", b.get("cy", 180)), "zoom": b.get("wzoom", b.get("zoom", 1.0))}
    return img, [slot(b["t"], 0, 0, W, H, b, blur=True, dim=0.35), slot(b["t"], 160, 110, 760, 560, win)]


# ---- E: 心の声(上に丸いワイプ、下にチャットの吹き出しが積み上がる) ----
def layer_E(b):
    tx = b["texts"]
    r = 380
    img = Image.new("RGBA", (W, H), (236, 229, 221, 255))
    hole(img, (W // 2 - r, 200, W // 2 + r, 200 + 2 * r), "circle")
    d = ImageDraw.Draw(img)
    d.rectangle((0, 0, W, 150), fill=(70, 120, 90))
    ctext(d, (W / 2, 85), tx.get("title", ""), font("xb", 48), (255, 255, 255))
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
    return img, [slot(b["t"], W // 2 - r, 200, 2 * r, 2 * r, b)]


# ---- D2: レシート改(元動画は横幅いっぱい・拡大なし。上に続きが気になるコピー、下にレシート) ----
VID_Y2 = 330
REC_S = 0.65  # レシートの大きさ(下の案内を YouTube の表示より上に置くため小さくする)
SLIDE_T = 0.3  # 切り替えで元動画が流れる秒数
UI_SAFE = 1536  # これより下は YouTube のタイトル・ボタンが重なる目安(画面の下から約20%)


def layer_D2(b, t=None):
    tx = b["texts"]
    pa = tx.get("pop_at")  # 答えが出る時刻(区切りの頭からの秒)。それまでは before の中身(「？」)を出し、ネタバレしない
    big = 1.0
    if pa is not None and t is not None:
        if t < pa:
            tx = {**tx, **tx.get("before", {})}
        else:
            k = min(1.0, (t - pa) / 0.35)
            big = 1 + 0.8 * (1 - k) ** 3 + 0.2 * math.sin(math.pi * k) * (1 - k)  # 大きく出て弾んで戻る
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    l1, l2 = tx.get("copy", ["", ""])
    if l1:
        ctext(d, (W / 2, 135), l1, font("xb", 62), (255, 255, 255), 6)
    f = font("dela", 96)
    while d.textlength(l2, font=f) > W - 80:
        f = font("dela", f.size - 4)
    y2 = 240 if l1 else 195  # 1行だけのときは上の枠の中央に
    f2 = font("dela", int(f.size * big))
    if tx.get("plate"):  # 座布団: 色の帯の上に白文字+黒フチ(スマホで潰れにくい)
        tw = d.textlength(l2, font=f2)
        d.rounded_rectangle((W / 2 - tw / 2 - 28, y2 - f2.size * 0.62, W / 2 + tw / 2 + 28, y2 + f2.size * 0.62), radius=18, fill=tuple(tx["plate"]))
        ctext(d, (W / 2, y2), l2, f2, (255, 255, 255), 8)
    else:
        ctext(d, (W / 2, y2), l2, f2, (255, 220, 60), 8)
    vh = W * 9 // 16
    d.rectangle((0, VID_Y2 - 6, W, VID_Y2), fill=(255, 255, 255)); d.rectangle((0, VID_Y2 + vh, W, VID_Y2 + vh + 6), fill=(255, 255, 255))
    s = REC_S
    half = (W - 240) * (0.5 + s) / 2 / 1.0 * 0.82
    px0, px1, py0 = W / 2 - half, W / 2 + half, VID_Y2 + vh + 24
    rows = tx.get("rows", [])
    nrow = max(len(rows), tx.get("min_rows", 0))  # 区切りごとにレシートの大きさが変わらないよう行数をそろえる
    py1 = py0 + 200 * s + 84 * s * nrow + (150 * s if tx.get("total") else 0)
    d.rectangle((px0, py0, px1, py1), fill=(252, 251, 246))
    nz = max(1, int((px1 - px0) // 24)); zw = (px1 - px0) / nz  # ギザギザは端でちょうど終わるように割る
    for k in range(nz):
        x = px0 + k * zw
        d.polygon([(x, py1), (x + zw / 2, py1 + 18), (x + zw, py1)], fill=(252, 251, 246))
    ctext(d, (W / 2, py0 + 60 * s), tx.get("head", ""), font("dela", int(50 * s)), (30, 30, 30))
    ctext(d, (W / 2, py0 + 112 * s), tx.get("sub", ""), font("bold", int(30 * s)), (120, 120, 120))
    d.line((px0 + 30, py0 + 150 * s, px1 - 30, py0 + 150 * s), fill=(150, 150, 150), width=3)
    for k, row in enumerate(rows):
        a, v = row[0], row[1]
        hl = len(row) > 2 and row[2] == "big"  # 夢の金額は赤く特大、元手は小さく落ち着いた色(金額の差を見せる)
        lo = len(row) > 2 and row[2] == "small"
        y = py0 + 195 * s + 84 * s * k
        d.text((px0 + 40, y), a, font=font("xb", int(44 * s)), fill=(40, 40, 40), anchor="lm")
        unk = v.startswith("？")  # まだ分からない欄は赤く大きく
        size = 70 if unk or hl else (42 if lo else 50)
        col = (200, 40, 50) if v.startswith("ARS") or v.startswith("PSA") or unk or hl else ((90, 120, 100) if lo else (40, 40, 40))
        d.text((px1 - 40, y), v, font=font("dela", int(size * s)), fill=col, anchor="rm")
    if tx.get("total"):
        y = py1 - 95 * s
        d.line((px0 + 30, y - 55 * s, px1 - 30, y - 55 * s), fill=(40, 40, 40), width=4)
        val, sc, mark = tx["total"][1], 1.0, None
        tp = tx.get("total_pop")  # 確定の値段が出る時刻(区切りの頭からの秒)。マーカーが引かれ、数字が大きく出て戻る
        if tp is not None:
            u = 1.0 if t is None else (t - tp) / 0.4
            if u < 0:
                val = tx.get("total_before", "？円")
            else:
                mark = min(1.0, u * 1.6)
                k = min(1.0, u)
                sc = 1 + 0.9 * (1 - k) ** 3 + 0.25 * math.sin(math.pi * k) * (1 - k)  # 大きく出て少し弾んで戻る
        if mark:
            d.rectangle((px0 + 20, y - 46 * s, px0 + 20 + (px1 - px0 - 40) * mark, y + 46 * s), fill=(255, 226, 80))
        d.text((px0 + 40, y), tx["total"][0], font=font("dela", int(54 * s)), fill=(40, 40, 40), anchor="lm")
        d.text((px1 - 40, y), val, font=font("dela", int(68 * s * sc)), fill=(200, 40, 50), anchor="rm")
    if tx.get("buy") is not None:  # 「買う？見送る？」の選択(-1=どちらも未選択)
        by = py1 + 60
        pops = tx.get("buy_pop", [])  # 各ボタンが一度だけ跳ねる時刻(区切りの頭からの秒)
        for k, (lab, col) in enumerate([("買う", (220, 40, 50)), ("見送る", (60, 90, 160))]):
            on = tx["buy"] == k
            q = 0.0
            if t is not None and k < len(pops):
                u = (t - pops[k]) / 0.35
                if 0 <= u <= 1:
                    q = math.sin(math.pi * u)  # 0→1→0 の一山
                    on = True
            sc = 1 + 0.12 * q; dy = -14 * q
            cx0, cy0 = 110 + k * 450 + 205, by + 70 + dy
            hw, hh = 205 * sc, 70 * sc
            d.rounded_rectangle((cx0 - hw, cy0 - hh, cx0 + hw, cy0 + hh), radius=30, fill=col if on else (255, 255, 255), outline=col, width=10)
            d.text((cx0, cy0), lab, font=font("dela", int(68 * sc)), fill=(255, 255, 255) if on else col, anchor="mm")
    if tx.get("cta"):  # 関連動画への案内(レシートの下・YouTube の表示より上)
        a, pill = tx["cta"]
        y = py1 + 50
        ctext(d, (W / 2, y), a, font("xb", 40), (255, 255, 255), 5)
        f = font("black", 50); tw = d.textlength(pill + " ▼", font=f)
        d.rounded_rectangle((W / 2 - tw / 2 - 36, y + 34, W / 2 + tw / 2 + 36, y + 114), radius=22, fill=(240, 192, 120))
        ctext(d, (W / 2, y + 74), pill + " ▼", f, (32, 96, 64))
    full = {"cx": 320, "cy": 180, "zoom": 1.0}
    return img, [slot(b["t"], 0, 0, W, H, b, blur=True, dim=0.55), slot(b["t"], 0, VID_Y2, W, vh, full, slide=True)]


# ---- C: サムネ特化(briefs/mewtwo_typeC.md)。最初と最後は「左にカード(白フチ)・右に短い行」、中盤は映像+下に字幕2行 ----
C_BG, C_SAFE_R = (40, 34, 30), 940


def c_text(d, xy, s, fo, fill):  # 黒フチ+右下に黒い影
    x, y = xy
    d.text((x + 8, y + 10), s, font=fo, fill=(0, 0, 0), anchor="mm", stroke_width=8, stroke_fill=(0, 0, 0))
    d.text((x, y), s, font=fo, fill=fill, anchor="mm", stroke_width=8, stroke_fill=(0, 0, 0))


def c_fit(d, s, size, maxw, kind="dela"):
    while size > 40 and d.textlength(s, font=font(kind, size)) + 16 > maxw:
        size -= 4
    return font(kind, size)


def layer_C(b, t=None):
    tx = b["texts"]
    img = Image.new("RGBA", (W, H), C_BG + (255,)); d = ImageDraw.Draw(img)
    pa = tx.get("pop_at")
    big = 1.0
    if pa is not None and t is not None:
        if t < pa:
            tx = {**tx, **tx.get("before", {})}
        else:
            k = min(1.0, (t - pa) / 0.35)
            big = 1 + 0.8 * (1 - k) ** 3 + 0.2 * math.sin(math.pi * k) * (1 - k)
    if tx.get("side"):  # 左にカード、右に短い行
        d.rectangle((30, 440, 530, 1360), fill=(255, 255, 255))
        hole(img, (46, 456, 514, 1344))
        lines = tx["side"]
        y = 900 - (len(lines) - 1) * 150 / 2
        for k, (s_, col, size) in enumerate(lines):
            sc = big if (pa is not None and k == len(lines) - 1) else 1.0
            c_text(d, (745, y), s_, c_fit(d, s_, int(size * sc), (C_SAFE_R - 560) * sc), tuple(col)); y += 150
        if tx.get("cta"):
            a, pill = tx["cta"]
            c_text(d, (W / 2, 1530), a, c_fit(d, a, 60, 900, "black"), (255, 255, 255))
            c_text(d, (W / 2, 1630), pill + " ▼", c_fit(d, pill + " ▼", 70, 900, "black"), (255, 230, 0))
        sl = [slot(b["t"], 46, 456, 468, 888, b)]
    else:  # 中盤: 映像は横幅いっぱい(拡大しない)、上下はぼかした同じ映像
        vh = W * 9 // 16
        vy = 240 + (1180 - vh) // 2
        hole(img, (0, 240, W, 1420))
        c1, c2 = tx.get("copy", ["", ""])
        if c1:
            c_text(d, (W / 2, 1500), c1, c_fit(d, c1, 70, 900, "black"), (255, 255, 255))
        if c2:
            c_text(d, (W / 2, 1620), c2, c_fit(d, c2, int(92 * big), 900 * big), tuple(tx.get("c2", (255, 230, 0))))
        if tx.get("vignette"):  # 四隅を暗く(映像の上に重ねる)
            v = Image.new("L", (W, 1180), 0)
            yy, xx = np.mgrid[0:1180, 0:W]
            r = np.sqrt(((xx - W / 2) / (W / 2)) ** 2 + ((yy - 590) / 590) ** 2)
            v = Image.fromarray((np.clip((r - 0.55) / 0.6, 0, 1) * 200).astype(np.uint8))
            dark = Image.new("RGBA", (W, 1180), (0, 0, 0, 255)); dark.putalpha(v)
            img.alpha_composite(dark, (0, 240))
        sl = [slot(b["t"], 0, 240, W, 1180, {}, blur=True, dim=0.5), slot(b["t"], 0, vy, W, vh, {})]
    if tx.get("flash") and t is not None and t < 0.2:  # 冒頭の白フラッシュ(30%→0)
        a = int(255 * 0.3 * (1 - t / 0.2))
        img.alpha_composite(Image.new("RGBA", (W, H), (255, 255, 255, a)))
    return img, sl


# ---- CHAT: チャット風(design5b 案9)。上に元動画、下に本人の言葉をトークの吹き出しで積む ----
def layer_CHAT(b, t=None):
    tx = b["texts"]
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    vh = W * 9 // 16
    VY = 170
    if tx.get("head"):
        ctext(d, (W / 2, 90), tx["head"], font("black", 52), (255, 255, 255), 6)
    tt = 1e9 if t is None else t
    shown = [m for m in tx.get("chat", []) if m[2] <= tt][-5:]
    y = 1500  # 下から上へ積む(新しいものが下)
    for who, s_, at in reversed(shown):
        k = 1.0 if at < 0 or t is None else min(1.0, (tt - at) / 0.25)
        big = who == "big"
        kind, size = ("dela", 96) if big else ("black", 54)
        while size > 30 and d.textlength(s_, font=font(kind, size)) > 780:  # 吹き出しが画面からはみ出さない
            size -= 2
        f = font(kind, int(size * (0.6 + 0.4 * k)))
        tw = d.textlength(s_, font=f); h = int(size * 1.9)
        y -= h
        if who == "me":  # 本人(右・緑)
            x1 = 930; d.rounded_rectangle((x1 - tw - 64, y, x1, y + h - 14), radius=40, fill=(120, 225, 120)); d.text((x1 - 32, y + (h - 14) / 2), s_, font=f, fill=(0, 0, 0), anchor="rm")
        elif who == "big":  # 結果(中央・黄)
            d.rounded_rectangle((W / 2 - tw / 2 - 50, y, W / 2 + tw / 2 + 50, y + h - 14), radius=50, fill=(255, 230, 0), outline=(0, 0, 0), width=8); d.text((W / 2, y + (h - 14) / 2), s_, font=f, fill=(200, 30, 40), anchor="mm")
        else:  # 問い(左・白)
            x0 = 70; d.rounded_rectangle((x0, y, x0 + tw + 64, y + h - 14), radius=40, fill=(255, 255, 255)); d.text((x0 + 32, y + (h - 14) / 2), s_, font=f, fill=(0, 0, 0), anchor="lm")
        y -= 22
    if tx.get("cta"):
        a, pill = tx["cta"]
        ctext(d, (W / 2, 1585), a, font("xb", 40), (255, 255, 255), 5)
        f = font("black", 50); tw = d.textlength(pill + " ▼", font=f)
        d.rounded_rectangle((W / 2 - tw / 2 - 36, 1620, W / 2 + tw / 2 + 36, 1700), radius=22, fill=(240, 192, 120))
        ctext(d, (W / 2, 1660), pill + " ▼", f, (32, 96, 64))
    d.rectangle((0, VY - 6, W, VY), fill=(255, 255, 255)); d.rectangle((0, VY + vh, W, VY + vh + 6), fill=(255, 255, 255))
    return img, [slot(b["t"], 0, 0, W, H, b, blur=True, dim=0.6), slot(b["t"], 0, VY, W, vh, {"cx": 320, "cy": 180, "zoom": 1.0}, slide=True)]


# ---- TL: 時系列(design5d 案16)。上に元動画、下に縦の線で「2年前→提出→返却→結果」、今の段が光る ----
TL_STEPS = [("2年前", "2,000円で購入"), ("提出", "PSA鑑定へ"), ("返却", "ラベルは…"), ("結果", "？")]


def layer_TL(b, t=None):
    tx = b["texts"]
    pa = tx.get("pop_at"); big = 1.0
    if pa is not None and t is not None:
        if t < pa:
            tx = {**tx, **tx.get("before", {})}
        else:
            k = min(1.0, (t - pa) / 0.35); big = 1 + 0.6 * (1 - k) ** 3
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    vh = W * 9 // 16; VY = 200
    if tx.get("head"):
        f = font("dela", 80)
        while d.textlength(tx["head"], font=f) > W - 80: f = font("dela", f.size - 4)
        ctext(d, (W / 2, 105), tx["head"], f, (255, 230, 0), 8)
    d.rectangle((0, VY - 6, W, VY), fill=(255, 255, 255)); d.rectangle((0, VY + vh, W, VY + vh + 6), fill=(255, 255, 255))
    step = tx["step"]; x = 150; y0 = 900
    d.line((x, y0, x, y0 + 3 * 170), fill=(200, 200, 200), width=10)
    d.line((x, y0, x, y0 + min(step, 3) * 170), fill=(255, 42, 42), width=10)
    for i, (a, v) in enumerate(TL_STEPS):
        y = y0 + i * 170; on = i <= step
        if i == 3: v = tx.get("result", v)
        d.ellipse((x - 38, y - 38, x + 38, y + 38), fill=(255, 42, 42) if i == step else ((255, 255, 255) if on else (90, 90, 90)))
        d.text((x + 80, y - 34), a, font=font("black", 42), fill=(255, 255, 255) if on else (130, 130, 130), anchor="lm")
        size = int((76 if i == step else 54) * (big if i == 3 and i == step else 1))
        f = font("dela", size)
        while d.textlength(v, font=f) > 760: f = font("dela", f.size - 4)
        ctext(d, (x + 80, y + 36), v, f, (255, 230, 0) if i == step else ((255, 255, 255) if on else (130, 130, 130)), 7, anchor="lm")
    if tx.get("cta"):
        a, pill = tx["cta"]
        ctext(d, (W / 2, 1585), a, font("xb", 40), (255, 255, 255), 5)
        f = font("black", 50); tw = d.textlength(pill + " ▼", font=f)
        d.rounded_rectangle((W / 2 - tw / 2 - 36, 1620, W / 2 + tw / 2 + 36, 1700), radius=22, fill=(240, 192, 120))
        ctext(d, (W / 2, 1660), pill + " ▼", f, (32, 96, 64))
    return img, [slot(b["t"], 0, 0, W, H, b, blur=True, dim=0.6), slot(b["t"], 0, VY, W, vh, {"cx": 320, "cy": 180, "zoom": 1.0}, slide=True)]


# ---- NEWS: 新聞の見出し風(design5d 案17)。明朝の大見出し+白黒写真+紙の質感 ----
def layer_NEWS(b, t=None):
    tx = b["texts"]
    pa = tx.get("pop_at"); big = 1.0
    if pa is not None and t is not None:
        if t < pa:
            tx = {**tx, **tx.get("before", {})}
        else:
            k = min(1.0, (t - pa) / 0.35); big = 1 + 0.25 * (1 - k) ** 3
    img = Image.new("RGBA", (W, H), (238, 232, 218, 255)); d = ImageDraw.Draw(img)
    rng = np.random.default_rng(3)  # 紙の質感(固定の点)
    for _ in range(2500):
        x, y = rng.integers(0, W), rng.integers(0, H); d.point((int(x), int(y)), fill=(220, 212, 195, 255))
    d.line((60, 120, 1020, 120), fill=(20, 20, 20), width=6); d.line((60, 136, 1020, 136), fill=(20, 20, 20), width=2)
    d.text((60, 170), "トレカ鑑定　第48号", font=font("minm", 40), fill=(60, 60, 60))
    hl = tx["hl"]; f = font("min", int(140 * big))
    while d.textlength(hl, font=f) > 960: f = font("min", f.size - 6)
    d.text((W / 2, 350), hl, font=f, fill=(20, 20, 20), anchor="mm")
    sub = tx.get("sub", "")
    if sub:
        f = font("min", 54)
        while d.textlength(sub, font=f) > 940: f = font("min", f.size - 4)
        d.text((W / 2, 490), sub, font=f, fill=(150, 20, 20), anchor="mm")
    pw = W - 120; ph = pw * 9 // 16; PY = 580
    hole(img, (60, PY, 60 + pw, PY + ph))
    d.rectangle((56, PY - 4, 64 + pw, PY + ph + 4), outline=(20, 20, 20), width=4)
    d.text((60, PY + ph + 30), "▲ " + tx.get("cap", "2年前に2,000円で買った拡張シートのミュウツー"), font=font("minm", 36), fill=(60, 60, 60))
    d.line((60, PY + ph + 100, 1020, PY + ph + 100), fill=(20, 20, 20), width=2)
    if tx.get("body"):
        f = font("minm", 44); y = PY + ph + 120
        for ln in tx["body"]:
            d.text((60, y), ln, font=f, fill=(30, 30, 30)); y += 58
    if tx.get("cta"):
        a, pill = tx["cta"]
        d.text((W / 2, 1575), a, font=font("min", 44), fill=(20, 20, 20), anchor="mm")
        f = font("min", 54); tw = d.textlength(pill + " ▼", font=f)
        d.rectangle((W / 2 - tw / 2 - 30, 1610, W / 2 + tw / 2 + 30, 1700), fill=(150, 20, 20))
        d.text((W / 2, 1655), pill + " ▼", font=f, fill=(255, 255, 255), anchor="mm")
    return img, [slot(b["t"], 60, PY, pw, ph, {"cx": 320, "cy": 180, "zoom": 1.0}, gray=True)]


# ---- THUMB: サムネ連動(briefs/thumbsync_mewtwo.md)。全面のカード+集中線+上に白・下に黄の極太文字 ----
def speed_lines(img, strength=1.0, seed=1, n=90, inner=0.42):
    import random
    r = random.Random(seed); d = ImageDraw.Draw(img); cx, cy, R = W / 2, H * 0.47, 1500
    for i in range(n):
        a = 2 * math.pi * i / n + r.uniform(-0.02, 0.02); w = r.uniform(0.006, 0.02) * strength
        rin = R * (inner + r.uniform(0, 0.15))
        d.polygon([(cx + R * math.cos(a - w), cy + R * math.sin(a - w)), (cx + R * math.cos(a + w), cy + R * math.sin(a + w)),
                   (cx + rin * math.cos(a), cy + rin * math.sin(a))], fill=(0, 0, 0, 255))


def thick(d, xy, s, size, fill, maxw=1000, stroke=14):
    while size > 40 and d.textlength(s, font=font("dela", size)) > maxw:
        size -= 4
    x, y = xy
    d.text((x + 6, y + 10), s, font=font("dela", size), fill=(0, 0, 0), anchor="mm", stroke_width=stroke, stroke_fill=(0, 0, 0))
    d.text((x, y), s, font=font("dela", size), fill=fill, anchor="mm", stroke_width=stroke, stroke_fill=(0, 0, 0))


def layer_THUMB(b, t=None):
    tx = b["texts"]
    pa = tx.get("pop_at"); big = 1.0; after = 9.0
    if pa is not None and t is not None:
        if t < pa:
            tx = {**tx, **tx.get("before", {})}
        else:
            after = t - pa; k = min(1.0, after / 0.35); big = 1 + 0.5 * (1 - k) ** 3 + 0.12 * math.sin(math.pi * k) * (1 - k)
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    if tx.get("lines", 0):
        speed_lines(img, tx["lines"], seed=b.get("seed", 1))
    if tx.get("l1"):
        thick(d, (W / 2, 560), tx["l1"], 120, (255, 255, 255))
    y = tx.get("y2", 1330)
    for s_ in tx.get("l2", []):
        thick(d, (W / 2, y), s_, int(190 * big), tuple(tx.get("c2", (255, 230, 0))), maxw=1000 * big); y += 200
    if tx.get("cta"):
        d.rounded_rectangle((W / 2 - 340, 1560, W / 2 + 340, 1660), radius=24, fill=(240, 192, 120), outline=(0, 0, 0), width=6)
        d.text((W / 2, 1610), tx["cta"], font=font("black", 56), fill=(32, 96, 64), anchor="mm")
    fl = None
    if tx.get("flash") and t is not None and t < 0.2: fl = t
    if pa is not None and t is not None and 0 <= after < 0.2 and tx.get("pop_flash"): fl = after
    if fl is not None:
        img.alpha_composite(Image.new("RGBA", (W, H), (255, 255, 255, int(255 * 0.5 * (1 - fl / 0.2)))))
    return img, [slot(b["t"], 0, 0, W, H, b, enhance=True, delogo=b.get("delogo", False), slide=True)]


# ---- QUIZ: クイズ3択(design5b 案7)+シリーズの題名。上にコピー、中に元動画(拡大なし)、下に3択。答えの瞬間に正解が光る ----
def layer_QUIZ(b, t=None):
    tx = b["texts"]
    pa = tx.get("pop_at"); big = 1.0; shown = tx.get("answer")
    if pa is not None and t is not None:
        if t < pa:
            tx = {**tx, **tx.get("before", {})}; shown = tx.get("answer")
        else:
            k = min(1.0, (t - pa) / 0.35); big = 1 + 0.25 * (1 - k) ** 3
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    if tx.get("series"):  # シリーズの題名(毎回同じ見た目)
        f = font("black", 40); tw = d.textlength(tx["series"], font=f)
        d.rounded_rectangle((W / 2 - tw / 2 - 30, 26, W / 2 + tw / 2 + 30, 92), radius=33, fill=(200, 30, 40))
        d.text((W / 2, 59), tx["series"], font=f, fill=(255, 255, 255), anchor="mm")
    l1, l2 = tx.get("copy", ["", ""])
    if l1:
        ctext(d, (W / 2, 160), l1, font("xb", 60), (255, 255, 255), 6)
    f = font("dela", 92)
    while d.textlength(l2, font=f) > W - 80: f = font("dela", f.size - 4)
    ctext(d, (W / 2, 255 if l1 else 210), l2, f, (255, 220, 60), 8)
    vh = W * 9 // 16; VY = 330
    d.rectangle((0, VY - 6, W, VY), fill=(255, 255, 255)); d.rectangle((0, VY + vh, W, VY + vh + 6), fill=(255, 255, 255))
    q = tx.get("q", "何点だと思う？")
    ctext(d, (W / 2, 1010), q, font("dela", 70), (255, 255, 255), 7)
    for i, opt in enumerate(tx.get("opts", ["PSA 8", "PSA 9", "PSA 10"])):
        y = 1090 + i * 165; on = shown == opt; off = shown is not None and not on
        sc = big if on else 1.0; hw, hh = 380 * sc, 70 * sc; cx, cy = W / 2, y + 70
        d.rounded_rectangle((cx - hw, cy - hh, cx + hw, cy + hh), radius=40, fill=(255, 230, 0) if on else ((70, 70, 70) if off else (255, 255, 255)), outline=(0, 0, 0), width=8)
        d.text((cx, cy), opt, font=font("dela", int(76 * sc)), fill=(200, 30, 40) if on else ((150, 150, 150) if off else (0, 0, 0)), anchor="mm")
        if on and tx.get("price"):
            d.text((cx + hw - 30, cy), tx["price"], font=font("black", int(44 * sc)), fill=(0, 0, 0), anchor="rm")
    if tx.get("cta"):
        a, pill = tx["cta"]
        ctext(d, (W / 2, 1600), a, font("xb", 40), (255, 255, 255), 5)
        f = font("black", 50); tw = d.textlength(pill + " ▼", font=f)
        d.rounded_rectangle((W / 2 - tw / 2 - 36, 1630, W / 2 + tw / 2 + 36, 1705), radius=22, fill=(240, 192, 120))
        ctext(d, (W / 2, 1667), pill + " ▼", f, (32, 96, 64))
    return img, [slot(b["t"], 0, 0, W, H, b, blur=True, dim=0.6), slot(b["t"], 0, VY, W, vh, {"cx": 320, "cy": 180, "zoom": 1.0}, slide=True)]


LAYER = {"A": layer_A, "B": layer_B, "C": layer_C, "D": layer_D, "E": layer_E, "D2": layer_D2, "C": layer_C, "CHAT": layer_CHAT, "TL": layer_TL, "NEWS": layer_NEWS, "THUMB": layer_THUMB, "QUIZ": layer_QUIZ}


def still(src, key, b, t=None):
    """絵コンテ用: 枠に元動画の1コマを貼り、上に絵を重ねる。t: 区切りの頭からの秒(答えが出る前後を描き分ける)"""
    over, slots = LAYER[key](b, t) if key in ("D2", "C", "CHAT", "TL", "NEWS", "THUMB", "QUIZ") else LAYER[key](b)
    img = Image.new("RGB", (W, H), (0, 0, 0))
    for s in slots:
        im = frame(src, s["t"])
        x, y, cw, ch = crop_box(*im.size, s["w"], s["h"], s["cx"], s["cy"], s["zoom"])
        p = im.crop((x, y, x + cw, y + ch)).resize((s["w"], s["h"]), Image.LANCZOS)
        if s.get("blur"):
            p = p.filter(ImageFilter.GaussianBlur(14))
        if s.get("dim"):
            p = Image.blend(p, Image.new("RGB", p.size, (20, 20, 20)), s["dim"])
        img.paste(p, (s["x"], s["y"]))
    return Image.alpha_composite(img.convert("RGBA"), over).convert("RGB")


def board(p, src, out_dir):
    for v in p["variants"]:
        panels = []  # 答えが出る区切りは「出る前」「出た後」の2コマに分ける
        for b in v["beats"]:
            pa = b["texts"].get("pop_at")
            if pa is not None:
                panels.append((b, 0.0, "(答えの前) ")); panels.append((b, pa + 1.0, f"({pa:.1f}秒で答え) "))
            else:
                panels.append((b, None, ""))
        frames = [still(src, v["key"], b, t).resize((W // 3, H // 3), Image.LANCZOS) for b, t, _ in panels]
        tw, th = frames[0].size
        sheet = Image.new("RGB", (16 + len(frames) * (tw + 16), th + 520), "white")
        d = ImageDraw.Draw(sheet)
        d.text((20, 18), f"案{v['key']}  {v['name']}", font=font("dela", 44), fill=(30, 30, 30))
        d.text((20, 80), "構成: " + v["structure"], font=font("bold", 26), fill=(60, 60, 60))
        d.text((20, 118), "デザイン: " + v["design"], font=font("bold", 26), fill=(60, 60, 60))
        for k, (fr, (b, _, tag)) in enumerate(zip(frames, panels)):
            x = 16 + k * (tw + 16)
            sheet.paste(fr, (x, 170))
            line, yy = "", 170 + th + 10
            n = v["beats"].index(b) + 1
            for ch in f"{n}. {tag}声: " + b.get("say", ""):
                if d.textlength(line + ch, font=font("bold", 21)) > tw:
                    d.text((x, yy), line, font=font("bold", 21), fill=(70, 70, 70)); yy += 27; line = ch
                else:
                    line += ch
            d.text((x, yy), line, font=font("bold", 21), fill=(70, 70, 70))
            if b.get("fx"):  # 演出(動き・効果・音)の指示を赤で
                line, yy = "", yy + 34
                for ch in "演出: " + b["fx"]:
                    if d.textlength(line + ch, font=font("bold", 20)) > tw:
                        d.text((x, yy), line, font=font("bold", 20), fill=(190, 40, 50)); yy += 26; line = ch
                    else:
                        line += ch
                d.text((x, yy), line, font=font("bold", 20), fill=(190, 40, 50))
        out = os.path.join(out_dir, f"variant_{p['name']}_{v['key']}.png")
        sheet.save(out); print(out, sheet.size)


SE_GAIN = {"whoosh2": 0.22, "impact2": 0.5, "register": 0.2}  # 新しい効果音は声に負けない大きさ


def kinetic_frame(path, fi, n, words, push=0.10):
    """動く冒頭の1コマ: カードの絵はゆっくり寄り、言葉が時刻どおりに1つずつ弾んで積み上がる。止まる瞬間を作らない。
    words: [{"t": 出る秒, "text": 文字, "size": 大きさ, "color": [r,g,b]}]。最後は切らずに終わる(切り替えは手動)。"""
    t = fi / 30
    card = Image.open(path).convert("RGB")
    bg = card.resize((W, H), Image.LANCZOS).filter(ImageFilter.GaussianBlur(30))
    bg = Image.blend(bg, Image.new("RGB", (W, H), (10, 10, 10)), 0.6)
    sc = 1 + push * fi / max(1, n - 1)
    cw = int(W * 0.92 * sc); ch = int(cw * card.height / card.width)
    img = bg.convert("RGBA")
    img.paste(card.resize((cw, ch), Image.LANCZOS), (int(W / 2 - cw / 2), int(H / 2 - ch / 2)))
    shown = [w for w in words if t >= w["t"]]
    if shown:
        hs_all = [int(w.get("size", 90)) + 40 for w in words]  # 位置は最後の並びで固定(言葉が増えても上下に動かない)
        top = H / 2 - sum(hs_all) / 2
        hs = hs_all[: len(shown)]
        band = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(band).rectangle((0, top - 30, W, top + sum(hs) + 30), fill=(0, 0, 0, 165))
        img.alpha_composite(band)
        d = ImageDraw.Draw(img)
        y = top
        for w, h in zip(shown, hs):
            k = min(1.0, (t - w["t"]) / 0.18)
            pop = 1 + 0.45 * (1 - k) ** 2  # 出た瞬間だけ大きく、すぐ戻る
            f = font("dela", int(w.get("size", 90) * pop))
            while d.textlength(w["text"], font=f) > W - 50:
                f = font("dela", f.size - 4)
            ctext(d, (W / 2, y + h / 2), w["text"], f, tuple(w.get("color", (255, 255, 255))), 9)
            y += h
    return img


def intro_frame(path, fi, n, copy=None):
    """冒頭のカード全面表示の1コマ。カードはゆっくり寄り(動き)、文字は画面の中央に弾んで出る。
    最後の 0.13 秒で元動画の枠の位置へ縮みながら消える。"""
    card = Image.open(path).convert("RGB")
    bg = card.resize((W, H), Image.LANCZOS).filter(ImageFilter.GaussianBlur(30))
    bg = Image.blend(bg, Image.new("RGB", (W, H), (10, 10, 10)), 0.6)
    cw = int(W * 0.9); ch = int(cw * card.height / card.width)
    out_n = 4  # 縮んで消えるコマ数
    k = max(0.0, (fi - (n - out_n)) / out_n)
    e = 1 - (1 - k) ** 2
    push = 1 + 0.12 * min(1.0, fi / max(1, n - out_n))  # ゆっくり寄る
    sc = push * (1 - 0.55 * e)
    cy = H / 2 + (VID_Y2 + W * 9 // 32 - H / 2) * e
    c = card.resize((int(cw * sc), int(ch * sc)), Image.LANCZOS)
    img = bg.convert("RGBA")
    img.paste(c, (int(W / 2 - c.width / 2), int(cy - c.height / 2)))
    if copy:  # 何の画面かを一言で。画面の中央に、帯を敷いて読みやすく
        d = ImageDraw.Draw(img, "RGBA")
        l1, l2 = copy
        u = min(1.0, fi / 6)
        pop = 1 + 0.3 * (1 - u) ** 2 - 0.08 * math.sin(math.pi * u) * (1 - u)  # 大きめに出て弾んで戻る

        def fit(kind, size, text, margin):  # 拡大しても画面からはみ出さない(1コマ目はサムネイルにもなる)
            f = font(kind, int(size))
            while d.textlength(text, font=f) > W - margin:
                f = font(kind, f.size - 4)
            return f
        band = Image.new("RGBA", (W, H), (0, 0, 0, 0))  # 帯は重ねて塗る(直接塗ると下の動画が透ける)
        ImageDraw.Draw(band).rectangle((0, H / 2 - 170, W, H / 2 + 150), fill=(0, 0, 0, 150))
        img.alpha_composite(band); d = ImageDraw.Draw(img, "RGBA")
        if l1:
            ctext(d, (W / 2, H / 2 - 85), l1, fit("xb", 66 * pop, l1, 80), (255, 255, 255), 7)
        base = fit("dela", 120, l2, 80).size
        ctext(d, (W / 2, H / 2 + 50), l2, fit("dela", base * pop, l2, 40), (255, 220, 60), 10)
    a = int(255 * (1 - k))
    img.putalpha(img.getchannel("A").point(lambda v: v * a // 255))
    return img


def render(p, v, src, out):
    """1案を動画にする。各区切り: 声(元動画・間詰め)の長さだけ、枠に元動画を流して絵を重ねる。"""
    src_w, src_h = rs.probe(src)
    rs.JET_MIN, rs.JET_PAD = ps.JET_MIN, ps.JET_PAD
    with tempfile.TemporaryDirectory() as td:
        parts, audio, t, prev_band = [], [], 0.0, None
        for i, b in enumerate(v["beats"]):
            voices, sfx = [], []
            for j, c in enumerate(b["cuts"]):
                a0, a1 = to_sec(c["a"][0]), to_sec(c["a"][1])
                spans = ps.voice_spans(src, a0, a1) if c.get("jet", True) else [(a0, a1)]
                at = sum(len(x) for x in voices) / SR
                v_ = np.concatenate([rs.source_audio(src, s0, s1) for s0, s1 in spans])
                voices.append(np.zeros_like(v_) if c.get("mute") else v_)  # mute: 映像だけ使い、声は入れない(倍率の連打など)
                if c.get("se"):
                    sfx.append((at, c["se"]))
            voice = np.concatenate(voices)
            n = max(1, round(len(voice) / SR * 30))
            dur = n / 30
            if i > 0 and b.get("slide", True):  # slide: false の区切りは切り替えの動きと音なし
                sfx.insert(0, (-0.05, "whoosh"))  # シュッは切り替えの動きと同時
            audio.append((t, voice, sfx))
            if b["texts"].get("total_pop") is not None:
                sfx.append((b["texts"]["total_pop"], "ding"))  # 確定の値段に合わせてチーン
            if b["texts"].get("pop_at") is not None:
                sfx.append((b["texts"]["pop_at"], b["texts"].get("pop_se", "register")))  # 答えが出る瞬間の音
            anim = (bool(b["texts"].get("buy_pop")) or b["texts"].get("total_pop") is not None
                    or b["texts"].get("pop_at") is not None or b["texts"].get("flash") or b["texts"].get("chat")) and v["key"] in ("D2", "C", "CHAT", "TL", "NEWS", "THUMB", "QUIZ")
            if anim:  # 時刻ごとに描いた連番(ボタンが跳ねる)
                for fi in range(n):
                    LAYER[v["key"]](b, fi / 30)[0].save(os.path.join(td, f"o{i:02d}_{fi:04d}.png"))
                over_in = ["-framerate", "30", "-i", os.path.join(td, f"o{i:02d}_%04d.png")]
                slots = LAYER[v["key"]](b)[1]
            else:
                over, slots = LAYER[v["key"]](b)
                png = os.path.join(td, f"o{i:02d}.png"); over.save(png)
                over_in = ["-loop", "1", "-framerate", "30", "-i", png]
            args, fc, last = [], [f"color=c=black:s={W}x{H}:r=30:d={dur + 1:.3f}[base]"], "base"
            nin = len(slots)
            for k, s in enumerate(slots):
                vlen = min(dur + 0.5, b.get("v_max", 1e9))  # v_max: 元動画の字幕が出る前で映像だけ止める(声は続ける)
                args += ["-ss", f"{s['t']:.3f}", "-t", f"{vlen:.3f}", "-i", src]
                x, y, cw, ch = crop_box(src_w, src_h, s["w"], s["h"], s["cx"], s["cy"], s["zoom"])
                pre = "delogo=x=1:y=1:w=205:h=68," if s.get("delogo") else ""  # 元動画の左上のロゴを周りの色で埋める
                if s.get("enhance"):  # 拡大しても荒れにくく: ノイズを抑えてから段階的に拡大し、輪郭を少し立てる(AI で描き足さない)
                    f = (f"[{k}:v]{pre}hqdn3d=3:3:4:4,crop={cw}:{ch}:{x}:{y},scale={cw * 2}:{ch * 2}:flags=lanczos,"
                         f"scale={s['w']}:{s['h']}:flags=lanczos,unsharp=5:5:0.9:5:5:0.0,eq=contrast=1.06:saturation=1.12,setsar=1,fps=30")
                else:
                    f = f"[{k}:v]{pre}crop={cw}:{ch}:{x}:{y},scale={s['w']}:{s['h']}:flags=lanczos,setsar=1,fps=30"
                if s.get("blur"):
                    f += ",boxblur=24:2"
                if s.get("gray"):  # 白黒(新聞風)
                    f += ",hue=s=0"
                if s.get("dim"):
                    f += f",eq=brightness={-s['dim'] * 0.5:.2f}"
                fc.append(f + f",setpts=PTS-STARTPTS,tpad=stop_mode=clone:stop_duration={dur + 1:.2f}[s{k}]")
                if s.get("slide") and i > 0 and prev_band and b.get("slide", True):  # 前の映像が右へ抜け、新しい映像が左から入る
                    args += ["-loop", "1", "-t", f"{SLIDE_T + 0.1:.2f}", "-i", prev_band]
                    P = f"(1-pow(1-min(t/{SLIDE_T},1),3))"
                    fc.append(f"[{nin}:v]setpts=PTS-STARTPTS[pv{k}]")
                    fc.append(f"[{last}][pv{k}]overlay=x='{s['w']}*{P}':y={s['y']}:eval=frame:eof_action=pass[q{k}]")
                    fc.append(f"[q{k}][s{k}]overlay=x='-{s['w']}*(1-{P})':y={s['y']}:eval=frame[b{k}]"); last = f"b{k}"
                    nin += 1
                else:
                    fc.append(f"[{last}][s{k}]overlay={s['x']}:{s['y']}[b{k}]"); last = f"b{k}"
            args += over_in
            fc.append(f"[{nin}:v]format=rgba[ov];[{last}][ov]overlay=0:0,format=yuv420p")
            part = os.path.join(td, f"p{i:02d}.mp4")
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *args, "-an", "-filter_complex", ";".join(fc),
                            "-frames:v", str(n), "-c:v", "libx264", "-crf", "17", part], check=True)
            parts.append(part)
            band = [q for q in slots if q.get("slide")]
            if band:  # 次の切り替え用に、この区切りの最後のコマの元動画部分を取っておく
                prev_band = os.path.join(td, f"band{i:02d}.png")
                subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-sseof", "-0.1", "-i", part, "-update", "1",
                                "-vf", f"crop={band[0]['w']}:{band[0]['h']}:0:{band[0]['y']}", prev_band], check=True)
            t += dur
        total = t
        intro = p.get("intro")  # 冒頭だけカードの画像を画面いっぱいに出し、元の画面へ縮んで消える
        if intro:
            n_in = round(intro.get("dur", 0.5) * 30)
            for fi in range(n_in):
                fr = (kinetic_frame(intro["image"], fi, n_in, intro["words"]) if intro.get("words")
                      else intro_frame(intro["image"], fi, n_in, intro.get("copy")))
                fr.save(os.path.join(td, f"in_{fi:04d}.png"))
            for w in intro.get("words", []):  # 言葉が出るたびに短い打撃音
                if w.get("se"):
                    audio.append((w["t"], np.zeros(1, np.float32), [(0, w["se"])]))
            if intro.get("before_voice"):  # 声と重ねない: 冒頭を頭に足し、声と効果音を後ろへずらす
                first = os.path.join(td, "first.png")
                subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", parts[0], "-frames:v", "1", first], check=True)
                clip = os.path.join(td, "intro.mp4")
                subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-framerate", "30", "-i", first,
                                "-framerate", "30", "-i", os.path.join(td, "in_%04d.png"), "-filter_complex",
                                "[0:v][1:v]overlay=0:0:eof_action=pass,format=yuv420p", "-frames:v", str(n_in),
                                "-c:v", "libx264", "-crf", "17", clip], check=True)
                parts.insert(0, clip)
                audio = [(at + n_in / 30, x, sfx) for at, x, sfx in audio]
                total += n_in / 30
            if intro.get("whoosh", True):
                audio.append((max(0.0, n_in / 30 - 0.2), np.zeros(1, np.float32), [(0, "whoosh")]))
        mix = np.zeros(int((total + 0.5) * SR), np.float32)
        for at, x, sfx in audio:
            i0 = int(at * SR); mix[i0:i0 + len(x)] += x[: len(mix) - i0]
            for dt, name in sfx:
                name = p.get("se_map", {}).get(name, name)  # 案ごとに効果音を差し替え(過去の動画は元の音のまま)
                s_ = se.get(name) * SE_GAIN.get(name, 0.3)
                j0 = max(0, int((at + dt) * SR)); mix[j0:j0 + len(s_)] += s_[: len(mix) - j0]
        mix = mix[: int(total * SR)]
        mix /= max(1.0, np.abs(mix).max() / 0.95)
        wav = os.path.join(td, "mix.wav"); se.write_wav(wav, mix)
        lst = os.path.join(td, "list.txt")
        open(lst, "w").write("".join(f"file '{q}'\n" for q in parts))
        vin, vmap = [], ["-map", "0:v"]
        if intro and not intro.get("before_voice"):
            vin = ["-framerate", "30", "-i", os.path.join(td, "in_%04d.png")]
            vmap = ["-filter_complex", "[0:v][2:v]overlay=0:0:eof_action=pass,format=yuv420p[v]", "-map", "[v]"]
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst, "-i", wav, *vin,
                        *vmap, "-map", "1:a", "-c:v", "libx264", "-crf", "19", "-pix_fmt", "yuv420p",
                        "-af", "loudnorm=I=-14:TP=-1.0:LRA=11", "-c:a", "aac", "-b:a", "192k", "-shortest",
                        "-movflags", "+faststart", out], check=True)
    print(f"{out} ({total:.1f}s)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("plan"); ap.add_argument("source"); ap.add_argument("--out-dir", required=True)
    ap.add_argument("--video", nargs="*", help="動画にする案の key(例: A B)")
    a = ap.parse_args()
    p = json.load(open(a.plan, encoding="utf-8"))
    os.makedirs(a.out_dir, exist_ok=True)
    if a.video is None:
        board(p, a.source, a.out_dir)
        return
    for v in p["variants"]:
        if v["key"] in a.video:
            render(p, v, a.source, os.path.join(a.out_dir, f"variant_{p['name']}_{v['key']}.mp4"))


if __name__ == "__main__":
    main()
