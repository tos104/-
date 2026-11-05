# Shorts デザインの追加5案(11〜15)。ミュウツー 2,000円→PSA9 の同じ場面。素材は元動画のコマ、文字は台本と字幕の事実だけ。
#   python3 briefs/design5c_mewtwo.py <src.mp4> <out.png>
import sys, math
sys.path.insert(0, "."); sys.path.insert(0, "briefs")
from PIL import Image, ImageDraw
import storyboard_variants as sv
from design5_mewtwo import W, H, WHITE, YEL, RED, GRN, BLK, T, blurbg, band, card, ui, grab, HOOK, RES, C_HOOK, C_RES  # noqa: E402

SCRATCH = grab(830.0)  # 13:50 カードの裏の初期傷(本人が見せている所)
PRE = grab(866.6)  # 14:26 ラベルが見える前(答えの字幕が出ない)
designs = []

# 11 ビフォー/アフター(上=買った時 2,000円、下=鑑定後)
def d11(top_fr, bot_fr, top_lab, bot_lab, bot_val):
    img = Image.new("RGB", (W, H), (20, 20, 24)); d = ImageDraw.Draw(img)
    band(img, top_fr, 170); band(img, bot_fr, 960)
    T(d, (W / 2, 100), top_lab, 70, GRN)
    T(d, (W / 2, 880), bot_lab, 70, WHITE)
    T(d, (W / 2, 1650), bot_val, 110, RED)
    return img
designs.append(("11 ビフォー/アフター", "上=買った時(2,000円)、下=鑑定後。同じ画面で差を見せ続ける", d11(HOOK, PRE, "買った時 2,000円", "鑑定後は…", "？円"), d11(HOOK, RES, "買った時 2,000円", "PSA 9", "16万円")))

# 12 スロット(等級の数字が回って止まる)
def d12(fr, reel, stop):
    img = blurbg(fr); d = ImageDraw.Draw(img); band(img, fr, 200)
    d.rounded_rectangle((190, 1000, 890, 1500), radius=50, fill=(30, 30, 30), outline=YEL, width=14)
    for i, n in enumerate(reel):
        y = 1250 + (i - 1) * 170
        col = YEL if (stop and i == 1) else (110, 110, 110) if i != 1 else WHITE
        d.text((540, y), n, font=sv.font("dela", 150 if i == 1 else 90), fill=col, anchor="mm")
    d.polygon([(150, 1250), (200, 1220), (200, 1280)], fill=RED); d.polygon([(930, 1250), (880, 1220), (880, 1280)], fill=RED)
    T(d, (W / 2, 900), "PSA", 90, WHITE)
    return img
designs.append(("12 スロット", "等級の数字がドラムロールで回り、結果で止まる。答えの瞬間が一番動く", d12(HOOK, ["10", "8", "9"], False), d12(RES, ["8", "9", "10"], True)))

# 13 期待度メーター(本人の言葉で針が動く)
def d13(fr, ang, lab):
    img = blurbg(fr); d = ImageDraw.Draw(img); band(img, fr, 200)
    cx, cy, r = 540, 1500, 380
    for i, c in enumerate([(60, 200, 110), (255, 230, 0), (255, 140, 0), (255, 42, 42)]):
        d.pieslice((cx - r, cy - r, cx + r, cy + r), 180 + i * 45, 225 + i * 45, fill=c)
    d.pieslice((cx - r + 90, cy - r + 90, cx + r - 90, cy + r - 90), 180, 360, fill=(30, 30, 30))
    a = math.radians(180 + ang)
    d.line((cx, cy, cx + (r - 40) * math.cos(a), cy + (r - 40) * math.sin(a)), fill=WHITE, width=18)
    d.ellipse((cx - 30, cy - 30, cx + 30, cy + 30), fill=WHITE)
    T(d, (W / 2, 960), lab, 84, YEL)
    return img
designs.append(("13 期待度メーター", "針が「欠けも何一つない」で上がり、結果で止まる。タメの数秒を動かす", d13(HOOK, 150, "期待度 MAX!?"), d13(RES, 120, "PSA 9 = 16万円")))

# 14 速報テロップ(画面下の帯が流れる。報道機関の名前・ロゴは使わない)
def d14(fr, head, ticker):
    img = blurbg(fr); d = ImageDraw.Draw(img)
    c = fr.crop((60, 0, 580, 360)).resize((W, int(360 * W / 520))); img.paste(c, (0, 330))
    d.rectangle((0, 1140, W, 1300), fill=(200, 20, 30)); d.rectangle((0, 1140, 260, 1300), fill=WHITE)
    d.text((130, 1220), "結果", font=sv.font("dela", 70), fill=(200, 20, 30), anchor="mm")
    d.text((300, 1220), head, font=sv.font("dela", 70), fill=WHITE, anchor="lm")
    d.rectangle((0, 1300, W, 1390), fill=(20, 20, 20)); d.text((40, 1345), ticker, font=sv.font("black", 46), fill=YEL, anchor="lm")
    return img
designs.append(("14 速報テロップ", "下に赤い帯+流れる文字。「結果が出た」感。報道のロゴ・名前は使わない", d14(HOOK, "鑑定結果 まもなく", "仕入れ2,000円 / PSA10なら約200万円 / 拡張シートのミュウツー"), d14(RES, "PSA 9 確定", "鑑定後 160,000円 / 10は幻 / 残り47枚は関連動画")))

# 15 ルーペ拡大(傷の所を丸く拡大して「なぜ10が難しいか」を見せる)
def d15(fr, lab, box):
    img = blurbg(fr); d = ImageDraw.Draw(img); band(img, fr, 300)
    if box:
        z = fr.crop(box).resize((560, 560))
        m = Image.new("L", (560, 560), 0); ImageDraw.Draw(m).ellipse((0, 0, 560, 560), fill=255)
        img.paste(z, (260, 960), m); d.ellipse((260, 960, 820, 1520), outline=WHITE, width=16)
        d.line((780, 1480, 900, 1620), fill=WHITE, width=30)
    T(d, (W / 2, 200), lab, 84, YEL)
    return img
designs.append(("15 ルーペ拡大", "傷の所を丸く拡大(本人が見せている所)。なぜ10が難しいかを目で見せる", d15(SCRATCH, "ここが初期傷", (20, 110, 200, 290)), d15(RES, "PSA 9", None)))

for _, _, a, b in designs:
    for im in (a, b): ui(ImageDraw.Draw(im))
PW, PH = 300, 533
out = Image.new("RGB", (40 + len(designs) * (2 * PW + 60), PH + 330), WHITE); od = ImageDraw.Draw(out)
od.text((20, 14), "Shorts デザイン 追加5案(11〜15)・左=冒頭 右=結果・水色=Shorts の UI", font=sv.font("black", 30), fill=BLK)
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
