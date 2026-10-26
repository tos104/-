#!/usr/bin/env python3
"""写真だけで作るリール(飲食・宿向け)。無音で書き出し、曲は投稿アプリで付ける。

スタイルは PLAYBOOK.md 4.85。乱数は固定(同じ台本からは毎回同じ映像)。

台本(JSON):
{
  "assets": "../../output/tangatable/assets",    # 台本からの相対パス
  "shots": [
    {"img": "a.jpg", "dur": 2.3, "cam": "pullback|push|pan", "layout": "full|band",
     "fx": "hook|count|wipe|cards|sparkle|cta", "trans": "whip|flash|rise|fade", ... 各 fx の値,
     "note": "なぜこのカットがあるか"}
  ]
}
  python3 photo_short.py script.json --board sb.png     # 絵コンテ(各カット 3 コマ。実際の画面と同じ合成)
  python3 photo_short.py script.json --out out.mp4
"""
import argparse, math, json, os, re, subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H, FPS = 1080, 1920, 30
HERE = os.path.dirname(os.path.abspath(__file__))
F_HEAD = os.path.join(HERE, "fonts", "ShipporiMincho-ExtraBold.ttf")
F_BODY = os.path.join(HERE, "fonts", "ShipporiMincho-Medium.ttf")
F_NOTE = os.path.join(HERE, "fonts", "MPLUSRounded1c-Bold.ttf")
CREAM, INK, ACCENT, WHITE = (245, 239, 230), (42, 33, 29), (142, 42, 34), (255, 255, 255)
ROSE = (233, 161, 150)  # 写真の上の強調色(ACCENT は暗い写真に沈むため明るくした)
TRANS = 0.25   # 切り替えの長さ(秒)
BAND_H = 1000  # 横長写真の帯の高さ
BAND_Y = 700   # 帯の上端(文字は帯より上の安全域 230〜650 に置く)


def font(path, size, _cache={}):
    if (path, size) not in _cache:
        _cache[path, size] = ImageFont.truetype(path, size)
    return _cache[path, size]


def out_cubic(k):
    k = min(1.0, max(0.0, k))
    return 1 - (1 - k) ** 3


def out_back(k, s=1.7):
    k = min(1.0, max(0.0, k)) - 1
    return 1 + k * k * ((s + 1) * k + s)


def prog(t, start, dur):
    return min(1.0, max(0.0, (t - start) / dur))


# ---------- 写真とカメラ ----------

def cover(img, w, h):
    s = max(w / img.width, h / img.height)
    img = img.resize((round(img.width * s), round(img.height * s)), Image.LANCZOS)
    x, y = (img.width - w) // 2, (img.height - h) // 2
    return img.crop((x, y, x + w, y + h))


class Shot:
    """写真 1 枚分の静的な層を先に作っておき、毎コマはカメラの切り出しだけ行う。"""

    def __init__(self, path, layout, cam):
        self.im = Image.open(path).convert("RGB")
        self.layout, self.cam = layout, cam
        if layout == "band":
            self.bg = cover(self.im, W, H).filter(ImageFilter.GaussianBlur(45)).point(lambda v: int(v * 0.42))
            bw = max(round(self.im.width * BAND_H / self.im.height), W)
            self.band = self.im.resize((bw, round(self.im.height * bw / self.im.width)), Image.LANCZOS)
        else:
            self.full = cover(self.im, round(W * 1.15), round(H * 1.15))

    def frame(self, t, dur):
        k = t / dur
        if self.layout == "band":
            img = self.bg.copy()
            b = self.band
            y0 = (b.height - BAND_H) // 2
            if self.cam == "pan":   # 帯の中で左から右へ流す
                x = round((b.width - W) * (0.1 + 0.9 * out_cubic(k)))
                crop = b.crop((x, y0, x + W, y0 + BAND_H))
            else:                   # 帯の中でゆっくり寄る
                s = 1 + 0.07 * k
                cw, ch = W / s, BAND_H / s
                x0, yy = (b.width - cw) / 2, (b.height - ch) / 2
                crop = b.resize((W, BAND_H), Image.BICUBIC, box=(x0, yy, x0 + cw, yy + ch))
            img.paste(crop, (0, BAND_Y))
            return img
        f = self.full
        s = {"pullback": 1.15 - 0.15 * out_cubic(k), "push": 1.0 + 0.08 * k}.get(self.cam, 1.0)
        cw, ch = W * 1.15 / s, H * 1.15 / s
        x0, y0 = (f.width - cw) / 2, (f.height - ch) / 2
        return f.resize((W, H), Image.BICUBIC, box=(x0, y0, x0 + cw, y0 + ch))


# ---------- 文字 ----------

def segments(line):
    return [(s.strip("{}"), s.startswith("{")) for s in re.split(r"(\{[^}]*\})", line) if s]


