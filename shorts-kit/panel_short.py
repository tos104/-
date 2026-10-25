#!/usr/bin/env python3
"""3段レイアウトのショート(上=見出し2行 / 中=元動画を横長のまま / 下=解説パネル)。本人の声・ジェットカット。

参考: ユーザー提供の見本(2026-10-24, 720x1280)を実測して 1080x1920 に拡大した寸法と色。

設計図(JSON):
{
  "speed": 1.0,
  "beats": [                                     # 見出しとパネルが変わる区切り
    {"cuts": [{"a": ["15:54.0", "15:58.05"], "v": "14:45.0", "jet": false, "zoom": [285, 190, 1.6]}],
     "head": ["30万で買った青眼が", "{化けるか！？}"], "tone": "red",      # 2行目の {} を強調色に
     "panel": {"pill": "30万 → 130万", "above": "", "below": "の勝負", "foot": "※撮影時の紹介相場", "pill_tone": "green"},
     "open": true,                                # 冒頭用: 背景に集中線
     "say": "30万か130万かのチャレンジ…せーの",    # 絵コンテ用(元動画の声)
     "why": "最初の1秒で賭け金を見せる"},
    {"panel": {"thumb": ["15:00.0", 190, 50, 190, 280], "lines": ["PSA10が150万の頃に", "{30万}で買えた"], "foot": "※本人談"}}
  ]
}
  python3 panel_short.py plan.json source.mp4 --board board.png   # 絵コンテ(実際の画面と同じ合成)
  python3 panel_short.py plan.json source.mp4 --out out.mp4
"""
import argparse, functools, json, math, os, re, subprocess, tempfile
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import se
import rich_short as rs
from make_short import to_sec

SR = rs.SR
W, H = 1080, 1920
BAND = (400, 1110)          # 黒い帯
VID_Y, VID_H = 451, 608     # 元動画(16:9)
PANEL = (1110, 1590)
HERE = os.path.dirname(os.path.abspath(__file__))
F_HEAD = os.path.join(HERE, "fonts", "MPLUSRounded1c-ExtraBold.ttf")
F_BODY = os.path.join(HERE, "fonts", "MPLUSRounded1c-Bold.ttf")
F_BIG = os.path.join(HERE, "fonts", "MPLUSRounded1c-Black.ttf")
CREAM, EDGE_TOP, EDGE_BOT = (239, 239, 230), (186, 187, 172), (182, 183, 174)
INK, SUB = (26, 56, 48), (120, 126, 120)
TONE = {"red": (180, 35, 44), "green": (32, 96, 64)}
PILL = {"green": (210, 234, 96), "orange": (240, 192, 120)}
JET_MIN, JET_PAD = 0.35, 0.10  # 0.35 秒以上の間だけ詰める。語尾が切れないよう前後に 0.1 秒残す
SLIDE = 0.25  # 切り替えで元動画が左へ流れる秒数


def font(path, size):
    return ImageFont.truetype(path, size)


def rich(d, cy, text, f, base, accent):
    """{...} を強調色にして、中央揃えで 1 行描く。"""
    parts = [(p.strip("{}"), accent if p.startswith("{") else base) for p in re.split(r"(\{.+?\})", text) if p]
    x = (W - sum(d.textlength(p, font=f) for p, _ in parts)) / 2
    for p, c in parts:
        d.text((x, cy), p, font=f, fill=c, anchor="lm")
        x += d.textlength(p, font=f)


def fit(d, text, path, size, width):
    while d.textlength(re.sub(r"[{}]", "", text), font=font(path, size)) > width and size > 30:
        size -= 2
    return font(path, size)


@functools.lru_cache(maxsize=64)
def _frame(source, t):
    with tempfile.NamedTemporaryFile(suffix=".png") as f:
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{t:.3f}", "-i", source,
                        "-frames:v", "1", f.name], check=True)
        im = Image.open(f.name).convert("RGB")
        im.load()
    return im


def grab(source, t, box=None):
    """元動画の 1 コマ(必要なら切り抜き)。"""
    im = _frame(source, to_sec(t))
    if box:
        x, y, w, h = box
        im = im.crop((x, y, x + w, y + h))
    return im


