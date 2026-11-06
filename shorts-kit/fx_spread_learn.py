"""1107 ① FX会社の稼ぎ方(学びの流れ v8・冒頭A)の舞台。neon_short.py の scene "fx_spread_learn"。

各カット = 前のカットで生まれた疑問への答え(PLAYBOOK 4.9986)。カットの中の時刻 u(秒)で物を順に出す。
"""
from PIL import Image, ImageDraw
from neon_stage import *          # noqa

CX, BAND_Y = 540, 450
YOU = (300, 1200)
L_PTS = [(80 + i * 66, 1200) for i in range(5)]
L_STAY = [(120, 1200), (186, 1200), (153, 1110)]
L_LEAVE = [(420, 1265), (490, 1285)]                 # 右下へ去る(ユーザー指定)
STACK6 = [(120, 1200), (186, 1200), (252, 1200), (153, 1110), (219, 1110), (186, 1020)]
GRAY = (205, 210, 218)


def k_(u, t0, d=0.3):
    return ease((u - t0) / d)


def fade(im, fn, a):
    if a <= 0:
        return im
    tmp = im.copy()
    fn(tmp)
    return tmp if a >= 1 else Image.blend(im, tmp, a)


def lerp(a, b, k):
    return tuple(x + (y - x) * k for x, y in zip(a, b))


def you(im, x=YOU[0], y=YOU[1], label="あなた", k=1.0):
    if k <= 0:
        return
    s = 1.6 * back(k)
    people(im, [(x, y)], RED, s=max(0.2, s))
    ImageDraw.Draw(im).text((x, y + 16), label, font=F(46), anchor="ma", fill=RED)


def loss_chart(im, k):
    """買った値段から値段が下がり続け、含み損(赤い面)が広がる。k=0〜1 で右へ進む。"""
    x0, x1, yb = 120, 960, 760
    pts = [(120, 760), (220, 740), (300, 770), (380, 820), (450, 800), (530, 870), (610, 930), (680, 905),
           (760, 990), (840, 1050), (960, 1110)]
    xe = x0 + (x1 - x0) * k
    vis = [p for p in pts if p[0] <= xe]
    i = len(vis)
    if 0 < i < len(pts) and vis[-1][0] < xe:
        a, b = pts[i - 1], pts[i]
        r = (xe - a[0]) / (b[0] - a[0])
        vis.append((xe, a[1] + (b[1] - a[1]) * r))
    layer = Image.new("RGBA", im.size, (0, 0, 0, 0))
    if len(vis) > 1:
        ImageDraw.Draw(layer).polygon([(vis[0][0], yb)] + [(x, max(y, yb)) for x, y in vis] + [(vis[-1][0], yb)],
                                      fill=(216, 81, 58, 70))
    im.paste(layer, (0, 0), layer)
    d = ImageDraw.Draw(im)
    xx = x0
    while xx < x1:
        d.line((xx, yb, min(xx + 24, x1), yb), fill=SUB, width=4)
        xx += 40
    d.text((x1, yb - 12), "買った値段", font=F(36), anchor="rd", fill=SUB)
    if len(vis) > 1:
        glow(im, lambda dd, c: dd.line(vis, fill=c, width=7, joint="curve"), INK, 8, 0.25)
    d = ImageDraw.Draw(im)
    d.ellipse((x0 - 16, yb - 16, x0 + 16, yb + 16), fill=RED)
    d.text((x0, yb + 26), "買い", font=F(40), anchor="ma", fill=RED)
    ex, ey = vis[-1]
    sticker(im, min(ex, 760), ey + 120, "含み損", col=RED, angle=-6)


def mini_band(im, cx, gap, col, label, k=1.0, dim=0.0):
    if k <= 0:
        return
    g = gap * back(k)
    top = SHELF_Y - 40 - g
    c = tuple(int(a + (b - a) * dim) for a, b in zip(col, (200, 205, 212)))
    layer = Image.new("RGBA", im.size, (0, 0, 0, 0))
    ImageDraw.Draw(layer).rectangle((cx - 120, top, cx + 120, top + g), fill=c + (int(60 - 35 * dim),))
    im.paste(layer, (0, 0), layer)
    glow(im, lambda d, cc: (d.line((cx - 120, top, cx + 120, top), fill=cc, width=6),
                            d.line((cx - 120, top + g, cx + 120, top + g), fill=cc, width=6)), c, 12, 0.35)
    ImageDraw.Draw(im).text((cx, SHELF_Y + 30), label, font=F(54), anchor="ma", fill=c)


