# Shorts デザインの追加5案(16〜20)。ミュウツー 2,000円→PSA9 の同じ場面。素材は元動画のコマ、文字は台本と字幕の事実だけ。
#   python3 briefs/design5d_mewtwo.py <src.mp4> <out.png>
import sys, os
sys.path.insert(0, "."); sys.path.insert(0, "briefs")
from PIL import Image, ImageDraw, ImageFont
import storyboard_variants as sv
from design5_mewtwo import W, H, WHITE, YEL, RED, GRN, BLK, T, blurbg, band, card, ui, grab, HOOK, RES, C_HOOK, C_RES  # noqa: E402
MIN = lambda s: ImageFont.truetype(os.path.join("fonts", "ShipporiMincho-ExtraBold.ttf"), s)
PRE = grab(866.6)
designs = []

# 16 時系列(左に縦の線。2年前に2,000円→提出→鑑定→結果。どこまで来たかが光る)
def d16(fr, step, last):
    img = blurbg(fr); d = ImageDraw.Draw(img); band(img, fr, 160)
    steps = [("2年前", "2,000円で購入"), ("提出", "PSA鑑定へ"), ("返却", "ラベルは…"), ("結果", last)]
    x = 150; d.line((x, 900, x, 1600), fill=(200, 200, 200), width=10)
    for i, (a, b) in enumerate(steps):
        y = 900 + i * 230; on = i <= step
        d.ellipse((x - 40, y - 40, x + 40, y + 40), fill=RED if i == step else (WHITE if on else (90, 90, 90)))
        d.text((x + 80, y - 30), a, font=sv.font("black", 44), fill=WHITE if on else (130, 130, 130), anchor="lm")
        T(d, (x + 80 + 330, y + 35), b, 64 if on else 48, YEL if i == step else (WHITE if on else (130, 130, 130)), stroke=6, maxw=640)
    return img
designs.append(("16 時系列", "左に縦の線。2年前の2,000円→提出→返却→結果。今どこかが光る", d16(PRE, 2, "？"), d16(RES, 3, "PSA 9・16万円")))

