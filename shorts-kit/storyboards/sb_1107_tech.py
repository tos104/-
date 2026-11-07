"""1107 ②〜⑤ を、テクニカル動画の最新版(fx_usdjpy_1022 v15)のデザインで描いた絵コンテ。

v15 のデザイン(実物から): 白地/チャートを画面幅いっぱいに大きく(帯 y≈940〜)/説明は右上の縦書き(しっぽり明朝 ExtraBold 80px、冒頭 92px)
/チャート上に赤丸・矢印・パターンの線・ラベル/画面を切り替えず、チャートを地続きで進める・寄る・引く
/最後に段階ごとに描く模式図(値動きをなぞった線+リボン)→ 保存の画面。小見出し・字幕の箱・床の格子は無い
"""
import os, subprocess, sys
sys.argv = ["x"]
sys.path.insert(0, "/home/user/-/shorts-kit")
import chart_short as cs
from PIL import Image, ImageDraw, ImageFont

SRC = "/home/user/-/output/src_1107/src.mp4"
OUT = "/home/user/-/output/sb_1107"
W, H = 1080, 1920
F_HEAD = "/home/user/-/shorts-kit/fonts/ShipporiMincho-ExtraBold.ttf"
F_MED = "/home/user/-/shorts-kit/fonts/ShipporiMincho-Medium.ttf"
cs.BG = (255, 255, 255)
INK, RED, BLUE, GREEN = (16, 18, 20), (150, 34, 32), (31, 104, 176), (24, 140, 84)
PANEL_Y, PANEL_H = 940, 780
_f = {}


def F(s, p=F_HEAD):
    if (p, s) not in _f:
        _f[p, s] = ImageFont.truetype(p, s)
    return _f[p, s]


def grab(t):
    p = f"{OUT}/src_{t}.png"
    if not os.path.exists(p):
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(t), "-i", SRC, "-frames:v", "1", p], check=True)
    return Image.open(p).convert("RGB")


def chart(im, t, cx, cy, w, marks=()):
    """元動画のコマ(640x360)を中心 (cx,cy)・幅 w で切り抜き、帯いっぱいに拡大(仮。本番は高画質の画像で地続きに)。
    marks: ("ring"|"dot"|"arrow"|"label"|"line", 帯内の x 割合, y 割合, ...)"""
    h = w * PANEL_H / W
    fr = grab(t)
    canvas = Image.new("RGB", (fr.width + 400, fr.height + 400), (255, 255, 255))
    canvas.paste(fr, (200, 200))
    crop = canvas.crop((int(cx - w / 2 + 200), int(cy - h / 2 + 200), int(cx + w / 2 + 200), int(cy + h / 2 + 200)))
    crop = crop.resize((W, PANEL_H), Image.LANCZOS)
    im.paste(crop, (0, PANEL_Y), cs.edge_mask())
    d = ImageDraw.Draw(im)
    for m in marks:
        kind, rx, ry = m[0], m[1], m[2]
        x, y = rx * W, PANEL_Y + ry * PANEL_H
        if kind == "ring":
            d.ellipse((x - 40, y - 40, x + 40, y + 40), outline=RED, width=8)
        elif kind == "dot":
            d.ellipse((x - 14, y - 14, x + 14, y + 14), fill=m[4] if len(m) > 4 else RED, outline=(255, 255, 255), width=4)
            if len(m) > 3:
                d.text((x - 26, y - 34), m[3], font=F(40), anchor="rm", fill=m[4] if len(m) > 4 else RED,
                       stroke_width=6, stroke_fill=(255, 255, 255))
        elif kind == "arrow":
            x2, y2 = m[3] * W, PANEL_Y + m[4] * PANEL_H
            d.line((x, y, x2, y2), fill=m[5] if len(m) > 5 else RED, width=9)
            d.ellipse((x2 - 10, y2 - 10, x2 + 10, y2 + 10), fill=m[5] if len(m) > 5 else RED)
        elif kind == "label":
            d.text((x, y), m[3], font=F(44), anchor="mm", fill=m[4] if len(m) > 4 else INK,
                   stroke_width=7, stroke_fill=(255, 255, 255))
        elif kind == "line":
            d.line((x, y, m[3] * W, PANEL_Y + m[4] * PANEL_H), fill=m[5] if len(m) > 5 else INK, width=6)


def tate(im, text, size=80):
    cs.draw_tate(im, text, F(size), INK, 99, "right", y_top=540)


