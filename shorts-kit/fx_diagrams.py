"""FX の図解ショート用の図(絵コンテ 1107 ①「FX会社の稼ぎ方」)。chart_short.py の diagram から呼ぶ。

各図は t 秒で要素を順に出す(主役は 1 カットに 1 つ。PLAYBOOK 4.87)。数字は描かない(4.45)。
座標は帯の上端 oy からの相対(幅 1080)。下端は oy+640 まで(画面下のショートの文字と重ねない)。
"""
import math
from PIL import Image, ImageDraw

RED, BLUE, GRAY = (150, 34, 32), (31, 104, 176), (110, 110, 116)
PINK = (255, 226, 222)


def _e(k):                      # ease-out
    k = min(1.0, max(0.0, k))
    return 1 - (1 - k) ** 3


def _arrow(d, x0, y0, x1, y1, col, w=8):
    d.line((x0, y0, x1, y1), fill=col, width=w)
    a = math.atan2(y1 - y0, x1 - x0)
    L = 30
    d.polygon([(x1, y1), (x1 - L * math.cos(a - 0.45), y1 - L * math.sin(a - 0.45)),
               (x1 - L * math.cos(a + 0.45), y1 - L * math.sin(a + 0.45))], fill=col)


def _person(d, cx, cy, col, label, F):
    d.ellipse((cx - 34, cy - 110, cx + 34, cy - 42), fill=col)
    d.rounded_rectangle((cx - 55, cy - 36, cx + 55, cy + 70), 30, fill=col)
    d.text((cx, cy + 110), label, font=F(46), anchor="mm", fill=col)


def _fade_layer(im, draw_fn, alpha):
    """draw_fn(d) を透明度 alpha(0〜1)で重ねる。"""
    if alpha <= 0:
        return
    layer = Image.new("RGBA", im.size, (0, 0, 0, 0))
    draw_fn(ImageDraw.Draw(layer))
    if alpha < 1:
        a = layer.getchannel("A").point(lambda v: int(v * alpha))
        layer.putalpha(a)
    im.paste(layer, (0, 0), layer)


def _spread(im, d, oy, F, INK, fill=PINK, q=0.0, label=1.0, share=0.0, gap=120):
    y0 = oy + 170
    d.rectangle((140, y0, 940, y0 + gap), fill=fill)
    d.line((140, y0, 940, y0), fill=RED, width=8)
    d.line((140, y0 + gap, 940, y0 + gap), fill=BLUE, width=8)
    d.text((140, y0 - 52), "買う値段", font=F(46), fill=RED)
    d.text((140, y0 + gap + 18), "売る値段", font=F(46), fill=BLUE)
    _fade_layer(im, lambda dl: dl.text((540, y0 + gap / 2), "？", font=F(110), anchor="mm", fill=INK + (255,)), q)
    _fade_layer(im, lambda dl: dl.text((540, y0 + gap / 2), "スプレッド", font=F(54), anchor="mm", fill=INK + (255,)), label)
    if share > 0:
        def f(dl):
            yb = y0 + gap + 200
            dl.line((860, yb, 860, y0 + gap + 24), fill=INK + (255,), width=8)
            dl.polygon([(860, y0 + gap + 14), (842, y0 + gap + 44), (878, y0 + gap + 44)], fill=INK + (255,))
            dl.text((860, yb + 40), "FX会社の取り分", font=F(46), anchor="mm", fill=INK + (255,))
        _fade_layer(im, f, share)