# 17 新聞・雑誌の見出し風(明朝の大見出し+小見出し。紙の質感)
def d17(fr, big, small):
    img = Image.new("RGB", (W, H), (238, 232, 218)); d = ImageDraw.Draw(img)
    d.line((60, 120, 1020, 120), fill=BLK, width=6); d.line((60, 135, 1020, 135), fill=BLK, width=2)
    d.text((60, 170), "トレカ鑑定 2026年", font=MIN(40), fill=(60, 60, 60))
    f = 150
    while d.textlength(big, font=MIN(f)) > 960: f -= 6
    d.text((W / 2, 340), big, font=MIN(f), fill=BLK, anchor="mm")
    d.text((W / 2, 480), small, font=MIN(56), fill=(150, 20, 20), anchor="mm")
    g = fr.convert("L").convert("RGB").resize((W - 120, (W - 120) * 9 // 16)); img.paste(g, (60, 580))
    d.rectangle((60, 580, W - 60, 580 + (W - 120) * 9 // 16), outline=BLK, width=4)
    d.text((60, 1150), "▲ 2年前に2,000円で買った拡張シートのミュウツー", font=MIN(36), fill=(60, 60, 60))
    return img
designs.append(("17 新聞の見出し風", "明朝の大見出し+写真(白黒)。他の Shorts と見た目が全く違うので目に留まる", d17(HOOK, "PSA10なら二百万!?", "拡張シートのミュウツー、鑑定へ"), d17(RES, "結果はPSA 9", "二千円が十六万円に 「10は幻」")))

# 18 ゲームのステータス画面(価値 Lv が上がる)
def d18(fr, cb, val, lv, up):
    img = Image.new("RGB", (W, H), (16, 20, 48)); d = ImageDraw.Draw(img)
    d.rounded_rectangle((40, 120, 1040, 1700), radius=30, outline=WHITE, width=8)
    c = card(fr, cb).resize((360, 680)); img.paste(c, (90, 200)); d.rectangle((90, 200, 450, 880), outline=WHITE, width=6)
    rows = [("なまえ", "ミュウツー"), ("しゅるい", "拡張シート"), ("しいれ", "2,000円"), ("かち", val)]
    for i, (a, b) in enumerate(rows):
        d.text((500, 260 + i * 150), a, font=sv.font("black", 44), fill=(170, 190, 255)); d.text((520, 320 + i * 150), b, font=sv.font("dela", 60), fill=YEL if i == 3 else WHITE)
    d.rectangle((90, 1000, 990, 1080), outline=WHITE, width=6); d.rectangle((96, 1006, 96 + int(888 * lv), 1074), fill=GRN if lv < 0.9 else RED)
    d.text((90, 960), "PSA", font=sv.font("black", 40), fill=WHITE)
    if up: T(d, (W / 2, 1300), up, 110, YEL)
    return img
designs.append(("18 ステータス画面", "ゲームの能力表。価値の数字とゲージが上がり「レベルアップ」で結果", d18(HOOK, C_HOOK, "？？？", 0.3, ""), d18(RES, C_RES, "160,000円", 0.9, "PSA 9 にレベルアップ!")))

# 19 ノートに手書き(写真をテープで貼り、赤ペンで丸と矢印)
def d19(fr, note, circle):
    img = Image.new("RGB", (W, H), (250, 250, 245)); d = ImageDraw.Draw(img)
    for y in range(160, H, 80): d.line((0, y, W, y), fill=(200, 220, 240), width=2)
    d.line((120, 0, 120, H), fill=(240, 160, 160), width=3)
    ph = fr.resize((860, 484)).rotate(-3, expand=True, fillcolor=(250, 250, 245)); img.paste(ph, (130, 250))
    d.rectangle((420, 225, 620, 285), fill=(240, 230, 150))
    if circle: d.ellipse(circle, outline=(220, 30, 30), width=10)
    y = 900
    for s in note:
        d.text((180, y), s, font=sv.font("black", 72), fill=(30, 50, 140) if not s.startswith("→") else (220, 30, 30)); y += 130
    return img
designs.append(("19 ノートに手書き", "写真をテープで貼り、ペンで丸・矢印・メモ。研究ノートのような手作り感", d19(HOOK, ["拡張シートのミュウツー", "仕入れ 2,000円", "→ PSA10なら200万!?"], None), d19(RES, ["仕入れ 2,000円", "→ PSA 9", "→ 16万円(80倍)"], (300, 270, 620, 720))))

# 20 ミニマル(黒い背景に1語だけ特大。映像は小さく下に)
def d20(fr, word, sub, col):
    img = Image.new("RGB", (W, H), (8, 8, 8)); d = ImageDraw.Draw(img)
    f = 300
    while d.textlength(word, font=sv.font("dela", f)) > 960: f -= 10
    d.text((W / 2, 600), word, font=sv.font("dela", f), fill=col, anchor="mm")
    d.text((W / 2, 860), sub, font=sv.font("black", 56), fill=(200, 200, 200), anchor="mm")
    img.paste(fr.resize((720, 405)), (180, 1020))
    return img
designs.append(("20 ミニマル", "黒地に1語だけ特大。言葉が拍で切り替わる。映像は小さく下に", d20(HOOK, "200万?", "PSA10なら", WHITE), d20(RES, "9", "PSA 9 ・ 16万円", RED)))

for _, _, a, b in designs:
    for im in (a, b): ui(ImageDraw.Draw(im))
PW, PH = 300, 533
out = Image.new("RGB", (40 + len(designs) * (2 * PW + 60), PH + 330), WHITE); od = ImageDraw.Draw(out)
od.text((20, 14), "Shorts デザイン 追加5案(16〜20)・左=冒頭 右=結果・水色=Shorts の UI", font=sv.font("black", 30), fill=BLK)
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