def background(open_lines=False):
    img = Image.new("RGB", (W, H), CREAM)
    px = np.array(img).astype(np.float32)
    y = np.arange(H)[:, None]
    top = np.clip(1 - y / 150, 0, 1)[..., None]
    bot = np.clip((y - PANEL[1]) / (H - PANEL[1]), 0, 1)[..., None]
    px = px * (1 - top) + np.array(EDGE_TOP) * top
    px = px * (1 - bot) + np.array(EDGE_BOT) * bot
    img = Image.fromarray(px.astype(np.uint8))
    if open_lines:  # 集中線(乱数は固定)
        rng = np.random.default_rng(7)
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(lay)
        cx, cy = W / 2, (BAND[0] + BAND[1]) / 2
        for k in range(90):
            a = 2 * math.pi * k / 90 + rng.uniform(-0.02, 0.02)
            r0, r1 = rng.uniform(560, 760), 1500
            w = rng.uniform(0.006, 0.016)
            pts = [(cx + r1 * math.cos(a - w), cy + r1 * math.sin(a - w)),
                   (cx + r0 * math.cos(a), cy + r0 * math.sin(a)),
                   (cx + r1 * math.cos(a + w), cy + r1 * math.sin(a + w))]
            d.polygon(pts, fill=(150, 152, 140, 150))
        img = Image.alpha_composite(img.convert("RGBA"), lay).convert("RGB")
    return img


# ---- 図解と動くスタンプ(t = 区切りの頭からの秒。None は動き終わりの状態) ----
def ease(x):
    x = min(max(x, 0.0), 1.0)
    return 1 - (1 - x) ** 3


def back(x):
    x = min(max(x, 0.0), 1.0)
    c = 1.7
    return 1 + (c + 1) * (x - 1) ** 3 + c * (x - 1) ** 2


FX_H = {"bars": lambda fx: 120 * len(fx["rows"]), "count": lambda fx: 140, "arrow": lambda fx: 200,
        "stamp": lambda fx: 250, "plays": lambda fx: 160, "bounce": lambda fx: 90,
        "survive": lambda fx: 190, "chips": lambda fx: 104 * len(fx["items"]),
        "counter": lambda fx: 190, "ledger": lambda fx: 92 * len(fx["rows"]) + 20}


def fx_length(fx):
    """動きが終わるまでの秒(bounce は 1 周期)。"""
    return {"bars": 0.3 * (len(fx.get("rows", [])) - 1) + 0.5, "count": 0.07 * fx.get("n", 0) + 0.3,
            "arrow": 0.85, "stamp": 0.3, "plays": 0.55, "bounce": 0.8,
            "survive": 0.4 + 0.25 * fx.get("n", 4),
            "counter": 0.9, "ledger": 0.35 * len(fx.get("rows", [])) + 0.3,
            "chips": max(fx.get("at", [0.3 * k for k in range(len(fx.get("items", [])))]) or [0]) + 0.3}[fx["type"]]


def paste_pop(img, sprite, cx, cy, k, alpha=1.0):
    """sprite を倍率 k で中心 (cx, cy) に貼る。"""
    if k <= 0.01:
        return
    sp = sprite.resize((max(1, int(sprite.width * k)), max(1, int(sprite.height * k))), Image.LANCZOS)
    if alpha < 1:
        a = sp.getchannel("A").point(lambda v: int(v * alpha))
        sp.putalpha(a)
    img.paste(sp, (int(cx - sp.width / 2), int(cy - sp.height / 2)), sp)


