# 3つの型の見比べ絵コンテ(神龍 32:02〜34:32)。素材の部分は灰色の枠(元動画のコマで置き換える)。
import sys
from PIL import Image, ImageDraw, ImageFont, ImageFilter
F = "/home/user/-/shorts-kit/fonts/"
DELA, MPB = F + "DelaGothicOne-Regular.ttf", F + "MPLUSRounded1c-Black.ttf"
W, H = 1080, 1920
WHITE, YEL, RED, BLK = (255, 255, 255), (255, 230, 0), (255, 42, 42), (0, 0, 0)

def font(p, s): return ImageFont.truetype(p, s)

def placeholder(d, box, label, dark=0):
    x0, y0, x1, y1 = box
    base = 120 - dark
    d.rectangle(box, fill=(base, base, base + 6))
    for k in range(x0 - (y1 - y0), x1, 60):
        d.line([(k, y1), (k + (y1 - y0), y0)], fill=(base + 14,) * 3, width=3)
    f = font(MPB, 40)
    for i, ln in enumerate(label.split("|")):
        tw = d.textlength(ln, font=f)
        d.text(((x0 + x1 - tw) / 2, (y0 + y1) / 2 - 50 + i * 54), ln, font=f, fill=(235, 235, 235))

def text3(d, xy, s, f, fill, anchor="mm", stroke=8):
    # 3層: 影(黒・ずらし) + 黒フチ + 本体
    x, y = xy
    d.text((x + 8, y + 10), s, font=f, fill=(0, 0, 0), anchor=anchor, stroke_width=stroke, stroke_fill=(0, 0, 0))
    d.text((x, y), s, font=f, fill=fill, anchor=anchor, stroke_width=stroke, stroke_fill=BLK)

def runs(d, cx, y, parts, f):  # [(文字, 色), ...] を中央揃えで1行に
    total = sum(d.textlength(t, font=f) for t, _ in parts)
    x = cx - total / 2
    for t, c in parts:
        text3(d, (x, y), t, f, c, anchor="lm")
        x += d.textlength(t, font=f)

def frame():
    im = Image.new("RGB", (W, H), (18, 18, 20)); return im, ImageDraw.Draw(im)

def ui(d):  # Shorts の UI がかぶる所(右のボタン・下の説明)
    d.rectangle((960, 1080, W, 1720), outline=(80, 200, 255), width=3)
    d.rectangle((0, 1720, W, H), outline=(80, 200, 255), width=3)
    d.text((24, 1740), "Shorts UI(文字を置かない)", font=font(MPB, 30), fill=(80, 200, 255))

# ---- 型A 上下分割
def A(i):
    im, d = frame()
    placeholder(d, (0, 0, W, 640), "元動画 32:02〜|手元とカードのコマ")
    d.rectangle((0, 640, W, 900), fill=BLK)
    if i == 0:
        runs(d, W / 2, 770, [("仕入れ", WHITE), ("35,000円", YEL)], font(DELA, 110))
        placeholder(d, (60, 940, 1020, 1660), "神龍の接写|(同区間から拡大)")
        runs(d, W / 2, 1560, [("一度暴落したカード、", WHITE)], font(MPB, 64))
        runs(d, W / 2, 1650, [("今いくら？", YEL)], font(MPB, 76))
    elif i == 1:
        runs(d, W / 2, 770, [("サ終決定で", WHITE), ("暴落", RED)], font(DELA, 100))
        placeholder(d, (60, 940, 1020, 1660), "神龍の接写")
        runs(d, W / 2, 1600, [("「流通がかなり", WHITE), ("少ない", YEL), ("」", WHITE)], font(MPB, 70))
    else:
        runs(d, W / 2, 770, [("鑑定後", WHITE), ("100,000円", RED)], font(DELA, 104))
        placeholder(d, (60, 940, 1020, 1660), "PSA ケース入りの神龍")
        runs(d, W / 2, 1600, [("V字回復", YEL)], font(DELA, 96))
    ui(d); return im

# ---- 型B 吹き出し(映像全面・暗め)
def bubble(d, box, tail):
    d.rounded_rectangle(box, 40, fill=WHITE, outline=BLK, width=10)
    d.polygon(tail, fill=WHITE, outline=BLK)
    d.line(tail[:2], fill=WHITE, width=14)

