# Shorts デザイン5案(26〜30)。元動画は拡大しない(横幅いっぱい=今の3段と同じ大きさまで)。素材は元動画のコマ、文字は台本と字幕の事実だけ。
#   python3 briefs/design5f_mewtwo.py <src.mp4> <out.png>
import sys, subprocess, io
sys.path.insert(0, ".")
from PIL import Image, ImageDraw, ImageFilter
import storyboard_variants as sv
W, H = 1080, 1920
WH, YE, RE, BK, GR = (255, 255, 255), (255, 230, 0), (255, 42, 42), (0, 0, 0), (60, 200, 110)
src = sys.argv[1]
def grab(t):
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-ss", str(t), "-i", src, "-frames:v", "1", "-f", "image2pipe", "-vcodec", "png", "-"], capture_output=True).stdout
    return Image.open(io.BytesIO(raw)).convert("RGB")
HOOK, TAME, RES = grab(786.0), grab(846.0), grab(869.0)
BW, BH = W, W * 9 // 16
band = lambda fr, w=BW: fr.resize((w, w * 9 // 16), Image.LANCZOS)
T = sv.thick
def blurbg(fr): return fr.resize((W, H)).filter(ImageFilter.GaussianBlur(28)).point(lambda v: v * 0.4)
designs = []

# 26 電光掲示板: 下に黒い掲示板。仕入れと鑑定後の数字が1桁ずつ回って止まる
def board(fr, top, rows):
    im = blurbg(fr); d = ImageDraw.Draw(im); T(d, (W / 2, 150), top, 100, YE); im.paste(band(fr), (0, 260))
    d.rectangle((40, 940, 1040, 1600), fill=(15, 15, 15), outline=(90, 90, 90), width=8)
    for i, (a, v, c) in enumerate(rows):
        y = 1040 + i * 190; d.text((90, y), a, font=sv.font("black", 52), fill=(200, 200, 200), anchor="lm")
        for k, ch in enumerate(v.rjust(9)):
            x = 1000 - (9 - k) * 66; d.rectangle((x, y - 60, x + 58, y + 60), fill=(35, 35, 35)); d.text((x + 29, y), ch, font=sv.font("dela", 76), fill=c, anchor="mm")
    return im
designs.append(("26 電光掲示板", "下に黒い掲示板。数字が1桁ずつ回って止まる(パタパタ)。答えの「？」が最後に止まる",
    board(TAME, "鑑定後の値段は…", [("仕入れ", "2,000円", GR), ("PSA", "?", YE), ("鑑定後", "?円", RE)]),
    board(RES, "PSA 9", [("仕入れ", "2,000円", GR), ("PSA", "9", YE), ("鑑定後", "160,000円", RE)])))

# 27 ポラロイド: 映像をインスタント写真の枠に入れ、コルクボードにピン留め。下の余白に手書き風メモ
def polaroid(fr, memo, memo_c, tilt):
    im = Image.new("RGB", (W, H), (176, 128, 80)); d = ImageDraw.Draw(im)
    for i in range(0, H, 9): d.line((0, i, W, i + 4), fill=(168, 120, 74), width=2)
    pw = 960; ph = pw * 9 // 16
    card = Image.new("RGB", (pw + 60, ph + 260), (250, 250, 248)); card.paste(band(fr, pw), (30, 30))
    cd = ImageDraw.Draw(card); cd.text(((pw + 60) / 2, ph + 140), memo, font=sv.font("black", 80), fill=memo_c, anchor="mm")
    card = card.rotate(tilt, expand=True, fillcolor=(176, 128, 80)); im.paste(card, ((W - card.width) // 2, 420))
    d.ellipse((W / 2 - 26, 390, W / 2 + 26, 442), fill=RE)
    T(d, (W / 2, 220), "2,000円で買ったミュウツー", 76, WH, stroke=8); return im
designs.append(("27 ポラロイド", "映像を写真の枠に入れてボードにピン留め。下の余白に一言メモ。結果で写真が差し替わる",
    polaroid(HOOK, "PSA10なら200万!?", (30, 50, 140), 2), polaroid(RES, "PSA 9 → 16万円", (200, 30, 30), -2)))

# 28 テレビ枠: 映像を角の丸いテレビ画面に。下に字幕のテロップ板(ブランドは描かない)
def tv(fr, cap, cap_c, top):
    im = Image.new("RGB", (W, H), (24, 22, 30)); d = ImageDraw.Draw(im)
    d.rounded_rectangle((20, 360, 1060, 1140), radius=70, fill=(60, 50, 40), outline=(20, 20, 20), width=10)
    im.paste(band(fr, 940), (70, 410)); d.rounded_rectangle((70, 410, 1010, 939), radius=30, outline=(10, 10, 10), width=14)
    for k in range(3): d.ellipse((150 + k * 120, 1000, 220 + k * 120, 1070), fill=(30, 30, 30))
    T(d, (W / 2, 220), top, 100, YE)
    d.rectangle((0, 1240, W, 1460), fill=(250, 250, 250)); d.text((W / 2, 1350), cap, font=sv.font("dela", 96), fill=cap_c, anchor="mm"); return im
designs.append(("28 テレビ枠", "映像をテレビ画面に入れ、下に白いテロップ板。「番組を見ている」感じで集中させる",
    tv(HOOK, "PSA10なら200万!?", RE, "拡張シートのミュウツー"), tv(RES, "PSA 9 ＝ 16万円", RE, "鑑定結果")))

# 29 付箋: 映像のまわりに付箋を貼っていく(事実を1枚ずつ)。結果で赤い付箋
def sticky(fr, notes):
    im = blurbg(fr); d = ImageDraw.Draw(im); im.paste(band(fr), (0, 300))
    for x, y, s, c, r in notes:
        n = Image.new("RGBA", (440, 300), c); nd = ImageDraw.Draw(n)
        f = 64
        while nd.textlength(s, font=sv.font("black", f)) > 390: f -= 4
        nd.text((220, 150), s, font=sv.font("black", f), fill=BK, anchor="mm")
        n = n.rotate(r, expand=True); im.paste(n, (x, y), n)
    return im
designs.append(("29 付箋", "映像の下に事実の付箋を1枚ずつ貼る。結果は赤い付箋",
    sticky(TAME, [(60, 980, "2,000円で購入", (255, 240, 120), 4), (560, 1000, "PSA10なら200万", (180, 230, 255), -3), (300, 1310, "結果は…?", (255, 200, 220), 2)]),
    sticky(RES, [(60, 980, "2,000円で購入", (255, 240, 120), 4), (560, 1000, "PSA10なら200万", (180, 230, 255), -3), (250, 1310, "PSA 9 = 16万円", (255, 110, 110), 2)])))

# 30 電卓: 下に電卓の表示。2,000 × ？ ＝ … → 2,000 × 80 ＝ 160,000
def calc(fr, top, expr, ans, ans_c):
    im = blurbg(fr); d = ImageDraw.Draw(im); T(d, (W / 2, 150), top, 100, YE); im.paste(band(fr), (0, 260))
    d.rounded_rectangle((90, 940, 990, 1620), radius=50, fill=(40, 42, 48), outline=(20, 20, 20), width=8)
    d.rounded_rectangle((140, 990, 940, 1330), radius=20, fill=(190, 205, 170))
    d.text((900, 1080), expr, font=sv.font("dela", 70), fill=(40, 50, 40), anchor="rm"); d.text((900, 1240), ans, font=sv.font("dela", 120), fill=ans_c, anchor="rm")
    for k, s in enumerate(["×", "＝", "AC", "÷"]):
        d.rounded_rectangle((150 + k * 200, 1400, 310 + k * 200, 1560), radius=30, fill=(230, 120, 40) if s in "×＝" else (90, 92, 100)); d.text((230 + k * 200, 1480), s, font=sv.font("black", 64), fill=WH, anchor="mm")
    return im
designs.append(("30 電卓", "下に電卓。2,000 × ？ を計算して、答えで 160,000 と 80倍 が出る",
    calc(TAME, "2,000円が何倍に?", "2,000 × ？", "＝ ？", (40, 50, 40)), calc(RES, "PSA 9", "2,000 × 80", "160,000", (180, 20, 20))))

for _, _, *ims in designs:
    for im in ims:
        d = ImageDraw.Draw(im); d.rectangle((960, 1080, W, 1720), outline=(80, 200, 255), width=3); d.rectangle((0, 1720, W, H), outline=(80, 200, 255), width=3)
PW, PH = 300, 533
out = Image.new("RGB", (40 + len(designs) * (2 * PW + 60), PH + 300), WH); od = ImageDraw.Draw(out)
od.text((20, 14), "Shorts デザイン5案(26〜30)・元動画は拡大しない・左=冒頭/タメ 右=結果・水色=Shorts の UI", font=sv.font("black", 30), fill=BK)
for k, (name, note, *ims) in enumerate(designs):
    x = 20 + k * (2 * PW + 60)
    for j, im in enumerate(ims): out.paste(im.convert("RGB").resize((PW, PH), Image.LANCZOS), (x + j * (PW + 10), 80))
    od.text((x, PH + 100), name, font=sv.font("dela", 36), fill=(200, 30, 30))
    line, yy = "", PH + 155
    for ch in note:
        if od.textlength(line + ch, font=sv.font("bold", 24)) > 2 * PW: od.text((x, yy), line, font=sv.font("bold", 24), fill=(60, 60, 60)); yy += 32; line = ch
        else: line += ch
    od.text((x, yy), line, font=sv.font("bold", 24), fill=(60, 60, 60))
out.save(sys.argv[2]); print(out.size)