def draw_fx(img, fx, y, t):
    d = ImageDraw.Draw(img)
    T = 99.0 if t is None else t
    kind = fx["type"]
    if kind == "bars":  # 横棒グラフ。棒が伸びてから数字が出る
        vmax = max(r[1] for r in fx["rows"])
        for k, (label, value, shown, mark) in enumerate(fx["rows"]):
            yy = y + 120 * k + 55
            p = ease((T - 0.3 * k) / 0.5)
            d.text((90, yy), label, font=font(F_HEAD, 52), fill=INK, anchor="lm")
            x0, wmax = 300, 330
            w = int(wmax * value / vmax * p)
            if w > 4:
                d.rounded_rectangle((x0, yy - 38, x0 + w, yy + 38), radius=14,
                                    fill=PILL["green"] if mark == "max" else (206, 209, 197))
            if p > 0.6:
                d.text((x0 + w + 18, yy), shown, font=font(F_BIG, 50),
                       fill=TONE["green"] if mark == "max" else INK, anchor="lm")
    elif kind == "count":  # カードのアイコンが 1 枚ずつ並ぶ
        n, cw, ch, gap = fx["n"], 74, 104, 14
        x0 = (W - (n * cw + (n - 1) * gap)) / 2
        card = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
        cd = ImageDraw.Draw(card)
        cd.rounded_rectangle((0, 0, cw - 1, ch - 1), radius=8, fill=(205, 168, 82))
        cd.rounded_rectangle((8, 16, cw - 9, ch - 34), radius=4, fill=(52, 64, 88))
        cd.rectangle((8, ch - 28, cw - 9, ch - 10), fill=(235, 222, 186))
        for k in range(n):
            paste_pop(img, card, x0 + k * (cw + gap) + cw / 2, y + 70, back((T - 0.07 * k) / 0.25))
    elif kind == "arrow":  # 左の箱 → 矢印が伸びる → 右の箱が弾んで出る
        (l1, v1), (l2, v2) = fx["left"], fx["right"]
        fb, fl = font(F_BIG, 56), font(F_HEAD, 36)
        lw = d.textlength(v1, font=fb) + 60
        rw = d.textlength(v2, font=fb) + 60
        gapw = 150
        x0 = (W - (lw + gapw + rw)) / 2
        bx = (x0, y + 60, x0 + lw, y + 170)
        d.text(((bx[0] + bx[2]) / 2, y + 28), l1, font=fl, fill=SUB, anchor="mm")
        d.rounded_rectangle(bx, radius=20, fill=(255, 255, 250), outline=(190, 192, 180), width=4)
        d.text(((bx[0] + bx[2]) / 2, y + 116), v1, font=fb, fill=INK, anchor="mm")
        p = ease((T - 0.15) / 0.35)
        ax0, ax1 = bx[2] + 22, bx[2] + gapw - 22
        ax = ax0 + (ax1 - ax0) * p
        if p > 0:
            d.line((ax0, y + 115, ax, y + 115), fill=TONE["red"], width=12)
            d.polygon([(ax + 6, y + 115), (ax - 24, y + 93), (ax - 24, y + 137)], fill=TONE["red"])
        rx = bx[2] + gapw
        box = Image.new("RGBA", (int(rw), 110), (0, 0, 0, 0))
        bd = ImageDraw.Draw(box)
        bd.rounded_rectangle((0, 0, rw - 1, 109), radius=20, fill=PILL[fx.get("right_tone", "green")])
        bd.text((rw / 2, 56), v2, font=fb, fill=TONE["green"], anchor="mm")
        k = back((T - 0.5) / 0.3)
        if k > 0.01:
            d.text((rx + rw / 2, y + 28), l2, font=fl, fill=SUB, anchor="mm")
        paste_pop(img, box, rx + rw / 2, y + 115, k)
    elif kind == "stamp":  # 判子。大きい所から押し込まれる。右肩上がりに傾ける
        f = font(F_BIG, fx.get("size", 120))
        tw = int(ImageDraw.Draw(img).textlength(fx["text"], font=f))
        sp = Image.new("RGBA", (tw + 90, int(f.size * 1.6)), (0, 0, 0, 0))
        sd = ImageDraw.Draw(sp)
        col = TONE[fx.get("tone", "red")]
        sd.rounded_rectangle((6, 6, sp.width - 7, sp.height - 7), radius=26, fill=(255, 255, 250, 235), outline=col, width=12)
        sd.text((sp.width / 2, sp.height / 2 + 4), fx["text"], font=f, fill=col, anchor="mm")
        sp = sp.rotate(fx.get("angle", 7), resample=Image.BICUBIC, expand=True)
        p = ease(T / 0.2)
        paste_pop(img, sp, W / 2, y + 125, 1.9 - 0.9 * p, alpha=min(1.0, T / 0.12) if t is not None else 1.0)
    elif kind == "plays":  # 動画のアイコンが n 個
        n, tw_, th_, gap = fx["n"], 210, 128, 30
        x0 = (W - (n * tw_ + (n - 1) * gap)) / 2
        tile = Image.new("RGBA", (tw_, th_), (0, 0, 0, 0))
        td_ = ImageDraw.Draw(tile)
        td_.rounded_rectangle((0, 0, tw_ - 1, th_ - 1), radius=18, fill=(52, 58, 60))
        td_.polygon([(tw_ / 2 - 22, th_ / 2 - 28), (tw_ / 2 - 22, th_ / 2 + 28), (tw_ / 2 + 30, th_ / 2)], fill=(255, 255, 255))
        for k in range(n):
            paste_pop(img, tile, x0 + k * (tw_ + gap) + tw_ / 2, y + 75, back((T - 0.15 * k) / 0.25))
    elif kind == "survive":  # n 枚のカードが並び、残す 1 枚以外に順に×が付いて暗くなる
        n, keep, cw, ch, gap = fx.get("n", 4), fx.get("keep", 0), 120, 168, 34
        x0 = (W - (n * cw + (n - 1) * gap)) / 2
        cy = y + 95
        for k in range(n):
            card = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
            cd = ImageDraw.Draw(card)
            cd.rounded_rectangle((0, 0, cw - 1, ch - 1), radius=10, fill=(205, 168, 82))
            cd.rounded_rectangle((12, 26, cw - 13, ch - 54), radius=6, fill=(52, 64, 88))
            cd.rectangle((12, ch - 44, cw - 13, ch - 14), fill=(235, 222, 186))
            others = [j for j in range(n) if j != keep]
            if k != keep:
                q = ease((T - 0.4 - 0.25 * others.index(k)) / 0.2)
                if q > 0:
                    dim = Image.new("RGBA", (cw, ch), (239, 239, 230, int(170 * q)))
                    card = Image.alpha_composite(card, dim)
                    cd = ImageDraw.Draw(card)
                    m = 22
                    cd.line((m, m + 10, cw - m, ch - m - 10), fill=TONE["red"] + (int(255 * q),), width=12)
                    cd.line((cw - m, m + 10, m, ch - m - 10), fill=TONE["red"] + (int(255 * q),), width=12)
            elif T > 0.4 + 0.25 * (n - 1):
                ring = Image.new("RGBA", (cw + 24, ch + 24), (0, 0, 0, 0))
                ImageDraw.Draw(ring).rounded_rectangle((0, 0, cw + 23, ch + 23), radius=16, outline=TONE["green"], width=8)
                img.paste(ring, (int(x0 + k * (cw + gap) - 12), int(cy - ch / 2 - 12)), ring)
            paste_pop(img, card, x0 + k * (cw + gap) + cw / 2, cy, 1.0 if fx.get("instant") else back((T - 0.06 * k) / 0.25))
    elif kind == "chips":  # 名前の札が 1 枚ずつ出る(右に赤い札)。at は区切りの頭からの秒
        items, tag = fx["items"], fx.get("tag", "")
        ats = fx.get("at", [0.3 * k for k in range(len(items))])
        fb, ft = font(F_HEAD, 58), font(F_HEAD, 40)
        for k, name in enumerate(items):
            p = back((T - ats[k]) / 0.25)
            if p <= 0.01:
                continue
            nw = d.textlength(name, font=fb)
            tw = d.textlength(tag, font=ft) + 36 if tag else 0
            w_ = int(nw + 60 + tw + (20 if tag else 0))
            row = Image.new("RGBA", (w_, 88), (0, 0, 0, 0))
            rd = ImageDraw.Draw(row)
            rd.rounded_rectangle((0, 0, w_ - 1, 87), radius=18, fill=(255, 255, 250), outline=(200, 202, 190), width=3)
            rd.text((30, 45), name, font=fb, fill=INK, anchor="lm")
            if tag:
                rd.rounded_rectangle((w_ - tw - 14, 16, w_ - 14, 72), radius=12, fill=TONE["red"])
                rd.text((w_ - 14 - tw / 2, 45), tag, font=ft, fill=(255, 255, 255), anchor="mm")
            paste_pop(img, row, W / 2, y + 46 + 104 * k, p)
    elif kind == "counter":  # 金額が 0 から数え上がる(0.8 秒)
        p = ease(T / 0.8)
        v = round(fx["value"] * p)
        txt = f"{fx.get('prefix', '')}{v:,}{fx.get('suffix', '')}"
        f = font(F_BIG, fx.get("size", 120))
        full = f"{fx.get('prefix', '')}{fx['value']:,}{fx.get('suffix', '')}"
        tw = d.textlength(full, font=f)
        x0 = (W - tw) / 2 - 40
        d.rounded_rectangle((x0, y + 20, W - x0, y + 180), radius=26, fill=PILL[fx.get("tone", "green")])
        d.text((W / 2, y + 102), txt, font=f, fill=TONE["green"], anchor="mm")
    elif kind == "ledger":  # 収支の表。1 行ずつ出て、最後の行(合計)は線の下で強調
        rows = fx["rows"]
        fl, fv = font(F_HEAD, 50), font(F_BIG, 56)
        xl, xr = 150, W - 150
        for k, (label, value) in enumerate(rows):
            p = ease((T - 0.35 * k) / 0.3)
            if p <= 0:
                continue
            last = k == len(rows) - 1
            yy = y + 46 + 92 * k + (20 if last else 0) + (1 - p) * 30
            col = TONE["green"] if last else (TONE["red"] if value.startswith("−") else INK)
            if last:
                d.line((xl, yy - 52, xr, yy - 52), fill=INK, width=5)
                d.rounded_rectangle((xl - 20, yy - 42, xr + 20, yy + 42), radius=16, fill=PILL["green"])
            d.text((xl, yy), label, font=fl, fill=INK, anchor="lm")
            d.text((xr, yy), value, font=fv, fill=col, anchor="rm")
    elif kind == "bounce":  # 下向きの矢印が上下に揺れる(ループ)
        off = 0 if t is None else 14 * abs(math.sin(math.pi * (t % 0.8) / 0.8))
        cx, cy = W / 2, y + 30 + off
        d.polygon([(cx - 46, cy), (cx + 46, cy), (cx, cy + 46)], fill=TONE["green"])