def text_layer(lines, size, color=WHITE, hot=ROSE, path=F_HEAD, shadow=True, gap=22, maxw=W - 160):
    """複数行の文字(RGBA)。{} は強調色。影は柔らかく 1 枚だけ。maxw を超える行があれば全体を縮める。"""
    while True:
        f = font(path, size)
        widths = [sum(f.getlength(t) for t, _ in segments(ln)) for ln in lines]
        if max(widths) <= maxw or size <= 20:
            break
        size -= 2
    lw, lh = int(max(widths)) + 40, len(lines) * (size + gap) + 40 + size // 4  # 読点などの下に出る部分を切らない
    im = Image.new("RGBA", (lw, lh), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for i, ln in enumerate(lines):
        x, y = (lw - widths[i]) / 2, 20 + i * (size + gap)
        for t, h in segments(ln):
            d.text((x, y), t, font=f, fill=(hot if h else color) + (255,))
            x += f.getlength(t)
    if shadow:
        sh = Image.new("RGBA", im.size, (0, 0, 0, 0))
        sh.putalpha(im.getchannel("A").filter(ImageFilter.GaussianBlur(10)).point(lambda a: int(a * 0.75)))
        sh.alpha_composite(im)
        im = sh
    return im


def put(canvas, layer, x, y, alpha=1.0, scale=1.0):
    """RGBA を中心 (x, y) に、透明度と拡大率つきで重ねる。"""
    if alpha <= 0:
        return
    if scale != 1.0:
        layer = layer.resize((max(1, round(layer.width * scale)), max(1, round(layer.height * scale))), Image.BICUBIC)
    if alpha < 1:
        layer = layer.copy()
        layer.putalpha(layer.getchannel("A").point(lambda a: int(a * alpha)))
    canvas.alpha_composite(layer, (round(x - layer.width / 2), round(y - layer.height / 2)))


def wipe(layer, k):
    """左から右へ文字を出す(マスクリビール)。"""
    out = layer.copy()
    m = Image.new("L", out.size, 0)
    ImageDraw.Draw(m).rectangle((0, 0, round(out.width * out_cubic(k)), out.height), fill=255)
    out.putalpha(Image.composite(out.getchannel("A"), m, m))
    return out


def top_shade(canvas, h=760, strength=150):
    """文字の下だけ暗くする(上から帯状に。画面中央は暗くしない)。"""
    g = np.linspace(strength, 0, h).astype(np.uint8)
    shade = Image.new("RGBA", (W, h), (0, 0, 0, 0))
    shade.putalpha(Image.fromarray(np.repeat(g[:, None], W, 1), "L"))
    canvas.alpha_composite(shade, (0, 0))


# ---------- 演出(fx) ----------

def fx_hook(c, t, sh):
    """縦書きの 1 行目を 1 文字ずつ、2 行目は横書きで大きく。"""
    top_shade(c, 900, 120)
    x, y = 900, 250
    for i, ch in enumerate(sh["vertical"]):
        k = prog(t, 0.05 + i * 0.07, 0.25)
        if k <= 0:
            break
        dx, dy = (52, -58) if ch in "、。" else (0, 0)  # 縦書きの句読点は右上へ(横書き用の字形は左下にあるため)
        put(c, text_layer([ch], 86, gap=0), x + dx, y + i * 96 + dy + 18 * (1 - out_cubic(k)), alpha=out_cubic(k))
    k = prog(t, 0.65, 0.35)
    lay = text_layer([sh["horizontal"]], 104, color=CREAM, hot=CREAM)
    put(c, lay, 540, 1010, alpha=out_cubic(k), scale=1.12 - 0.12 * out_back(k))
    k2 = prog(t, 0.85, 0.4)  # 下線を引く
    if k2 > 0:
        x0 = 540 - lay.width / 2 + 30
        ImageDraw.Draw(c).line((x0, 1085, x0 + (lay.width - 60) * out_cubic(k2), 1085), fill=CREAM + (230,), width=4)


def fx_count(c, t, sh):
    """人数を数え上げる。2 つの数字の間に縦線を引く。"""
    top_shade(c, 720, 140)
    for i, (label, n, unit) in enumerate(sh["nums"]):
        cx = 300 + i * 480
        v = round(n * out_cubic(prog(t, 0.1 + i * 0.15, 0.9)))
        put(c, text_layer([label], 52, path=F_BODY), cx, 300, alpha=out_cubic(prog(t, i * 0.15, 0.25)))
        num = text_layer([f"{v}"], 190, color=CREAM)
        put(c, num, cx - 30, 470, alpha=out_cubic(prog(t, 0.1 + i * 0.15, 0.2)))
        put(c, text_layer([unit], 64, color=CREAM), cx + num.width / 2 - 10, 520,
            alpha=out_cubic(prog(t, 0.8 + i * 0.15, 0.2)))
    k = prog(t, 0.2, 0.5)
    if k > 0:
        ImageDraw.Draw(c).line((540, 300, 540, 300 + 260 * out_cubic(k)), fill=CREAM + (200,), width=3)


def fx_wipe(c, t, sh):
    """行ごとに左から右へ出す。"""
    top_shade(c, 720, 140)
    for i, ln in enumerate(sh["text"]):
        k = prog(t, 0.1 + i * 0.25, 0.4)
        if k > 0:
            put(c, wipe(text_layer([ln], 92, color=CREAM), k), 540, 330 + i * 130)


def polaroid(img, caption, size=440):
    card = Image.new("RGBA", (size + 44, size + 120), (252, 250, 246, 255))
    card.paste(cover(img, size, size), (22, 22))
    f = font(F_BODY, 38)
    ImageDraw.Draw(card).text(((card.width - f.getlength(caption)) / 2, size + 40), caption, font=f, fill=INK)
    return card


def fx_cards(c, t, sh, cache={}):
    """紙の上に、料理のカードを 1 枚ずつ落とす。値段は判子のように押す。"""
    key = id(sh)
    if key not in cache:
        rng = np.random.default_rng(7)
        paper = np.clip(np.array(CREAM, np.float32) + rng.normal(0, 4, (H, W, 1)), 0, 255).astype(np.uint8)
        cards = []
        for (img, cap), rot in zip(sh["cards"], (-6, 5, -2)):
            p = polaroid(Image.open(os.path.join(sh["_root"], img)).convert("RGB"), cap)
            s = Image.new("RGBA", (p.width + 80, p.height + 80), (0, 0, 0, 0))
            s.paste((0, 0, 0, 90), (40, 52, 40 + p.width, 52 + p.height))
            s = s.filter(ImageFilter.GaussianBlur(16))
            s.alpha_composite(p, (40, 40))
            cards.append(s.rotate(rot, Image.BICUBIC, expand=True))
        cache[key] = (Image.fromarray(paper).convert("RGBA"), cards)
    paper, cards = cache[key]
    c.alpha_composite(paper)
    for i, (card, (x, y)) in enumerate(zip(cards, ((290, 930), (790, 1190), (390, 1470)))):
        k = prog(t, 0.45 + i * 0.75, 0.35)
        if k > 0:
            put(c, card, x, y - 60 * (1 - out_cubic(k)), alpha=min(1, k * 2), scale=1.25 - 0.25 * out_back(k))
    put(c, text_layer(["税込"], 50, color=INK, path=F_BODY, shadow=False), 540, 270, alpha=out_cubic(prog(t, 0, 0.25)))
    k = prog(t, 0.08, 0.3)
    put(c, text_layer([sh["price"]], 170, color=ACCENT, shadow=False), 540, 400, alpha=min(1, k * 2.5),
        scale=1.5 - 0.5 * out_back(k, 1.2))
    put(c, wipe(text_layer([sh["sub"]], 70, color=INK, hot=ACCENT, shadow=False), prog(t, 0.35, 0.45)), 540, 560)


def fx_sparkle(c, t, sh):
    """乾杯の上で光が瞬く。文字は 1 行ずつ下から。"""
    top_shade(c, 720, sh.get("shade", 150))
    rng = np.random.default_rng(3)
    d = ImageDraw.Draw(c)
    for _ in range(16):
        x, y = rng.uniform(200, 900), rng.uniform(820, 1400)
        ph, r = rng.uniform(0, 2 * math.pi), rng.uniform(14, 30)
        a = max(0.0, math.sin(t * 5 + ph)) * prog(t, 0.2, 0.3)
        if a > 0.05:
            rr, q = r * (0.6 + 0.4 * a), r * 0.18
            d.polygon([(x, y - rr), (x + q, y - q), (x + rr, y), (x + q, y + q),
                       (x, y + rr), (x - q, y + q), (x - rr, y), (x - q, y - q)], fill=(255, 248, 225, int(230 * a)))
    for i, ln in enumerate(sh["text"]):
        k = prog(t, 0.1 + i * 0.3, 0.4)
        put(c, text_layer([ln], 92, color=CREAM), 540, 340 + i * 130 + 30 * (1 - out_cubic(k)), alpha=out_cubic(k))


def fx_cta(c, t, sh):
    """締切を出し、予約のハイライトの丸を描いて終える。"""
    top_shade(c, 720, 160)
    size = 88
    while font(F_HEAD, size).getlength(re.sub(r"[{}]", "", sh["text"][0])) > W - 200:  # 安全域に収める
        size -= 4
    put(c, text_layer([sh["text"][0]], size, color=CREAM), 540, 300, alpha=out_cubic(prog(t, 0.05, 0.35)))
    k = prog(t, 0.45, 0.6)
    cx, cy, r = 220, 520, 78
    if k > 0:
        d = ImageDraw.Draw(c)
        d.arc((cx - r, cy - r, cx + r, cy + r), -90, -90 + 360 * out_cubic(k), fill=ACCENT + (255,), width=10)
        d.ellipse((cx - r + 14, cy - r + 14, cx + r - 14, cy + r - 14), fill=CREAM + (int(255 * out_cubic(k)),))
        put(c, text_layer([sh["ring"]], 44, color=INK, shadow=False), cx, cy, alpha=out_cubic(prog(t, 0.8, 0.3)))
    lay = text_layer([sh["text"][1]], 64, color=CREAM, path=F_BODY, maxw=W - 80 - (cx + r + 20))
    put(c, lay, cx + r + 10 + lay.width / 2, 520, alpha=out_cubic(prog(t, 0.9, 0.35)))  # 丸の右から並べる


def paper(_cache=[]):
    """クリームの紙(粒は固定の乱数)。"""
    if not _cache:
        rng = np.random.default_rng(7)
        a = np.clip(np.array(CREAM, np.float32) + rng.normal(0, 4, (H, W, 1)), 0, 255).astype(np.uint8)
        _cache.append(Image.fromarray(a).convert("RGBA"))
    return _cache[0]


def fx_lines(c, t, sh):
    """行ごとに下から。sparkle の光なし版。instant なら 1 行目は 0 フレーム目から出す(冒頭用)。"""
    top_shade(c, sh.get("shade_h", 720), sh.get("shade", 150))
    for i, ln in enumerate(sh["text"]):
        k = 1.0 if (i == 0 and sh.get("instant")) else prog(t, 0.1 + i * 0.3, 0.4)
        put(c, text_layer([ln], sh.get("size", 92), color=CREAM), 540, 340 + i * 130 + 30 * (1 - out_cubic(k)),
            alpha=out_cubic(k))


def fx_check(c, t, sh):
    """幹事のチェック項目。枠を出してからレ点を書く。"""
    dark = Image.new("RGBA", (W, H), (20, 14, 12, 0))
    dark.putalpha(int(170 * out_cubic(prog(t, 0, 0.3))))
    c.alpha_composite(dark)
    put(c, text_layer([sh["title"]], 76, color=CREAM), 540, 300, alpha=out_cubic(prog(t, 0, 0.3)))
    d = ImageDraw.Draw(c)
    for i, (label, value) in enumerate(sh["items"]):
        y, t0 = 470 + i * 230, 0.35 + i * sh.get("step", 0.55)
        k = prog(t, t0, 0.25)
        if k <= 0:
            continue
        a = int(255 * out_cubic(k))
        d.rounded_rectangle((110, y, 170, y + 60), 8, outline=CREAM + (a,), width=4)
        kc = prog(t, t0 + 0.15, 0.25)  # レ点は 2 画で書く
        if kc > 0:
            p1, p2, p3 = (122, y + 30), (138, y + 48), (178, y - 2)
            m = min(1, kc * 2)
            d.line((p1, (p1[0] + (p2[0] - p1[0]) * m, p1[1] + (p2[1] - p1[1]) * m)), fill=ROSE + (255,), width=9)
            if kc > 0.5:
                m = (kc - 0.5) * 2
                d.line((p2, (p2[0] + (p3[0] - p2[0]) * m, p2[1] + (p3[1] - p2[1]) * m)), fill=ROSE + (255,), width=9)
        lab = text_layer([label], 52, color=CREAM, path=F_BODY, shadow=False)
        c.alpha_composite(lab, (200, y - 12)) if k >= 1 else put(c, lab, 200 + lab.width / 2, y + lab.height / 2 - 12, alpha=k)
        val = text_layer([value], 64, color=CREAM, shadow=False)
        put(c, wipe(val, prog(t, t0 + 0.2, 0.35)), 200 + val.width / 2, y + 125)


def fx_ladder(c, t, sh):
    """3 つのコースを、品数の棒で比べる(紙の上)。"""
    c.alpha_composite(paper())
    put(c, text_layer([sh["title"]], 80, color=INK, shadow=False), 540, 300, alpha=out_cubic(prog(t, 0, 0.3)))
    d = ImageDraw.Draw(c)
    base, unit = 1460, 100
    for i, (price, n) in enumerate(sh["courses"]):
        x, t0 = 220 + i * 320, 0.3 + i * 0.35
        k = out_back(prog(t, t0, 0.45), 1.2)
        top = base - n * unit * k
        if k > 0:
            col = ACCENT if i == len(sh["courses"]) - 1 else (120, 92, 80)
            d.rectangle((x - 105, top, x + 105, base), fill=col + (255,))
            put(c, text_layer([f"{n}品"], 56, color=CREAM, shadow=False), x, top + 50, alpha=prog(t, t0 + 0.3, 0.2))
            put(c, text_layer([price], 58, color=INK, shadow=False), x, top - 50, alpha=prog(t, t0 + 0.2, 0.2))
    d.line((90, base, 990, base), fill=INK + (255,), width=3)
    put(c, wipe(text_layer([sh["foot"]], 60, color=INK, hot=ACCENT, shadow=False), prog(t, 1.4, 0.4)), 540, 1530)


def fx_bignum(c, t, sh):
    """数字 1 つだけを左寄せで大きく。下から切り出すように出す。"""
    dark = Image.new("RGBA", (W, H), (15, 10, 8, 150))
    c.alpha_composite(dark)
    lab = text_layer([sh["label"]], 60, color=CREAM, path=F_BODY)
    put(c, lab, 110 + lab.width / 2, 520, alpha=out_cubic(prog(t, 0, 0.25)))
    num = text_layer([sh["num"]], sh.get("size", 330), color=CREAM, hot=ROSE)
    k = prog(t, 0.1, 0.35)
    m = Image.new("L", num.size, 0)  # 下から上へマスクを開ける
    ImageDraw.Draw(m).rectangle((0, round(num.height * (1 - out_cubic(k))), num.width, num.height), fill=255)
    lay = num.copy()
    lay.putalpha(Image.composite(num.getchannel("A"), m, m))
    c.alpha_composite(lay, (90, 560 + round(40 * (1 - out_cubic(k)))))
    unit = text_layer([sh["unit"]], 88, color=CREAM)
    put(c, unit, 90 + num.width - 10 + unit.width / 2, 560 + num.height - 110,
        alpha=out_cubic(prog(t, 0.4, 0.25)))
    if sh.get("sub"):
        put(c, wipe(text_layer([sh["sub"]], 64, color=CREAM), prog(t, 0.55, 0.4)), 540, 560 + num.height + 90)


def fx_reveal(c, t, sh, cache={}):
    """無人の会場から、満席の会場へ。縦の線が左から右へ動いて入れ替える。"""
    if id(sh) not in cache:
        cache[id(sh)] = Shot(os.path.join(sh["_root"], sh["img2"]), sh.get("layout2", "full"), "push")
    k = out_cubic(prog(t, sh.get("at", 0.9), 0.9))
    if k > 0:
        x = round(W * k)
        after = cache[id(sh)].frame(t, sh["dur"]).convert("RGBA")
        c.alpha_composite(after.crop((0, 0, x, H)), (0, 0))
        if k < 1:
            ImageDraw.Draw(c).line((x, 0, x, H), fill=CREAM + (255,), width=6)
    top_shade(c, 720, 150)
    for i, ln in enumerate(sh["text"]):
        kk = prog(t, sh["text_at"][i], 0.4)
        put(c, text_layer([ln], 88, color=CREAM), 540, 330 + i * 130 + 24 * (1 - out_cubic(kk)), alpha=out_cubic(kk))


def bubble(text, fill, ink, tail_right):
    f = font(F_HEAD, 64)
    w, h = round(f.getlength(text)) + 90, 130
    im = Image.new("RGBA", (w, h + 30), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, w - 1, h), 50, fill=fill + (245,))
    tx = w - 70 if tail_right else 50
    d.polygon([(tx, h - 5), (tx + 20, h - 5), (tx + (30 if tail_right else -10), h + 28)], fill=fill + (245,))
    d.text((45, 28), text, font=f, fill=ink)
    return im