def B(i):
    im, d = frame()
    placeholder(d, (0, 0, W, H), "元動画 全面(明るさ −20%)|手元とカード", dark=50)
    bf = font(DELA, 92)
    if i == 0:
        bubble(d, (80, 260, 1000, 560), [(380, 552), (560, 552), (430, 700)])
        d.text((540, 410), "仕入れ35,000円", font=bf, fill=BLK, anchor="mm")
        d.text((540, 410), "仕入れ", font=bf, fill=BLK, anchor="rm") if False else None
    elif i == 1:
        bubble(d, (80, 260, 1000, 640), [(380, 632), (560, 632), (430, 780)])
        d.text((540, 380), "流通がかなり", font=bf, fill=BLK, anchor="mm")
        d.text((540, 520), "少ない", font=font(DELA, 120), fill=RED, anchor="mm")
    else:
        bubble(d, (80, 260, 1000, 640), [(380, 632), (560, 632), (430, 780)])
        d.text((540, 380), "鑑定後", font=bf, fill=BLK, anchor="mm")
        d.text((540, 520), "100,000円", font=font(DELA, 120), fill=RED, anchor="mm")
    ui(d); return im

# ---- 型C サムネ特化(1コマ目=サムネ)
def C(i):
    im, d = frame()
    d.rectangle((0, 0, W, H), fill=(40, 34, 30))
    if i == 0:
        d.rectangle((40, 380, 620, 1340), fill=WHITE)
        placeholder(d, (58, 398, 602, 1322), "神龍の接写|(白フチ)")
        f = font(DELA, 96)
        text3(d, (790, 700), "サ終で", f, WHITE); text3(d, (790, 850), "暴落", font(DELA, 120), RED)
        text3(d, (790, 1030), "↓", f, WHITE); text3(d, (790, 1200), "10万円", f, YEL)
    elif i == 1:
        placeholder(d, (0, 300, W, 1500), "元動画 32:xx|鑑定ケースを見せる所")
        runs(d, W / 2, 1600, [("「一生価値が", WHITE), ("上がり続ける", YEL), ("」", WHITE)], font(MPB, 62))
    else:
        d.rectangle((40, 380, 620, 1340), fill=WHITE)
        placeholder(d, (58, 398, 602, 1322), "PSA ケース")
        f = font(DELA, 90)
        text3(d, (790, 760), "仕入れ", f, WHITE); text3(d, (790, 900), "3.5万", f, YEL)
        text3(d, (790, 1100), "鑑定後", f, WHITE); text3(d, (790, 1240), "10万", font(DELA, 110), RED)
    ui(d); return im

TYPES = [("型A 上下分割", A, ["0.0-1.5秒 1コマ目に金額(4.95-1)。問いは案", "約1.5-6秒 字幕「サ終決定で暴落」+声", "最後 結果を赤で1つだけ"]),
         ("型B 吹き出し", B, ["0.0-1.5秒 吹き出しに金額", "約1.5-6秒 声を吹き出しに・要点だけ赤", "最後 結果を吹き出しで"]),
         ("型C サムネ特化", C, ["0.0-1.0秒 左カード+右2行(サムネ)", "中盤 全面の映像+声の字幕", "最後 3.5万→10万(A→Bは4.7で弱い)"])]
PW, PH, NOTE = 300, 533, 120
out = Image.new("RGB", (180 + 3 * (PW + 20) + 20, 110 + 3 * (PH + NOTE + 20)), WHITE)
od = ImageDraw.Draw(out)
od.text((20, 14), "3つの型の見比べ: ラストシークレット神龍 3.5万→10万(元動画 32:02〜34:32)", font=font(MPB, 26), fill=BLK)
od.text((20, 50), "灰色の枠=元動画のコマに置き換える所 / 水色の枠=Shorts の UI(文字を置かない)", font=font(MPB, 22), fill=(60, 60, 60))
for r, (name, fn, notes) in enumerate(TYPES):
    y = 110 + r * (PH + NOTE + 20)
    od.text((20, y + PH / 2), name.replace(" ", "\n"), font=font(DELA, 30), fill=BLK, anchor="lm")
    for c in range(3):
        x = 180 + c * (PW + 20)
        im = fn(c).resize((PW, PH), Image.LANCZOS)
        out.paste(im, (x, y))
        for k, ln in enumerate([notes[c][j:j + 13] for j in range(0, len(notes[c]), 13)]):
            od.text((x, y + PH + 8 + k * 30), ln, font=font(MPB, 22), fill=(200, 30, 30))
out.save(sys.argv[1])
print(out.size)
