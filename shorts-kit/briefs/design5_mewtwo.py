# ミュウツー(2,000円→PSA9 16万円)の同じ場面で、Shorts のデザイン5案を並べる。素材は元動画のコマだけ、文字は台本と字幕の事実だけ。
#   python3 briefs/design5_mewtwo.py <src.mp4> <out.png>
import sys, subprocess, io
sys.path.insert(0, ".")
from PIL import Image, ImageDraw, ImageFilter
import storyboard_variants as sv
W, H = 1080, 1920
WHITE, YEL, RED, GRN, BLK = (255, 255, 255), (255, 230, 0), (255, 42, 42), (60, 200, 110), (0, 0, 0)
src = sys.argv[1]
def grab(t):
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-ss", str(t), "-i", src, "-frames:v", "1", "-f", "image2pipe", "-vcodec", "png", "-"], capture_output=True).stdout
    return Image.open(io.BytesIO(raw)).convert("RGB")
def T(d, xy, s, size, fill, kind="dela", stroke=9, maxw=1000):
    while size > 30 and d.textlength(s, font=sv.font(kind, size)) > maxw: size -= 4
    x, y = xy
    d.text((x + 7, y + 9), s, font=sv.font(kind, size), fill=BLK, anchor="mm", stroke_width=stroke, stroke_fill=BLK)
    d.text((x, y), s, font=sv.font(kind, size), fill=fill, anchor="mm", stroke_width=stroke, stroke_fill=BLK)
def blurbg(fr):
    return fr.resize((W, H)).filter(ImageFilter.GaussianBlur(28)).point(lambda v: v * 0.45)
