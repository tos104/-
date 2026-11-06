"""図解ネオン(白版)の部品。PLAYBOOK 4.861 のスタイルガイドの数値で描く。

1 つの舞台に物を足し、色と位置を変えて見せる(場面転換なし)。
"""
import math, os
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
W, H = 1080, 1920
BG = (255, 255, 255)
INK = (18, 24, 38)
SUB = (131, 144, 168)
GRID = (227, 232, 239)
BLUE, RED, GREEN, PEOPLE = (31, 122, 224), (216, 81, 58), (15, 165, 127), (91, 143, 214)
BOX, SHELF_Y = (241, 244, 248), 1000
F_BLACK = os.path.join(HERE, "fonts", "ShipporiMincho-ExtraBold.ttf")   # nori のテクニカル動画と同じ(ユーザー指定 2026-11-06)
F_XB = os.path.join(HERE, "fonts", "ShipporiMincho-ExtraBold.ttf")
F_MED = os.path.join(HERE, "fonts", "ShipporiMincho-Medium.ttf")
_fc = {}


def F(size, path=F_BLACK):
    if (path, size) not in _fc:
        _fc[path, size] = ImageFont.truetype(path, size)
    return _fc[path, size]


def ease(k):
    k = min(1.0, max(0.0, k))
    return 1 - (1 - k) ** 3


def back(k):
    """少し行き過ぎて戻る(物が置かれる時。減衰 0.7 前後の上質なばね 4.87)。"""
    k = min(1.0, max(0.0, k))
    c = 1.4
    return 1 + (c + 1) * (k - 1) ** 3 + c * (k - 1) ** 2


def _background():
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    hz, vx = 1380, W / 2            # 床の格子(遠近)。上ほど薄く
    for i in range(-12, 13):
        d.line((vx + i * 40, hz, vx + i * 260, H), fill=GRID, width=2)
    y, gap = hz, 18
    while y < H:
        d.line((0, y, W, y), fill=GRID, width=2)
        y += gap
        gap *= 1.35
    return im


def glow(im, draw_fn, color, width=18, alpha=0.35):
    """draw_fn(d, col) で描いたものを、同じ色でにじませてから本体を重ねる(ネオン)。
    にじみは描いた範囲だけ切り出してぼかす(全画面をぼかすと遅いため)。"""
    layer = Image.new("RGBA", im.size, (0, 0, 0, 0))
    draw_fn(ImageDraw.Draw(layer), color + (255,))
    bb = layer.getbbox()
    if not bb:
        return
    m = width * 3
    box = (max(0, bb[0] - m), max(0, bb[1] - m), min(im.width, bb[2] + m), min(im.height, bb[3] + m))
    part = layer.crop(box)
    halo = part.filter(ImageFilter.GaussianBlur(width))
    a = halo.getchannel("A").point(lambda v: int(v * alpha))
    halo.putalpha(a)
    im.paste(halo, box[:2], halo)
    im.paste(part, box[:2], part)


_BG = []


def background():
    if not _BG:
        _BG.append(_background())
    return _BG[0].copy()


def shelf(im, y=SHELF_Y, k=1.0):
    glow(im, lambda d, c: d.line((40, y, 40 + (W - 80) * ease(k), y), fill=c, width=4), (150, 175, 210), 10, 0.5)


def title(im, text, y=200, size=72, alpha=1.0):
    d = ImageDraw.Draw(im)
    for i, line in enumerate(text.split("\n")):
        d.text((W / 2, y + i * size * 1.25), line, font=F(size), anchor="ma", fill=INK)


def header(im, text, y=230):
    ImageDraw.Draw(im).text((W / 2, y), text, font=F(48), anchor="ma", fill=SUB)


def caption(im, text, y=1300, final=False):
    d = ImageDraw.Draw(im)
    lines = text.split("\n")
    w = max(F(56).getlength(l) for l in lines) + 120
    h = len(lines) * 76 + 60
    x0 = (W - w) / 2
    if final:
        d.rounded_rectangle((x0, y, x0 + w, y + h), 28, fill=(232, 248, 242), outline=GREEN, width=5)
    else:
        d.rounded_rectangle((x0, y, x0 + w, y + h), 28, fill=BOX)
    for i, l in enumerate(lines):
        d.text((W / 2, y + 30 + i * 76), l, font=F(56), anchor="ma", fill=GREEN if final else INK)


def person(d, cx, base, col, s=1.0, w=5):
    """線画の人(頭+肩)。base は足元の y。"""
    r = 17 * s
    d.ellipse((cx - r, base - 78 * s, cx + r, base - 44 * s), outline=col, width=w)
    d.rounded_rectangle((cx - 30 * s, base - 38 * s, cx + 30 * s, base), int(20 * s), outline=col, width=w)


def people(im, pts, col=PEOPLE, s=1.2):
    glow(im, lambda d, c: [person(d, x, y, c, s) for x, y in pts], col, 10, 0.4)