def fx_qa(c, t, sh):
    """幹事の質問(左)と店の答え(右)を、吹き出しで弾ませて出す。"""
    top_shade(c, 1000, 170)
    q = bubble(sh["q"], CREAM, INK, False)
    a = bubble(sh["a"], ACCENT, CREAM, True)
    kq, ka = prog(t, 0.1, 0.35), prog(t, 0.75, 0.35)
    if kq > 0:
        put(c, q, 80 + q.width / 2, 330, alpha=min(1, kq * 3), scale=0.6 + 0.4 * out_back(kq))
    if ka > 0:
        put(c, a, W - 80 - a.width / 2, 520, alpha=min(1, ka * 3), scale=0.6 + 0.4 * out_back(ka))
    if sh.get("sub"):
        sub = text_layer([sh["sub"]], 52, color=CREAM, path=F_BODY)
        put(c, sub, W - 80 - sub.width / 2, 660, alpha=out_cubic(prog(t, 1.1, 0.3)))



def dim(c, a):
    """画面全体を暗くする(文字を読ませるカット用)。"""
    c.alpha_composite(Image.new("RGBA", (W, H), (15, 10, 8, int(a))))


def fx_slot(c, t, sh):
    """値段の数字をスロットのように回して止める。桁ごとに少しずつ遅れて止まる。"""
    dim(c, 120 * out_cubic(prog(t, 0, 0.3)))
    put(c, text_layer(sh["text"], 76, color=CREAM), 540, 360, alpha=out_cubic(prog(t, 0, 0.3)))
    size, f = 250, font(F_HEAD, 250)
    chars = list(sh["num"])
    widths = [f.getlength(ch) for ch in chars]
    x = 540 - sum(widths) / 2 - 60
    y, h = 760, round(size * 1.3)
    for i, ch in enumerate(chars):
        col = Image.new("RGBA", (round(widths[i]) + 10, h), (0, 0, 0, 0))
        d = ImageDraw.Draw(col)
        if ch.isdigit():
            k = out_cubic(prog(t, 0.25, 0.7 + 0.18 * i))
            p_ = int(ch) + 20 * (1 - k)          # 回っている位置(小数)
            d0, frac = int(p_) % 10, p_ - int(p_)
            d.text((5, -frac * h + 10), str(d0), font=f, fill=CREAM)
            d.text((5, (1 - frac) * h + 10), str((d0 + 1) % 10), font=f, fill=CREAM)
            a = 1.0
        else:
            d.text((5, 10), ch, font=f, fill=CREAM)
            a = out_cubic(prog(t, 0.25, 0.3))
        put(c, col, x + widths[i] / 2, y, alpha=a)
        x += widths[i]
    k = prog(t, 1.5, 0.3)
    put(c, text_layer([sh["unit"]], 96, color=ROSE), x + 110, y + 40, alpha=out_cubic(k), scale=1.4 - 0.4 * out_back(k))
    put(c, wipe(text_layer([sh["sub"]], 64, color=CREAM), prog(t, 1.7, 0.4)), 540, y + 230)