def band(img, fr, y):  # 横幅いっぱい(拡大なし相当)
    img.paste(fr.resize((W, W * 9 // 16)), (0, y))
def card(fr, box):  # 元動画の中のカード部分
    return fr.crop(box)
def ui(d):
    d.rectangle((960, 1080, W, 1720), outline=(80, 200, 255), width=3); d.rectangle((0, 1720, W, H), outline=(80, 200, 255), width=3)

HOOK, RES = grab(786.0), grab(876.5)
C_HOOK, C_RES = (135, 40, 330, 360), (165, 0, 375, 330)
designs = []

# 1 カード大写し+スタンプ(自チャンネルの当たり 約2万再生: カードが画面の主役・倍率の連打)
def d1(fr, cb, top, stamp, sc):
    img = blurbg(fr); d = ImageDraw.Draw(img)
    c = card(fr, cb); k = 1000 / c.height; c = c.resize((int(c.width * k), 1000)); img.paste(c, ((W - c.width) // 2, 420))
    T(d, (W / 2, 250), top, 96, WHITE)
    if stamp:
        d.rounded_rectangle((560, 1180, 1000, 1400), radius=40, fill=sc); T(d, (780, 1290), stamp, 120, WHITE, stroke=6)
    return img
designs.append(("1 カード大写し+スタンプ", "自チャンネルの当たり(約2万再生)の型。カードを主役に、答えは判子で", d1(HOOK, C_HOOK, "PSA10なら200万!?", "？", (110, 40, 140)), d1(RES, C_RES, "仕入れ2,000円が", "80倍", RED)))

# 2 3段+レシート(今の型・実験ログで伸びた)
def d2(fr, l1, l2, rows, tot):
    img = blurbg(fr); d = ImageDraw.Draw(img)
    T(d, (W / 2, 140), l1, 62, WHITE, "black"); T(d, (W / 2, 245), l2, 96, YEL)
    band(img, fr, 330)
    d.rectangle((150, 990, 930, 1480), fill=(252, 251, 246))
    for i, (a, v, c) in enumerate(rows):
        d.text((190, 1080 + i * 90), a, font=sv.font("xb", 44), fill=(40, 40, 40), anchor="lm"); d.text((890, 1080 + i * 90), v, font=sv.font("dela", 52), fill=c, anchor="rm")
    d.line((180, 1340, 900, 1340), fill=(40, 40, 40), width=4)
    d.text((190, 1410), "鑑定後", font=sv.font("dela", 52), fill=(40, 40, 40), anchor="lm"); d.text((890, 1410), tot, font=sv.font("dela", 64), fill=(200, 40, 50), anchor="rm")
    return img
R0 = [("仕入れ", "2,000円", (90, 120, 100)), ("PSA10なら", "約200万円", (200, 40, 50)), ("鑑定結果", "？", (200, 40, 50))]
R1 = R0[:2] + [("鑑定結果", "PSA 9", (200, 40, 50))]
designs.append(("2 3段+レシート", "今の型。上=問い、中=元動画、下=金額の表。伸びた型の延長", d2(HOOK, "昔のカード", "PSA10なら200万!?", R0, "？円"), d2(RES, "", "PSA 9", R1, "160,000円")))

# 3 吹き出し(映像を大きく・本人の言葉を吹き出しで)
def d3(fr, bubble, cap):
    img = blurbg(fr); d = ImageDraw.Draw(img)
    c = fr.crop((60, 0, 580, 360)); c = c.resize((W, int(360 * W / 520))); img.paste(c, (0, 420))
    d.rounded_rectangle((90, 190, 990, 380), radius=60, fill=WHITE, outline=BLK, width=8)
    d.polygon([(420, 375), (520, 375), (470, 450)], fill=WHITE, outline=BLK); d.line((424, 377, 516, 377), fill=WHITE, width=10)
    d.text((W / 2, 285), bubble, font=sv.font("black", 64), fill=BLK, anchor="mm")
    T(d, (W / 2, 1300), cap, 92, YEL)
    return img
designs.append(("3 吹き出し", "映像を大きく。本人の言葉を吹き出しに。字幕と同時に出さない", d3(HOOK, "「10取れたら200万とか」", "拡張シートのミュウツー"), d3(RES, "「10は幻なんで」", "PSA 9 → 16万円")))

# 4 サムネ特化(型C・書き出し済み)
def d4(fr, cb, lines):
    img = Image.new("RGB", (W, H), (40, 34, 30)); d = ImageDraw.Draw(img)
    d.rectangle((30, 440, 530, 1360), fill=WHITE); img.paste(card(fr, cb).resize((468, 888)), (46, 456))
    y = 900 - (len(lines) - 1) * 75
    for s, c, z in lines: T(d, (745, y), s, z, c, maxw=360); y += 150
    return img
designs.append(("4 サムネ特化(型C)", "1コマ目がそのままサムネ。左カード+右の短い行", d4(HOOK, C_HOOK, [("昔の", WHITE, 120), ("カード", WHITE, 120), ("PSA10", WHITE, 120), ("なら", WHITE, 100), ("200万!?", RED, 130)]), d4(RES, C_RES, [("仕入れ", WHITE, 90), ("2,000円", GRN, 90), ("鑑定後", WHITE, 90), ("16万円", RED, 120)])))

# 5 値段の物差し(縦の棒で 2,000円 / 16万 / 200万 の差を見せる)
def d5(fr, now, label):
    img = blurbg(fr); d = ImageDraw.Draw(img)
    band(img, fr, 240)
    import math
    vals = [("仕入れ", 2000, GRN), ("PSA9", 160000, YEL), ("PSA10", 2000000, RED)]
    base, top = 1620, 1080
    for i, (a, v, c) in enumerate(vals):
        h = (math.log10(v) - 3) / (math.log10(2e6) - 3) * (base - top - 80) + 80
        x = 180 + i * 260
        on = i <= now
        d.rectangle((x, base - h, x + 180, base), fill=c if on else (90, 90, 90))
        d.text((x + 90, base + 50), a, font=sv.font("black", 46), fill=WHITE, anchor="mm")
        T(d, (x + 90, base - h - 50), ["2,000円", "16万円", "200万円"][i] if (on or i == 2) else "？", 60, WHITE, stroke=6)
    T(d, (W / 2, 930), label, 80, YEL)
    return img
designs.append(("5 値段の物差し", "金額の差を棒で見せる(対数)。答えの棒は結果で色が付く", d5(HOOK, 0, "PSA10なら200万!?"), d5(RES, 1, "PSA 9 = 16万円")))

for _, _, a, b in designs:
    for im in (a, b): ui(ImageDraw.Draw(im))
PW, PH = 300, 533
out = Image.new("RGB", (40 + len(designs) * (2 * PW + 60), PH + 330), WHITE); od = ImageDraw.Draw(out)
od.text((20, 14), "Shorts デザイン5案(ミュウツー 2,000円→PSA9 の同じ場面・左=冒頭 右=結果・水色=Shorts の UI)", font=sv.font("black", 30), fill=BLK)
for k, (name, note, a, b) in enumerate(designs):
    x = 20 + k * (2 * PW + 60)
    out.paste(a.resize((PW, PH)), (x, 80)); out.paste(b.resize((PW, PH)), (x + PW + 10, 80))
    od.text((x, PH + 100), name, font=sv.font("dela", 36), fill=(200, 30, 30))
    line, yy = "", PH + 155
    for ch in note:
        if od.textlength(line + ch, font=sv.font("bold", 24)) > 2 * PW: od.text((x, yy), line, font=sv.font("bold", 24), fill=(60, 60, 60)); yy += 32; line = ch
        else: line += ch
    od.text((x, yy), line, font=sv.font("bold", 24), fill=(60, 60, 60))
out.save(sys.argv[2]); print(out.size)