def overlay(beat, source, t=None):
    """1 区切り分の静止レイヤー(帯の中は黒。動画は後から重ねる)。"""
    img = background(beat.get("open"))
    d = ImageDraw.Draw(img)
    d.rectangle((0, BAND[0], W, BAND[1]), fill=(0, 0, 0))
    l1, l2 = beat["head"]
    tone = TONE[beat.get("tone", "green")]
    rich(d, 215, l1, fit(d, l1, F_HEAD, 70, W - 120), INK, tone)
    rich(d, 318, l2, fit(d, l2, F_BIG, 100, W - 100), tone, tone)

    p = beat.get("panel", {})
    # パネルの中身は縦方向の中央にそろえる(先に高さを測る)
    pill_f = fit(d, p["pill"], F_BIG, p.get("pill_size", 96), W - 260) if p.get("pill") else None
    hgt = ((240 + 50) if p.get("thumb") else 0) + (95 if p.get("above") else 0) \
        + ((int(pill_f.size * 1.55) + 45) if pill_f else 0) + 92 * len(p.get("lines", [])) \
        + (90 if p.get("below") else 0) + (45 if p.get("foot") else 0) \
        + ((FX_H[p["fx"]["type"]](p["fx"]) + 30) if p.get("fx") else 0)
    y = PANEL[0] + max(30, (PANEL[1] - PANEL[0] - hgt) // 2)
    if p.get("thumb"):
        t, *box = p["thumb"]
        th = grab(source, t, box)
        th = th.resize((int(th.width * 240 / th.height), 240), Image.LANCZOS)
        sh = Image.new("RGBA", (th.width + 30, th.height + 30), (0, 0, 0, 0))
        ImageDraw.Draw(sh).rectangle((15, 19, th.width + 15, th.height + 19), fill=(0, 0, 0, 70))
        sh = sh.filter(ImageFilter.GaussianBlur(6))
        x = (W - th.width) // 2
        img.paste(sh, (x - 15, y - 15), sh)
        img.paste(th, (x, y))
        y += 240 + 50
    if p.get("above"):
        rich(d, y + 35, p["above"], font(F_HEAD, 62), INK, TONE["red"]); y += 95
    if p.get("fx") and p["fx"]["type"] != "bounce":
        draw_fx(img, p["fx"], y, t)
        d = ImageDraw.Draw(img)
        y += FX_H[p["fx"]["type"]](p["fx"]) + 30
    if pill_f:
        tw = d.textlength(p["pill"], font=pill_f)
        ph = int(pill_f.size * 1.55)
        x0 = (W - tw) / 2 - 48
        d.rounded_rectangle((x0, y, W - x0, y + ph), radius=24, fill=PILL[p.get("pill_tone", "green")])
        d.text((W / 2, y + ph / 2 + 2), p["pill"], font=pill_f, fill=TONE["green"], anchor="mm")
        y += ph + 45
    if p.get("fx") and p["fx"]["type"] == "bounce":
        draw_fx(img, p["fx"], y - 30, t)
        y += FX_H["bounce"](p["fx"]) + 30
    for k, line in enumerate(p.get("lines", [])):
        f = font(F_HEAD, 74 if k else 62)
        rich(d, y + 40, line, f, INK, TONE[p.get("tone", "red")]); y += 92
    if p.get("below"):
        rich(d, y + 35, p["below"], fit(d, p["below"], F_HEAD, 66, W - 120), INK, INK); y += 90
    if p.get("foot"):
        d.text((W / 2, y + 20), p["foot"], font=font(F_BODY, 32), fill=SUB, anchor="mm")
    return img


def vid_filter(beat_cut, src_w, src_h, speed):
    z = beat_cut.get("zoom")
    if z:
        cx, cy, k = z
        cw, ch = int(src_w / k) // 2 * 2, int(src_h / k) // 2 * 2
        x = min(max(cx - cw / 2, 0), src_w - cw); y = min(max(cy - ch / 2, 0), src_h - ch)
        crop = f"crop={cw}:{ch}:{x:.0f}:{y:.0f},"
    else:
        crop = ""
    return f"{crop}scale={W}:{VID_H}:flags=lanczos,unsharp=5:5:0.4,setpts=(PTS-STARTPTS)/{speed},fps=30"


def board(plan, source, out):
    """実際の合成と同じ画面で、各区切りの 1 コマを並べる。"""
    src_w, src_h = rs.probe(source)
    tiles = []
    for i, b in enumerate(plan["beats"]):
        img = overlay(b, source)
        c = b["cuts"][0]
        t = c.get("v", c["a"][0])
        fr = grab(source, to_sec(t) + b.get("board_dt", 0.5))
        z = c.get("zoom")
        if z:
            cx, cy, k = z
            cw, ch = src_w / k, src_h / k
            x = min(max(cx - cw / 2, 0), src_w - cw); y = min(max(cy - ch / 2, 0), src_h - ch)
            fr = fr.crop((int(x), int(y), int(x + cw), int(y + ch)))
        img.paste(fr.resize((W, VID_H), Image.LANCZOS), (0, VID_Y))
        tile = Image.new("RGB", (W // 3, H // 3 + 330), "white")
        tile.paste(img.resize((W // 3, H // 3), Image.LANCZOS), (0, 0))
        d = ImageDraw.Draw(tile)
        fb = font(F_BODY, 22)
        txt = [f"#{i + 1}  元 {c['a'][0]}〜{b['cuts'][-1]['a'][1]}", "声: " + b.get("say", ""), "狙い: " + b.get("why", "")]
        if b.get("fx_note"):
            txt.append("図解・動き: " + b["fx_note"])
        yy = H // 3 + 10
        for s in txt:
            line = ""
            for ch in s:
                if d.textlength(line + ch, font=fb) > W // 3 - 20:
                    d.text((10, yy), line, font=fb, fill=(40, 40, 40)); yy += 30; line = ch
                else:
                    line += ch
            d.text((10, yy), line, font=fb, fill=(40, 40, 40)); yy += 34
        tiles.append(tile)
    cols = 5
    rows = math.ceil(len(tiles) / cols)
    tw, th = tiles[0].size
    sheet = Image.new("RGB", (cols * (tw + 16) + 16, rows * (th + 16) + 16), (225, 225, 220))
    for k, t in enumerate(tiles):
        sheet.paste(t, (16 + (k % cols) * (tw + 16), 16 + (k // cols) * (th + 16)))
    sheet.save(out)
    print(out, sheet.size)
    # 動きのコマ送り(図解・スタンプのある区切りだけ。パネル部分を時間順に並べる)
    rows = [(i, b) for i, b in enumerate(plan["beats"]) if b.get("panel", {}).get("fx")]
    if rows:
        times = plan.get("motion_times", [0.0, 0.1, 0.2, 0.35, 0.6, None])
        cw, chh = W // 2, (PANEL[1] - PANEL[0]) // 2
        strip = Image.new("RGB", (160 + len(times) * (cw + 10), len(rows) * (chh + 10) + 60), (225, 225, 220))
        sd = ImageDraw.Draw(strip)
        for k, tt in enumerate(times):
            sd.text((160 + k * (cw + 10) + 10, 18), "完成" if tt is None else f"{tt:.2f}秒", font=font(F_HEAD, 30), fill=INK)
        for r, (i, b) in enumerate(rows):
            sd.text((14, 60 + r * (chh + 10) + chh // 2), f"#{i + 1}", font=font(F_HEAD, 40), fill=INK, anchor="lm")
            for k, tt in enumerate(times):
                im = overlay(b, source, tt).crop((0, PANEL[0], W, PANEL[1])).resize((cw, chh), Image.LANCZOS)
                strip.paste(im, (160 + k * (cw + 10), 60 + r * (chh + 10)))
        mo = out.replace(".png", "_motion.png")
        strip.save(mo)
        print(mo, strip.size)


def voice_spans(source, a0, a1):
    """カットの中の長い間だけを詰める。頭と尻は設計図の位置(語の切れ目)のまま、重なった区間はつなぐ。"""
    spans = sorted(rs.speech_spans(source, a0, a1))
    merged = []
    for x, y in spans:
        if merged and x <= merged[-1][1] + 0.02:
            merged[-1] = (merged[-1][0], max(merged[-1][1], y))
        else:
            merged.append((x, y))
    merged[0] = (a0, merged[0][1])
    merged[-1] = (merged[-1][0], a1)
    return merged


def render(plan, source, out):
    speed = plan.get("speed", 1.0)
    src_w, src_h = rs.probe(source)
    rs.JET_MIN, rs.JET_PAD = JET_MIN, JET_PAD
    with tempfile.TemporaryDirectory() as td:
        parts, audio, t, prev_last = [], [], 0.0, None
        for i, b in enumerate(plan["beats"]):
            fx = b.get("panel", {}).get("fx")
            n_anim = math.ceil(fx_length(fx) * 30) + 1 if fx else 1
            for f in range(n_anim):
                overlay(b, source, f / 30 if fx else None).save(os.path.join(td, f"bg{i:02d}_{f:04d}.png"))
            loop = bool(fx) and fx["type"] == "bounce"
            local = 0  # 区切りの頭からのコマ数
            for j, c in enumerate(b["cuts"]):
                a0, a1 = to_sec(c["a"][0]), to_sec(c["a"][1])
                spans = voice_spans(source, a0, a1) if c.get("jet", True) else [(a0, a1)]
                voice = np.concatenate([rs.source_audio(source, s0, s1) for s0, s1 in spans])
                vsegs = [(to_sec(c["v"]), to_sec(c["v"]) + len(voice) / SR)] if c.get("v") else spans
                frames = 0
                for k, (v0, v1) in enumerate(vsegs):
                    d = v1 - v0
                    n = max(1, round(d / speed * 30))
                    p = os.path.join(td, f"p{i:02d}_{j:02d}_{k:02d}.mp4")
                    slide = i > 0 and j == 0 and k == 0 and b.get("slide", True) and prev_last
                    if slide:  # 前の映像が左へ抜け、新しい映像が右から入る
                        P = f"(1-pow(1-min(t/{SLIDE},1),3))"
                        fc = (f"[1:v]{vid_filter(c, src_w, src_h, speed)},tpad=stop_mode=clone:stop_duration=1[v];"
                              f"[0:v]setpts=PTS-STARTPTS,tpad=stop_mode=clone:stop_duration=600[b];"
                              f"[2:v]setpts=PTS-STARTPTS[o];"
                              f"[b][o]overlay=x='-{W}*{P}':y={VID_Y}:eval=frame:eof_action=pass[bo];"
                              f"[bo][v]overlay=x='{W}*(1-{P})':y={VID_Y}:eval=frame,format=yuv420p")
                    else:
                        fc = (f"[1:v]{vid_filter(c, src_w, src_h, speed)},tpad=stop_mode=clone:stop_duration=1[v];"
                              f"[0:v]setpts=PTS-STARTPTS,tpad=stop_mode=clone:stop_duration=600[b];[b][v]overlay=0:{VID_Y},format=yuv420p")
                    seq = os.path.join(td, f"bg{i:02d}_%04d.png")
                    if loop:
                        bg_in = ["-loop", "1", "-framerate", "30", "-start_number", str(local % n_anim), "-i", seq]
                    elif local < n_anim - 1:
                        bg_in = ["-framerate", "30", "-start_number", str(local), "-i", seq]
                    else:
                        bg_in = ["-loop", "1", "-framerate", "30", "-i", seq % (n_anim - 1)]
                    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *bg_in,
                                    "-ss", f"{v0:.3f}", "-t", f"{d + 0.2:.3f}", "-i", source,
                                    *(["-loop", "1", "-t", f"{SLIDE + 0.1:.2f}", "-i", prev_last] if slide else []), "-an",
                                    "-filter_complex", fc, "-frames:v", str(n), "-c:v", "libx264", "-crf", "16", p],
                                   check=True)
                    parts.append(p)
                    frames += n
                    local += n
                    # 次の切り替え用に、最後のコマの帯部分を取っておく
                    prev_last = os.path.join(td, "last.png")
                    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-sseof", "-0.1", "-i", p, "-update", "1",
                                    "-vf", f"crop={W}:{VID_H}:0:{VID_Y}", prev_last], check=True)
                sfx = c.get("se") or ("whoosh" if i > 0 and j == 0 and b.get("slide", True) else None)
                audio.append((t, voice, sfx))
                t += frames / 30
        total = t
        mix = np.zeros(int((total + 0.5) * SR), np.float32)
        for at, v, name in audio:
            raw = os.path.join(td, "v.wav"); fast = os.path.join(td, "f.raw")
            se.write_wav(raw, v)
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", raw, "-af", f"atempo={speed}",
                            "-ac", "1", "-ar", str(SR), "-f", "s16le", fast], check=True)
            x = np.fromfile(fast, np.int16).astype(np.float32) / 32768
            i0 = int(at * SR); mix[i0:i0 + len(x)] += x[: len(mix) - i0]
            if name:
                s_ = se.get(name) * 0.3
                j0 = max(0, i0 - int(0.15 * SR)) if name == "whoosh" else i0  # シュッは切り替えの少し前から(声の頭に重ねない)
                mix[j0:j0 + len(s_)] += s_[: len(mix) - j0]
        mix = mix[: int(total * SR)]
        mix /= max(1.0, np.abs(mix).max() / 0.95)
        wav = os.path.join(td, "mix.wav"); se.write_wav(wav, mix)
        lst = os.path.join(td, "list.txt")
        open(lst, "w").write("".join(f"file '{p}'\n" for p in parts))
        os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst, "-i", wav,
                        "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-crf", "19", "-pix_fmt", "yuv420p",
                        "-af", "loudnorm=I=-14:TP=-1.0:LRA=11", "-c:a", "aac", "-b:a", "192k", "-shortest",
                        "-movflags", "+faststart", out], check=True)
    print(f"{out} ({total:.1f}s)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("plan")
    ap.add_argument("source")
    ap.add_argument("--out")
    ap.add_argument("--board")
    a = ap.parse_args()
    plan = json.load(open(a.plan, encoding="utf-8"))
    if a.board:
        board(plan, a.source, a.board)
    if a.out:
        render(plan, a.source, a.out)


if __name__ == "__main__":
    main()