def token(text, size, fill, ink, pad=36):
    f = font(F_HEAD, size)
    w = round(f.getlength(text)) + pad * 2
    im = Image.new("RGBA", (w, size + pad * 2), (0, 0, 0, 0))
    ImageDraw.Draw(im).rounded_rectangle((0, 0, w - 1, size + pad * 2 - 1), 24, fill=fill + (255,))
    ImageDraw.Draw(im).text((pad, pad - size * 0.08), text, font=f, fill=ink)
    return im


def fx_equation(c, t, sh):
    """式を組み立てる: 料理 ＋ 飲み放題 ＝ 値段。項目は左右から飛び込んで止まる。"""
    c.alpha_composite(paper())
    put(c, text_layer([sh["title"]], 70, color=INK, shadow=False), 540, 300, alpha=out_cubic(prog(t, 0, 0.3)))
    rows = [(token(sh["a"], 104, (255, 255, 255), INK), 540, -1, 0.2),
            (text_layer(["＋"], 100, color=INK, shadow=False), 720, 0, 0.55),
            (token(sh["b"], 104, (255, 255, 255), INK), 900, 1, 0.7),
            (text_layer(["＝"], 100, color=INK, shadow=False), 1080, 0, 1.05),
            (token(sh["c"], 160, ACCENT, CREAM, 48), 1300, 0, 1.25)]
    for lay, y, side, t0 in rows:
        k = prog(t, t0, 0.35)
        if k <= 0:
            continue
        if side:
            put(c, lay, 540 + side * 700 * (1 - out_back(k, 1.2)), y)
        else:
            put(c, lay, 540, y, alpha=min(1, k * 2), scale=1.6 - 0.6 * out_back(k, 1.4))
    put(c, text_layer([sh["foot"]], 50, color=INK, path=F_BODY, shadow=False), 540, 1490,
        alpha=out_cubic(prog(t, 1.6, 0.3)))