HEADERS = [None, "FX会社の稼ぎ方", "① スプレッド", "① スプレッド", "② カバー", "② カバー", "② カバー",
           "③ 残る", "③ 残る", "なぜ狭い方がいい？", "なぜ狭い方がいい？", "まとめ", None]


def scene(im, t, cuts, sc=None):
    i = max(j for j, c0 in enumerate(cuts) if t >= c0)
    u = t - cuts[i]
    # 小見出し(カットが替わる時だけ溶かす)
    h = HEADERS[i] if i < len(HEADERS) else None
    if h:
        same = i > 0 and HEADERS[i - 1] == h
        im = fade(im, lambda x: header(x, h), 1.0 if same else k_(u, 0, 0.25))

    if i == 0:      # 入口: 含み損、我慢してない？(最初から含み損が見えていて、2秒かけて広がる)
        title(im, "{含み損}、\n我慢してない？", y=170, size=96)
        loss_chart(im, 0.62 + 0.38 * ease(u / 2.2))
        you(im, 200, 1300)
        return im

    # 舞台(棚と会社)。3 カット目(スプレッドの定義)と 11 カット目以降は会社を消す
    show_bldg = i in (1, 3, 4, 5, 6, 7, 8, 9)
    a = 1.0
    if show_bldg and i in (1, 3):
        a = k_(u, 0, 0.3)
    if not show_bldg and i in (2, 10) and u < 0.3:
        a = 1 - k_(u, 0, 0.3)
        show_bldg = True
    if show_bldg:
        im = fade(im, lambda x: building(x, CX, SHELF_Y), a)
    if i not in (11, 12):
        shelf(im)

    if i == 1:      # 結論を先に: 損してる人ほど残ると、FX会社は儲かる
        im = fade(im, lambda x: loss_chart(x, 1.0), 1 - k_(u, 0, 0.25))
        pts = [p for n, p in enumerate(L_STAY) if u >= 0.2 + 0.1 * n]
        if pts:
            people(im, pts, RED)
        sticker(im, 820, 760, "儲かる", col=GREEN, angle=-8, k=(u - 0.9) / 0.35)
    elif i == 2:    # ① スプレッドとは: 買った瞬間、この分マイナス
        y_buy, y_sell = BAND_Y + 120, BAND_Y + 270
        im = fade(im, lambda x: spread_band(x, CX, y_buy, 640, 150, label="スプレッド"), k_(u, 0.1, 0.3))
        d = ImageDraw.Draw(im)
        if u >= 0.5:
            d.ellipse((804, y_buy - 16, 836, y_buy + 16), fill=RED)
            d.text((820, y_buy - 40), "ここで買う", font=F(44), anchor="md", fill=RED)
        arrow(im, 820, y_buy + 20, 820, y_sell - 10, RED, k=k_(u, 0.9, 0.4))
        sticker(im, CX, y_sell + 130, "買った瞬間マイナス", col=RED, angle=-6, k=(u - 1.4) / 0.35)
    elif i == 3:    # その差は会社の取り分
        im = fade(im, lambda x: spread_band(x, CX, BAND_Y, 640, 110, label="スプレッド"), k_(u, 0, 0.3))
        if u >= 0.5:
            arrow(im, CX, BAND_Y + 130, CX, SHELF_Y - 340, INK, k=k_(u, 0.5, 0.3))
            ImageDraw.Draw(im).text((CX + 30, BAND_Y + 140), "取り分", font=F(44), anchor="la", fill=INK)
    elif i == 4:    # ② あなたが買うと、会社は反対に売りを持つ
        you(im, k=(u - 0.2) / 0.3)
        arrow(im, 360, 1100, 430, 960, RED, k=k_(u, 0.5, 0.5))
        if u >= 0.6:
            ImageDraw.Draw(im).text((330, 1010), "買い", font=F(46), anchor="rm", fill=RED)
        sticker(im, 700, 700, "会社は売り", col=BLUE, angle=-6, k=(u - 1.1) / 0.35)
    elif i == 5:    # 売る人もいるので、お客さん同士でカバー
        you(im)
        im = fade(im, lambda x: sticker(x, 700, 700, "会社は売り", col=BLUE, angle=-6), 1 - k_(u, 0, 0.25))
        arrow(im, 360, 1100, 450, 960, RED)
        kk = (u - 0.2) / 0.3
        if kk > 0:
            people(im, [(780, 1200)], BLUE, s=1.6 * back(kk))
            ImageDraw.Draw(im).text((780, 1216), "売る人", font=F(46), anchor="ma", fill=BLUE)
        arrow(im, 720, 1100, 630, 960, BLUE, k=k_(u, 0.5, 0.5))
        sticker(im, CX, 700, "ぶつけて±0", col=GREEN, angle=-6, k=(u - 1.2) / 0.35)
    elif i == 6:    # 会社は値動きで損しない。スプレッドだけ入る
        im = fade(im, lambda x: spread_band(x, CX, BAND_Y, 640, 110, label="スプレッド"), k_(u, 0, 0.3))
        arrow(im, CX, BAND_Y + 130, CX, SHELF_Y - 340, INK, k=k_(u, 0.3, 0.3))
        sticker(im, 820, 760, "スプレッドだけ", col=GREEN, angle=-8, k=(u - 0.9) / 0.35)
    elif i == 7:    # ③ ストップを置く人は抜け、我慢する人は損したまま残る
        mv = k_(u, 0.8, 0.9)
        stay, leave = [], []
        for n, p in enumerate(L_PTS):
            kk = back((u - 0.1 - 0.08 * n) / 0.3)
            if kk <= 0:
                continue
            if n < 3:
                stay.append(lerp(p, L_STAY[n], mv))
            else:
                leave.append((lerp(p, L_LEAVE[n - 3], mv), n))
        for q, n in leave:
            people(im, [q], tuple(int(c) for c in lerp(RED, GRAY, mv)))
        if stay:
            people(im, stay, RED)
        if u >= 1.5:
            ImageDraw.Draw(im).text((455, 1130), "ストップ→抜ける", font=F(34), anchor="ma", fill=SUB)
        sticker(im, 153, 940, "我慢→残る", col=RED, angle=-8, k=(u - 1.9) / 0.35)
    elif i == 8:    # 残るほど、会社は儲かってくる
        pts = [p for n, p in enumerate(STACK6) if n < 3 or u >= 0.2 + 0.12 * (n - 3)]
        people(im, pts, RED)
        sticker(im, 820, 760, "儲かる", col=GREEN, angle=-8, k=(u - 1.0) / 0.35)
    elif i == 9:    # 昔はもっと広くて、何もしなくても会社は増えた
        p = k_(u, 0.1, 0.4)
        spread_band(im, 290, 420, 380, max(2, 220 * p), label="昔" if p > 0.6 else None)
        q = k_(u, 0.9, 0.35)
        if q > 0:
            spread_band(im, 790, 495, 380, max(2, 70 * q), label=None)
            ImageDraw.Draw(im).text((790, 530), "今", font=F(54), anchor="mm", fill=INK)
    elif i == 10:   # スプレッドは毎回払う分。だから狭い通貨で
        mini_band(im, 180, 50, BLUE, "ドル円", k=(u - 0.2) / 0.35)
        mini_band(im, 540, 60, BLUE, "ユーロドル", k=(u - 0.5) / 0.35)
        mini_band(im, 900, 240, RED, "マイナー通貨", k=(u - 0.8) / 0.35, dim=k_(u, 1.0, 0.4))
        sticker(im, 300, 770, "払う分が小さい", col=GREEN, angle=-8, k=(u - 1.2) / 0.35)
    elif i == 11:   # まとめ(① ② は同じ大きさ)
        p = back((u - 0.1) / 0.35)
        if p > 0:
            d = ImageDraw.Draw(im)
            cy, hh = 830, 270 * p
            d.rounded_rectangle((100, cy - hh, 980, cy + hh), 36, fill=(232, 248, 242), outline=GREEN, width=6)
            if p >= 0.95:
                d.text((540, 640), "含み損を我慢しないために", font=F(48), anchor="mm", fill=INK)
                if u >= 0.4:
                    d.text((160, 800), "① ストップを置く", font=F(64), anchor="lm", fill=GREEN)
                if u >= 0.9:
                    d.text((160, 960), "② スプレッドの狭い通貨で", font=F(64), anchor="lm", fill=GREEN)
    elif i == 12:   # 保存をすすめる画面
        a = k_(u, 0, 0.25)
        def end(x):
            d = ImageDraw.Draw(x)
            d.rectangle((0, 0, W, H), fill=(255, 255, 255))
            d.text((540, 760), "保存して、次のトレードで試す", font=F(64), anchor="mm", fill=(31, 104, 176))
            for n, line in enumerate(["教育目的であり、金融・投資助言では", "ありません。取引判断はご自身で", "行ってください。"]):
                d.text((540, 930 + n * 84), line, font=F(52), anchor="mm", fill=INK)
        im = fade(im, end, a)
    return im