def steps_diagram(im, title, pts, extras):
    """最後の模式図(v15 と同じ形): 左上に段階の名前、なぞった値動き、ラベル。"""
    d = ImageDraw.Draw(im)
    d.multiline_text((50, 600), title, font=F(44), fill=INK, spacing=12)
    import numpy as np
    xs = np.array([p[0] for p in pts], float); ys = np.array([p[1] for p in pts], float)
    gx = np.arange(xs[0], xs[-1] + 1, 6); gy = np.interp(gx, xs, ys)
    def ma(n, off):
        k = np.convolve(np.pad(gy, (n, 0), mode="edge"), np.ones(n) / n, "valid")[:len(gx)]
        return [(x, y + off) for x, y in zip(gx, k)]
    layer = Image.new("RGBA", im.size, (0, 0, 0, 0)); dl = ImageDraw.Draw(layer)
    for (n1, n2, cu, cd) in [(30, 60, (245, 215, 90, 90), (110, 205, 130, 80)), (8, 16, (235, 110, 100, 90), (80, 130, 230, 80))]:
        a, b = ma(n1, 0), ma(n2, 0)
        dl.polygon(a + b[::-1], fill=cu)
        dl.line(a, fill=cu[:3] + (255,), width=4); dl.line(b, fill=cd[:3] + (255,), width=4)
    im.paste(layer, (0, 0), layer)
    d = ImageDraw.Draw(im)
    d.line(pts, fill=INK, width=7, joint="curve")
    for e in extras:
        if e[0] == "line":
            d.line(e[1], fill=e[2], width=e[3] if len(e) > 3 else 5)
        elif e[0] == "text":
            d.text(e[1], e[2], font=F(38), anchor="mm", fill=e[3], stroke_width=5, stroke_fill=(255, 255, 255))
        elif e[0] == "band":
            d.rectangle(e[1], fill=(198, 216, 236), outline=BLUE, width=4)
    d.text((W - 60, 1640), "模式図", font=F(30, F_MED), anchor="rm", fill=(90, 96, 104))


def end_card(im):
    d = ImageDraw.Draw(im)
    d.text((540, PANEL_Y + 120), "保存して、次のトレードで試す", font=F(58), anchor="mm", fill=BLUE)
    for n, l in enumerate(["教育目的であり、金融・投資助言では", "ありません。取引判断はご自身で", "行ってください。"]):
        d.text((540, PANEL_Y + 330 + n * 74), l, font=F(52), anchor="mm", fill=INK)


def C(t, cx, cy, w, tt, marks=(), size=80):
    def f(im):
        chart(im, t, cx, cy, w, marks)
        tate(im, tt, size)
    return f


# ---- ② トライアングル → レジサポ転換 → 押し目買い(チャートは 13:24〜14:35 の画面)
P2 = ("② トライアングル → レジサポ転換 → 押し目買い(推奨・レジサポ転換は ×1.51)", [
    (2.6, C(809, 200, 200, 150, "トライ\nアングルを\n抜けた瞬間に\n買うと…", [("ring", 0.62, 0.45), ("dot", 0.62, 0.45, "もし買ったら")], 92),
     "冒頭(1022 と同じ型)。抜けた所に寄って赤丸", "13:20〜13:24"),
    (2.4, C(809, 200, 200, 230, "すぐ\n押して\nくる", [("arrow", 0.62, 0.40, 0.70, 0.62)]),
     "飛び乗った後に押してくる(地続きで右へ進める)", "13:50"),
    (2.0, C(827, 170, 190, 300, "待てる人は\nここが違う"), "1.5倍速で流して引く(1022 と同じ)", "-"),
    (3.0, C(827, 170, 190, 300, "上に抜けて\n安値を\n割らない", [("line", 0.18, 0.80, 0.55, 0.62, BLUE), ("label", 0.32, 0.88, "安値を割らない", BLUE)]),
     "根拠1(ダウで上)", "13:40"),
    (3.2, C(845, 170, 190, 300, "200で\n抑えられて\nいた線が\n支えに", [("label", 0.30, 0.30, "抵抗", RED), ("label", 0.70, 0.62, "支え", GREEN)]),
     "根拠2 レジサポ転換。線に「抵抗→支え」のラベル", "14:00〜14:10"),
    (2.8, C(857, 220, 200, 200, "押した所で\n買い", [("ring", 0.68, 0.52), ("dot", 0.68, 0.52, "買い", BLUE)]),
     "入り方。寄って青い点", "13:50"),
    (3.0, C(875, 180, 180, 330, "決済は\nトライアングル\nの角度で\nチャネル", [("line", 0.35, 0.75, 0.95, 0.25, INK), ("line", 0.35, 0.95, 0.95, 0.45, INK)]),
     "引いて決済の目安(平行な2本)", "14:20〜14:40"),
    (8.0, lambda im: steps_diagram(im, "① トライアングル\n② 上に抜けて安値を割らない\n③ レジサポ転換\n④ 押した所で買い → チャネルで決済",
        [(80, 1300), (180, 1060), (260, 1250), (350, 1110), (420, 1220), (500, 1150), (560, 1180), (640, 980), (720, 1100), (820, 900), (960, 800)],
        [("line", (60, 1040, 600, 1160), RED), ("line", (60, 1320, 600, 1190), BLUE), ("line", (60, 1120, 1000, 1120), GREEN, 4),
         ("text", (900, 1150), "200", GREEN), ("text", (720, 1160), "買い", BLUE)]),
     "まとめの模式図(1022 と同じ・段階ごとに描く)。リボンも入れる(必須)", "-"),
    (2.0, end_card, "保存の画面", "-"),
])