def fx_dish(c, t, sh):
    """料理の名前札を左から差し込む。下に小さくコース名。"""
    tag = token(sh["name"], 70, CREAM, INK, 34)
    k = prog(t, 0.1, 0.35)
    c.alpha_composite(tag, (round(-tag.width + (tag.width + 80) * out_cubic(k)), 300))
    if sh.get("sub"):  # 明るい料理の上でも読めるよう、暗い札にのせる
        sub = token(sh["sub"], 46, (35, 26, 22), CREAM, 22)
        put(c, sub, 80 + sub.width / 2, 300 + tag.height + 50, alpha=out_cubic(prog(t, 0.4, 0.3)))


def person(size, col):
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    r = size * 0.2
    d.ellipse((size / 2 - r, size * 0.06, size / 2 + r, size * 0.06 + 2 * r), fill=col)
    d.rounded_rectangle((size * 0.18, size * 0.5, size * 0.82, size * 0.98), round(size * 0.25), fill=col)
    return im


def fx_grid(c, t, sh):
    """人の形を 1 つずつ並べて人数を埋める。先に着席の数、続けて立食の数まで。"""
    dim(c, 150)
    total, first = sh["nums"][1][1], sh["nums"][0][1]
    cols, pitch = 10, 88
    x0, y0 = 540 - cols * pitch / 2 + pitch / 2, 520
    shown = round(total * out_cubic(prog(t, 0.2, 1.6)) ** 1.1)
    for i in range(shown):
        col = ROSE + (255,) if i >= first else CREAM + (255,)
        c.alpha_composite(person(70, col), (round(x0 + (i % cols) * pitch - 35), round(y0 + (i // cols) * 96 - 35)))
    lab = f"{sh['nums'][0][0]}{shown}名" if shown <= first else f"{sh['nums'][1][0]}{shown}名"
    put(c, text_layer([lab], 96, color=CREAM if shown <= first else ROSE), 540, 330)
    if shown >= total:
        put(c, text_layer([sh["sub"]], 56, color=CREAM, path=F_BODY), 540, 1330, alpha=out_cubic(prog(t, 1.9, 0.3)))


def fx_typer(c, t, sh):
    """1 文字ずつ打つ。打っている行の末尾に縦棒(カーソル)。"""
    top_shade(c, 760, 160)
    n = int(max(0.0, t - 0.1) / sh.get("cps", 0.06))
    for i, ln in enumerate(sh["text"]):
        plain = re.sub(r"[{}]", "", ln)
        shown, n = plain[:max(0, n)], n - len(plain)
        if not shown:
            break
        lay = text_layer([shown], 90, color=CREAM)
        c.alpha_composite(lay, (90 - 20, 280 + i * 130 - 20))
        if 0 > n > -len(plain) - 1 or (n <= 0 and len(shown) == len(plain)):
            if int(t * 4) % 2 == 0:
                x = 90 + font(F_HEAD, 90).getlength(shown) + 8
                ImageDraw.Draw(c).rectangle((x, 290 + i * 130, x + 6, 380 + i * 130), fill=ROSE + (255,))


def fx_split(c, t, sh, cache={}):
    """画面を上下に分け、2 枚目の写真が下から滑り込む。"""
    if id(sh) not in cache:
        cache[id(sh)] = cover(Image.open(os.path.join(sh["_root"], sh["img2"])).convert("RGB"), W, H // 2)
    k = out_cubic(prog(t, 0.3, 0.45))
    if k > 0:
        c.paste(cache[id(sh)], (0, round(H // 2 + H // 2 * (1 - k))))
        ImageDraw.Draw(c).line((0, H // 2, W, H // 2), fill=CREAM + (255,), width=6)
    top_shade(c, 700, 150)
    for i, ln in enumerate(sh["text"]):
        put(c, wipe(text_layer([ln], 84, color=CREAM), prog(t, 0.6 + i * 0.3, 0.4)), 540, 320 + i * 125)


def fx_vcap(c, t, sh):
    """最初は文字なしで写真だけ。途中から右側に縦書きで料理名、左下に小さくコース。"""
    k0 = sh.get("text_at", 1.0)
    a = out_cubic(prog(t, k0 - 0.2, 0.4))
    if a > 0:  # 縦書きの列と下の小さい文字の下だけ暗くする
        g = np.linspace(0, 150 * a, 340).astype(np.uint8)
        side = Image.new("RGBA", (340, H), (0, 0, 0, 0))
        side.putalpha(Image.fromarray(np.repeat(g[None, :], H, 0), "L"))
        c.alpha_composite(side, (W - 340, 0))
        g = np.linspace(0, 150 * a, 400).astype(np.uint8)
        low = Image.new("RGBA", (W, 400), (0, 0, 0, 0))
        low.putalpha(Image.fromarray(np.repeat(g[:, None], W, 1), "L"))
        c.alpha_composite(low, (0, 1100))
    for i, ch in enumerate(sh["name"]):
        k = prog(t, k0 + i * 0.06, 0.3)
        if k <= 0:
            break
        put(c, text_layer([ch], 80, gap=0), 940, 300 + i * 92 + 14 * (1 - out_cubic(k)), alpha=out_cubic(k))
    if sh.get("sub"):
        sub = text_layer([sh["sub"]], 62, color=CREAM, path=F_BODY)
        put(c, sub, 90 + sub.width / 2, 1380,
            alpha=out_cubic(prog(t, k0 + 0.5, 0.4)))


def fx_timeline(c, t, sh):
    """予約から当日までの 3 段。線が伸びて、今の段だけ明るく。"""
    dim(c, 160)
    steps, upto = sh["steps"], sh["upto"]
    put(c, text_layer([sh["title"]], 76, color=CREAM), 540, 300)
    x, y0, gap = 170, 520, 300
    d = ImageDraw.Draw(c)
    for i in range(upto):
        anim = i == upto - 1
        k = prog(t, 0.1, 0.45) if anim else 1.0
        if i:
            d.line((x, y0 + (i - 1) * gap + 40, x, y0 + (i - 1) * gap + 40 + (gap - 80) * out_cubic(k)),
                   fill=CREAM + (220,), width=5)
        kd = prog(t, 0.45, 0.25) if anim else 1.0
        if kd > 0:
            r = 34 * out_back(kd)
            cy = y0 + i * gap
            d.ellipse((x - r, cy - r, x + r, cy + r), fill=(ROSE if anim else CREAM) + (255,))
            put(c, text_layer([str(i + 1)], 40, color=INK, shadow=False), x, cy, alpha=kd)
            lay = text_layer([steps[i][0]], 72 if anim else 60, color=ROSE if anim else CREAM)
            put(c, lay, x + 70 + lay.width / 2, cy - 10, alpha=kd)
            if steps[i][1]:
                sub = text_layer([steps[i][1]], 46, color=CREAM, path=F_BODY)
                put(c, sub, x + 70 + sub.width / 2, cy + 70, alpha=out_cubic(prog(t, 0.7, 0.3)) if anim else 1)


def fx_stamp(c, t, sh):
    """「予約受付中」の判子を押して終える。"""
    dim(c, 130)
    k = prog(t, 0.15, 0.35)
    if k > 0:
        st = Image.new("RGBA", (520, 520), (0, 0, 0, 0))
        d = ImageDraw.Draw(st)
        d.ellipse((10, 10, 510, 510), outline=ROSE + (255,), width=16)
        d.ellipse((40, 40, 480, 480), outline=ROSE + (255,), width=5)
        f = font(F_HEAD, 92)
        for j, ln in enumerate(sh["stamp"]):
            d.text((260 - f.getlength(ln) / 2, 160 + j * 110), ln, font=f, fill=ROSE)
        st = st.rotate(-12, Image.BICUBIC)
        put(c, st, 540, 640, alpha=min(1, k * 3), scale=1.7 - 0.7 * out_back(k, 1.0))
    a = out_cubic(prog(t, 0.6, 0.3))
    if a > 0:  # 文字の下に暗い板(写真がにぎやかでも読めるように)
        top, bot = 950, 1010 + (len(sh["text"]) - 1) * 110 + 70
        board = Image.new("RGBA", (W - 120, bot - top), (0, 0, 0, 0))
        ImageDraw.Draw(board).rounded_rectangle((0, 0, W - 121, bot - top - 1), 28, fill=(20, 14, 12, int(190 * a)))
        c.alpha_composite(board, (60, top))
    for i, ln in enumerate(sh["text"]):
        put(c, text_layer([ln], 70 - i * 6, color=CREAM, path=F_HEAD if i == 0 else F_BODY), 540, 1010 + i * 110,
            alpha=out_cubic(prog(t, 0.7 + i * 0.3, 0.3)))


def fx_frame(c, t, sh):
    """細い枠を一筆で描き、枠の中に締めの言葉。"""
    dim(c, 140)
    k = out_cubic(prog(t, 0.1, 1.0))
    m, d = 70, ImageDraw.Draw(c)
    pts = [(m, m + 150), (W - m, m + 150), (W - m, H - m - 250), (m, H - m - 250), (m, m + 150)]
    per = sum(math.dist(a, b) for a, b in zip(pts, pts[1:]))
    left = per * k
    for a, b in zip(pts, pts[1:]):
        seg = math.dist(a, b)
        if left <= 0:
            break
        r = min(1, left / seg)
        d.line((a, (a[0] + (b[0] - a[0]) * r, a[1] + (b[1] - a[1]) * r)), fill=CREAM + (230,), width=3)
        left -= seg
    for i, ln in enumerate(sh["text"]):
        put(c, text_layer([ln], 84 if i == 0 else 60, color=ROSE if i == 2 else CREAM, path=F_HEAD if i != 1 else F_BODY),
            540, 700 + i * 140, alpha=out_cubic(prog(t, 0.6 + i * 0.35, 0.4)))


def fx_button(c, t, sh):
    """予約ボタンを出して、1 回押す(縮んで戻る)。"""
    dim(c, 130)
    put(c, text_layer([sh["text"][0]], 80, color=CREAM), 540, 420, alpha=out_cubic(prog(t, 0.05, 0.3)))
    b = token(sh["button"], 76, ROSE, INK, 44)
    k = prog(t, 0.4, 0.35)
    press = 1 - 0.08 * math.sin(math.pi * prog(t, 1.2, 0.25))
    put(c, b, 540, 700, alpha=min(1, k * 2), scale=(0.7 + 0.3 * out_back(k)) * press)
    put(c, text_layer([sh["text"][1]], 56, color=CREAM, path=F_BODY), 540, 880, alpha=out_cubic(prog(t, 1.4, 0.3)))


def leak(c, t, dur):
    """暖色の光が左上から右下へゆっくり流れる。"""
    k = t / dur
    cx, cy = -200 + 1400 * k, 200 + 900 * k
    g = np.zeros((H // 8, W // 8), np.float32)
    yy, xx = np.mgrid[0:H // 8, 0:W // 8]
    g = np.exp(-(((xx * 8 - cx) / 520) ** 2 + ((yy * 8 - cy) / 700) ** 2))
    a = Image.fromarray((g * 110).astype(np.uint8), "L").resize((W, H), Image.BILINEAR)
    lay = Image.new("RGBA", (W, H), (255, 170, 90, 0))
    lay.putalpha(a)
    c.alpha_composite(lay)


def grain(c, seed):
    rng = np.random.default_rng(seed)
    n = rng.normal(0, 7, (H // 2, W // 2)).astype(np.int16)
    a = Image.fromarray(np.clip(n + 128, 0, 255).astype(np.uint8), "L").resize((W, H))
    c.alpha_composite(Image.merge("RGBA", (a, a, a, Image.new("L", (W, H), 22))))



def fx_menu(c, t, sh):
    """コースの一覧表(紙の上)。行が 1 本ずつ左から入り、最後に注記。"""
    c.alpha_composite(paper())
    put(c, text_layer([sh["title"]], 70, color=INK, shadow=False), 540, 440, alpha=out_cubic(prog(t, 0, 0.3)))
    d = ImageDraw.Draw(c)
    for i, (price, body) in enumerate(sh["rows"]):
        y, k = 640 + i * 200, out_cubic(prog(t, 0.25 + i * 0.3, 0.35))
        if k <= 0:
            continue
        dx = round(-120 * (1 - k))
        d.line((110, y + 95, 970, y + 95), fill=INK + (int(80 * k),), width=2)
        p = text_layer([price], 96, color=ACCENT, shadow=False)
        b = text_layer([body], 64, color=INK, shadow=False)
        put(c, p, 110 + dx + p.width / 2 - 20, y + 20, alpha=k)
        put(c, b, 970 + dx - b.width / 2 + 20, y + 30, alpha=k)
    put(c, wipe(text_layer([sh["foot"]], 56, color=INK, hot=ACCENT, path=F_BODY, shadow=False), prog(t, 1.3, 0.4)),
        540, 640 + len(sh["rows"]) * 200 + 20)


FX = {"hook": fx_hook, "count": fx_count, "wipe": fx_wipe, "cards": fx_cards, "sparkle": fx_sparkle, "cta": fx_cta,
      "lines": fx_lines, "check": fx_check, "ladder": fx_ladder, "bignum": fx_bignum, "reveal": fx_reveal, "qa": fx_qa,
      "slot": fx_slot, "equation": fx_equation, "dish": fx_dish, "grid": fx_grid, "typer": fx_typer, "split": fx_split,
      "vcap": fx_vcap, "timeline": fx_timeline, "stamp": fx_stamp, "frame": fx_frame, "button": fx_button, "menu": fx_menu}


# ---------- 切り替え ----------

def transition(kind, prev, cur, k):
    if prev is None or k >= 1:
        return cur
    e = out_cubic(k)
    if kind == "whip":     # 横に流れる(流れている間だけぼかす)
        blur = 30 * (1 - abs(2 * k - 1))
        img = Image.new("RGB", (W, H))
        img.paste(prev, (round(-W * e), 0))
        img.paste(cur, (round(W * (1 - e)), 0))
        return img.filter(ImageFilter.BoxBlur(blur)) if blur > 1 else img
    if kind == "flash":    # 白く飛ばしてから戻す
        return Image.blend(cur, Image.new("RGB", (W, H), WHITE), 0.85 * (1 - e))
    if kind == "rise":     # 次の画面が下からせり上がる
        img = prev.copy()
        img.paste(cur, (0, round(H * (1 - e))))
        return img
    if kind == "slide":    # 横に押し出す(ぼかさない)
        img = Image.new("RGB", (W, H))
        img.paste(prev, (round(-W * e), 0))
        img.paste(cur, (round(W * (1 - e)), 0))
        return img
    if kind == "punch":    # 次の画面を大きく見せてから戻す
        s_ = 1.18 - 0.18 * e
        cw, ch = W / s_, H / s_
        return cur.resize((W, H), Image.BICUBIC, box=((W - cw) / 2, (H - ch) / 2, (W + cw) / 2, (H + ch) / 2))
    if kind == "dip":      # いったん暗くしてから次へ
        return Image.blend(prev, Image.new("RGB", (W, H)), min(1, k * 2)) if k < 0.5 else \
            Image.blend(Image.new("RGB", (W, H)), cur, (k - 0.5) * 2)
    return Image.blend(prev, cur, e)  # fade


# ---------- 書き出し ----------

def render(sc, root, times=None):
    """全コマを (カット番号, 秒, 画像) で返す。times を渡すと、その時刻のコマだけ(絵コンテ用)。"""
    total, prev_last = 0.0, None
    for idx, sh in enumerate(sc["shots"]):
        sh = dict(sh, _root=root)
        shot = Shot(os.path.join(root, sh["img"]), sh.get("layout", "full"), sh.get("cam", "push"))
        n = round(sh["dur"] * FPS)

        def draw(i):
            t = i / FPS
            c = shot.frame(t, sh["dur"]).convert("RGBA")
            FX[sh["fx"]](c, t, sh)
            if sh.get("leak"):
                leak(c, t, sh["dur"])
            if sh.get("grain"):
                grain(c, idx * 1000 + i)
            img = c.convert("RGB")
            if sh.get("trans") and t < TRANS:
                img = transition(sh["trans"], prev_last, img, t / TRANS)
            return img

        frames = range(n) if times is None else sorted({min(n - 1, round(x * FPS)) for x in times[idx]})
        for i in frames:
            yield idx, total + i / FPS, draw(i)
        prev_last = draw(n - 1)
        total += n / FPS


def board(sc, root, out):
    """各カット 3 コマ(入り・途中・終わり)と、秒・演出・理由を並べる。"""
    times = [(0.12, sh["dur"] * 0.45, sh["dur"] - 0.05) for sh in sc["shots"]]
    got = {}
    for idx, t, img in render(sc, root, times):
        got.setdefault(idx, []).append((t, img))
    tw, th = 216, 384
    rowh = th + 50
    sheet = Image.new("RGB", (40 + 3 * (tw + 14) + 520, 30 + len(sc["shots"]) * rowh), (250, 250, 247))
    d = ImageDraw.Draw(sheet)
    fn, fb = font(F_NOTE, 22), font(F_NOTE, 26)
    start = 0.0
    for r, sh in enumerate(sc["shots"]):
        y = 30 + r * rowh
        for j, (t, img) in enumerate(got[r]):
            x = 20 + j * (tw + 14)
            sheet.paste(img.resize((tw, th), Image.LANCZOS), (x, y))
            d.text((x, y + th + 4), f"{t:.2f}s", font=fn, fill=(90, 90, 90))
        x = 20 + 3 * (tw + 14) + 10
        d.text((x, y), f"{start:.1f}s〜（{sh['dur']}秒）", font=fb, fill=(20, 20, 20))
        info = [f"写真: {sh['img']}", f"カメラ: {sh.get('cam', 'push')}・{sh.get('layout', 'full')}",
                f"演出: {sh['fx']}" + (f" / 入り: {sh['trans']}" if sh.get("trans") else "")]
        note = sh.get("note", "")
        info += [note[i:i + 20] for i in range(0, len(note), 20)]
        for j, ln in enumerate(info):
            d.text((x, y + 40 + j * 30), ln, font=fn, fill=(60, 60, 60))
        start += round(sh["dur"] * FPS) / FPS
    sheet.save(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("script")
    ap.add_argument("--out")
    ap.add_argument("--board")
    a = ap.parse_args()
    sc = json.load(open(a.script, encoding="utf-8"))
    root = os.path.join(os.path.dirname(os.path.abspath(a.script)), sc["assets"])
    if a.board:
        board(sc, root, a.board)
        print(a.board)
    if a.out:
        os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
        enc = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                                "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-crf", "17",
                                "-pix_fmt", "yuv420p", "-movflags", "+faststart", a.out], stdin=subprocess.PIPE)
        n = 0
        for _, _, img in render(sc, root):
            enc.stdin.write(img.tobytes())
            n += 1
        enc.stdin.close()
        enc.wait()
        print(f"{a.out} ({n / FPS:.1f}s, {len(sc['shots'])} shots, 無音)")


if __name__ == "__main__":
    main()