def building(im, cx, base, col=INK, k=1.0, label="FX会社"):
    """FX会社(線画の建物)。k で下から伸びる。"""
    h = 260 * back(k)
    def f(d, c):
        d.rectangle((cx - 140, base - h, cx + 140, base), outline=c, width=6)
        d.polygon([(cx - 170, base - h), (cx, base - h - 80 * min(1, k * 1.2)), (cx + 170, base - h)], outline=c, width=6)
        for i in range(4):
            x = cx - 90 + i * 60
            d.line((x, base - h + 50, x, base - 20), fill=c, width=6)
    glow(im, f, col, 16, 0.3)
    if k >= 1:
        ImageDraw.Draw(im).text((cx, base + 24), label, font=F(46), anchor="ma", fill=col)


def spread_band(im, cx, y, w, gap, fill_k=1.0, q=0.0, label=None, dashed=False):
    """買う値段(赤)と売る値段(青)の 2 本の線と、その間(スプレッド)。"""
    d = ImageDraw.Draw(im)
    x0, x1 = cx - w / 2, cx + w / 2
    if fill_k > 0:
        layer = Image.new("RGBA", im.size, (0, 0, 0, 0))
        ImageDraw.Draw(layer).rectangle((x0, y, x1, y + gap), fill=(255, 210, 200, int(150 * fill_k)))
        im.paste(layer, (0, 0), layer)
    def line(d2, c, yy):
        if dashed:
            xx = x0
            while xx < x1:
                d2.line((xx, yy, min(xx + 26, x1), yy), fill=c, width=6)
                xx += 44
        else:
            d2.line((x0, yy, x1, yy), fill=c, width=6)
    glow(im, lambda d2, c: line(d2, c, y), RED, 12, 0.35)
    glow(im, lambda d2, c: line(d2, c, y + gap), BLUE, 12, 0.35)
    d = ImageDraw.Draw(im)
    d.text((x0, y - 14), "買う値段", font=F(40, F_XB), anchor="ld", fill=RED)
    d.text((x0, y + gap + 14), "売る値段", font=F(40, F_XB), anchor="la", fill=BLUE)
    if q > 0.05:      # 縮みながら消える(大きさ 0 は描かない)
        d.text((cx, y + gap / 2), "？", font=F(max(8, int(100 * q))), anchor="mm", fill=INK)
    if label:
        d.text((cx, y + gap / 2), label, font=F(54), anchor="mm", fill=INK)


def sticker(im, cx, cy, text, col=GREEN, angle=-8, k=1.0):
    """斜めの札(「お得！」の型)。k で大きさが弾んで出る。"""
    if k <= 0:
        return
    f = F(54)
    tw = f.getlength(text)
    tile = Image.new("RGBA", (int(tw + 120), 140), (0, 0, 0, 0))
    td = ImageDraw.Draw(tile)
    td.rounded_rectangle((10, 20, tw + 110, 120), 20, fill=col + (255,))
    td.text(((tw + 120) / 2, 70), text, font=f, anchor="mm", fill=(255, 255, 255, 255))
    s = back(k)
    tile = tile.resize((max(1, int(tile.width * s)), max(1, int(tile.height * s))), Image.LANCZOS).rotate(-angle, expand=True, resample=Image.BICUBIC)
    im.paste(tile, (int(cx - tile.width / 2), int(cy - tile.height / 2)), tile)


def pill(im, text, y=330, k=1.0, cursor=False):
    """上に出る案内の札(角丸・線)。"""
    if k <= 0:
        return
    d = ImageDraw.Draw(im)
    f = F(46)
    w = f.getlength(text) + 140
    x0 = (W - w) / 2
    yy = y + 20 * (1 - ease(k))
    glow(im, lambda d2, c: d2.rounded_rectangle((x0, yy, x0 + w, yy + 100), 26, outline=c, width=5), (120, 110, 210), 14, 0.35)
    d = ImageDraw.Draw(im)
    d.text((W / 2 + 20, yy + 50), text, font=f, anchor="mm", fill=INK)
    d.ellipse((x0 + 34, yy + 30, x0 + 58, yy + 54), outline=(120, 110, 210), width=4)
    d.rounded_rectangle((x0 + 26, yy + 56, x0 + 66, yy + 76), 8, outline=(120, 110, 210), width=4)
    if cursor:
        cx, cy = x0 + w - 30, yy + 70
        d.polygon([(cx, cy), (cx, cy + 60), (cx + 16, cy + 46), (cx + 30, cy + 74), (cx + 40, cy + 68), (cx + 26, cy + 42), (cx + 46, cy + 40)],
                  fill=(255, 255, 255), outline=INK)


def note(im, text, x=40, y=930):
    ImageDraw.Draw(im).text((x, y), text, font=F(30, F_MED), fill=SUB)


def arrow(im, x0, y0, x1, y1, col, w=8, k=1.0):
    if k <= 0:
        return
    x1, y1 = x0 + (x1 - x0) * k, y0 + (y1 - y0) * k
    def f(d, c):
        d.line((x0, y0, x1, y1), fill=c, width=w)
        a = math.atan2(y1 - y0, x1 - x0)
        L = 30
        d.polygon([(x1, y1), (x1 - L * math.cos(a - 0.45), y1 - L * math.sin(a - 0.45)),
                   (x1 - L * math.cos(a + 0.45), y1 - L * math.sin(a + 0.45))], fill=c)
    glow(im, f, col, 10, 0.3)