def draw(im, name, t, dur, oy, F, INK):
    d = ImageDraw.Draw(im)
    if name == "spread_q":          # 1コマ目から全部見せる(題材と争点。4.97)
        _spread(im, d, oy, F, INK, fill=(238, 240, 242), q=1.0, label=0.0)
    elif name == "spread":          # 「？」が消えて「スプレッド」、取り分の矢印
        p = _e(t / 0.3)
        fill = tuple(int(a + (b - a) * p) for a, b in zip((238, 240, 242), PINK))
        _spread(im, d, oy, F, INK, fill=fill, q=1 - p, label=p, share=_e((t - 0.8) / 0.3))
    elif name == "dealer":          # 肩書きを足す
        _spread(im, d, oy, F, INK, share=1.0)
        p = _e((t - 0.3) / 0.25)
        def f(dl):
            yy = oy + 30 + 16 * (1 - p)
            dl.rounded_rectangle((280, yy, 800, yy + 80), 16, outline=INK + (255,), width=4, fill=(255, 255, 255, 255))
            dl.text((540, yy + 40), "カバーディーラー出身", font=F(42), anchor="mm", fill=INK + (255,))
        _fade_layer(im, f, p)
    elif name == "both":            # 雇用統計の前、買う人も売る人もいる
        cy = oy + 330
        _fade_layer(im, lambda dl: _person(dl, 230, cy, RED + (255,), "買う人", F), _e((t - 0.3) / 0.25))
        _fade_layer(im, lambda dl: _person(dl, 850, cy, BLUE + (255,), "売る人", F), _e((t - 0.6) / 0.25))
        _fade_layer(im, lambda dl: dl.multiline_text((540, cy - 10), "どちらも\nいる", font=F(52), anchor="mm",
                                                     align="center", fill=INK + (255,)), _e((t - 1.0) / 0.25))
    elif name == "cover":           # 矢印が会社で出会う(主役)
        cy = oy + 300
        _person(d, 190, cy, RED, "買う人", F)
        _person(d, 890, cy, BLUE, "売る人", F)
        d.rounded_rectangle((390, cy - 70, 690, cy + 50), 20, outline=INK, width=6)
        d.text((540, cy - 10), "FX会社", font=F(50), anchor="mm", fill=INK)
        p = _e((t - 0.2) / 0.6)
        if p > 0:
            _arrow(d, 260, cy - 10, 260 + (380 - 260) * p, cy - 10, RED)
            _arrow(d, 820, cy - 10, 820 - (820 - 700) * p, cy - 10, BLUE)
        _fade_layer(im, lambda dl: dl.text((540, cy + 190), "お客さん同士でカバー", font=F(58), anchor="mm",
                                           fill=INK + (255,)), _e((t - 1.0) / 0.25))
    elif name == "stay":            # ストップを置く人は去り、我慢する人が残る
        cy = oy + 300
        p = _e((t - 0.4) / 0.8)
        _fade_layer(im, lambda dl: (_person(dl, 250 - 60 * p, cy - 120 * p, GRAY + (255,), "ストップを置く人", F)), 1 - 0.75 * p)
        _person(d, 800, cy, RED, "我慢する人", F)
        _fade_layer(im, lambda dl: dl.text((800, cy + 190), "→ 残る", font=F(60), anchor="mm", fill=RED + (255,)),
                    _e((t - 1.4) / 0.25))
    elif name == "old_new":         # 昔は広い、今は狭い
        for k, (x0, gap, lab, t0) in enumerate([(110, 230, "昔", 0.0), (600, 80, "今", 0.8)]):
            p = _e((t - t0) / 0.35)
            if p <= 0:
                continue
            y0 = oy + 160
            g = gap * p
            d.rectangle((x0, y0, x0 + 370, y0 + g), fill=PINK)
            d.line((x0, y0, x0 + 370, y0), fill=RED, width=8)
            d.line((x0, y0 + g, x0 + 370, y0 + g), fill=BLUE, width=8)
            d.text((x0 + 185, y0 - 70), lab, font=F(64), anchor="mm", fill=INK)
        _fade_layer(im, lambda dl: dl.text((540, oy + 500), "スプレッドが広かった", font=F(52), anchor="mm",
                                           fill=INK + (255,)), _e((t - 1.2) / 0.25))
    elif name == "pairs":           # 狭い通貨 ○ / マイナー通貨 ×(幅は形だけ・数字なし)
        rows = [("ドル円", 60, BLUE, "○", 0.2), ("ユーロドル", 70, BLUE, "○", 0.5), ("マイナー通貨", 300, RED, "×", 0.8)]
        for k, (nm, w, col, mk, t0) in enumerate(rows):
            p = _e((t - t0) / 0.35)
            if p <= 0:
                continue
            y = oy + 80 + k * 190
            d.text((90, y + 30), nm, font=F(54), anchor="lm", fill=INK)
            d.rectangle((480, y, 480 + max(1, w * p), y + 60), fill=col)
            if t >= 1.2:
                d.text((990, y + 30), mk, font=F(76), anchor="mm", fill=col)
    elif name == "next":            # 次は入り方 → 関連動画(信頼動画へ。4.996)
        p = _e((t - 0.2) / 0.3)
        def f(dl):
            dl.rounded_rectangle((140, oy + 100, 940, oy + 390), 24, outline=BLUE + (255,), width=6, fill=(255, 255, 255, 255))
            dl.text((540, oy + 190), "関連動画", font=F(46), anchor="mm", fill=BLUE + (255,))
            dl.text((540, oy + 290), "待てる人の入り方", font=F(58), anchor="mm", fill=INK + (255,))
        _fade_layer(im, f, p)
        q = _e((t - 0.6) / 0.3)
        if q > 0:
            _arrow(d, 540, oy + 560, 540, oy + 560 - 150 * q, BLUE)
    else:
        raise KeyError(name)


NAMES = {"spread_q", "spread", "dealer", "both", "cover", "stay", "old_new", "pairs", "next"}