# ---- ③ ウェッジ(14:49〜15:06)
P3 = ("③ 上昇の後のウェッジ(理由の説明が元動画に無い → ② に入れるのを推奨)", [
    (2.6, C(897, 160, 190, 160, "ウェッジを\n下に抜けて\n売ると…", [("ring", 0.55, 0.55), ("dot", 0.55, 0.55, "もし売ったら")], 92), "冒頭", "14:49"),
    (2.6, C(901, 150, 190, 280, "上昇の後の\nウェッジは", [("line", 0.15, 0.85, 0.60, 0.30, BLUE), ("line", 0.15, 0.55, 0.60, 0.20, RED)]), "形を線で", "14:49"),
    (2.6, C(905, 150, 190, 280, "下に抜けても\nまだ上に\n注意"), "結論", "14:52〜14:58"),
    (2.6, C(905, 150, 190, 280, "(なぜか)\n※本人に\n聞いて埋める"), "※理由が空く", "-"),
    (2.0, end_card, "保存の画面", "-"),
])

# ---- ④ 三尊(拡大っぽい形・15:09〜15:57)
P4 = ("④ 三尊でも注意が要る形(三尊は休む方針なので後回し)", [
    (2.6, C(917, 330, 170, 200, "三尊だから\n売ると…", [("line", 0.25, 0.55, 0.45, 0.35, RED), ("line", 0.45, 0.35, 0.60, 0.60, RED), ("line", 0.60, 0.60, 0.78, 0.30, RED)], 92), "冒頭", "15:10"),
    (3.0, C(917, 330, 170, 200, "右肩が\n上に来て\nさらに下", [("label", 0.25, 0.45, "左肩", RED), ("label", 0.45, 0.25, "頭", RED), ("label", 0.78, 0.20, "右肩", RED)]),
     "形にラベル", "15:10〜15:18"),
    (2.6, C(929, 330, 170, 260, "拡大っぽい\n時もある\n注意"), "結論", "15:20"),
    (3.0, C(935, 330, 180, 280, "真ん中の\n三尊で\n抵抗を受けて\n下がった"), "実際の値動き", "15:30〜15:38"),
    (3.0, C(955, 360, 190, 220, "リボンが\n抜けて\n押した所で\n入る", [("ring", 0.75, 0.55)]), "入り方", "15:50〜15:55"),
    (2.0, end_card, "保存の画面", "-"),
])

# ---- ⑤ N・M チャネル(16:00〜16:54)
P5 = ("⑤ N・M のチャネルで決済(三尊に近い話)", [
    (2.6, C(1013, 340, 170, 230, "決済、\nどこで\nしてる？", size=92), "冒頭", "16:00"),
    (3.0, C(983, 340, 170, 230, "大きく\n見ればM\nここで\n入ったらN", [("dot", 0.62, 0.55, "入り", BLUE)]), "見る大きさで形が変わる", "16:10〜16:23"),
    (3.0, C(1001, 340, 170, 230, "三尊みたいな\n時は\n右肩の幅の\n倍", [("line", 0.45, 0.30, 0.95, 0.30, INK), ("line", 0.45, 0.55, 0.95, 0.55, INK)]), "決済の目安", "16:40〜16:47"),
    (2.6, C(1013, 340, 170, 300, "伸ばすと\nまだ\n効いている"), "実際に効いているか", "16:50"),
    (2.0, end_card, "保存の画面", "-"),
])


def board(key, title_, cuts_):
    TW, TH = 300, 533
    cols = 5
    rows = (len(cuts_) + cols - 1) // cols
    b = Image.new("RGB", (cols * (TW + 20) + 20, 140 + rows * (TH + 150)), (236, 238, 240))
    bd = ImageDraw.Draw(b)
    bd.text((20, 20), title_, font=F(34), fill=INK)
    total = sum(c[0] for c in cuts_)
    bd.text((20, 74), f"計 {total:.1f} 秒・{len(cuts_)}カット・デザインは 1022 v15 と同じ・チャートは元動画 640x360 の拡大(仮)", font=F(26), fill=RED)
    t0 = 0
    for k, (dur, fn, why, src) in enumerate(cuts_):
        im = Image.new("RGB", (W, H), (255, 255, 255))
        fn(im)
        x, y = 20 + (k % cols) * (TW + 20), 140 + (k // cols) * (TH + 150)
        b.paste(im.resize((TW, TH), Image.LANCZOS), (x, y))
        cap = f"#{k+1} {t0:.1f}〜{t0+dur:.1f}秒 {why}\n元動画 {src}"
        lines = []
        for para in cap.split("\n"):
            cur = ""
            for ch in para:
                if F(19, F_MED).getlength(cur + ch) > TW:
                    lines.append(cur); cur = ""
                cur += ch
            lines.append(cur)
        bd.multiline_text((x, y + TH + 8), "\n".join(lines[:5]), font=F(19, F_MED), fill=INK, spacing=3)
        t0 += dur
    b.save(f"{OUT}/tech_{key}.png")
    print(key, total)


for key, (tt, cc) in {"2_triangle": P2, "3_wedge": P3, "4_hs": P4, "5_channel": P5}.items():
    board(key, tt, cc)
