# Shorts デザインの追加5案(6〜10)。ミュウツー 2,000円→PSA9 の同じ場面。素材は元動画のコマ、文字は台本と字幕の事実だけ。
#   python3 briefs/design5b_mewtwo.py <src.mp4> <out.png>
import sys
sys.path.insert(0, "."); sys.path.insert(0, "briefs")
from PIL import Image, ImageDraw
import storyboard_variants as sv
from design5_mewtwo import W, H, WHITE, YEL, RED, GRN, BLK, T, blurbg, band, card, ui, HOOK, RES, C_HOOK, C_RES  # noqa: E402

designs = []

# 6 全画面+カラオケ字幕(声に合わせて今の語だけ黄色)
def d6(fr, words, hi, top):
    img = blurbg(fr); d = ImageDraw.Draw(img)
    c = fr.crop((90, 0, 450, 360)); c = c.resize((W, W)); img.paste(c, (0, 300))
    T(d, (W / 2, 190), top, 70, WHITE, "black")
    x = 80; f = sv.font("dela", 84)
    tot = sum(d.textlength(w, font=f) for w in words); x = (W - tot) / 2
    for i, w in enumerate(words):
        wl = d.textlength(w, font=f)
        T(d, (x + wl / 2, 1500), w, 84, YEL if i == hi else WHITE, stroke=9, maxw=2000); x += wl
    return img
designs.append(("6 全画面+カラオケ字幕", "映像を縦いっぱい。声に合わせて今の語だけ黄色。音なしでも追える", d6(HOOK, ["10取れたら", "200万", "とか"], 1, "拡張シートのミュウツー"), d6(RES, ["素晴らしい、", "9点", "ですね"], 1, "PSA鑑定の結果")))

# 7 クイズ3択(見る人に予想させる → 正解が光る)
def d7(fr, ans):
    img = blurbg(fr); d = ImageDraw.Draw(img)
    T(d, (W / 2, 150), "何点だった？", 96, WHITE); band(img, fr, 260)
    for i, s in enumerate(["PSA 8", "PSA 9", "PSA 10"]):
        y = 980 + i * 190; on = ans is not None and s == ans
        d.rounded_rectangle((140, y, 900, y + 150), radius=40, fill=(255, 230, 0) if on else (255, 255, 255), outline=BLK, width=8)
        d.text((520, y + 75), s, font=sv.font("dela", 80), fill=BLK, anchor="mm")
        if ans is not None and not on: d.rounded_rectangle((140, y, 900, y + 150), radius=40, fill=None, outline=(120, 120, 120), width=8)
    return img
designs.append(("7 クイズ3択", "答えの前に3択を出して予想させる。コメント「9だと思った」を誘う", d7(HOOK, None), d7(RES, "PSA 9")))

# 8 進行バー+章(今どこか・あと何秒で答えかを見せる)
def d8(fr, step, l2):
    img = blurbg(fr); d = ImageDraw.Draw(img)
    names = ["カード", "なぜ高い", "タメ", "結果"]
    for i, n in enumerate(names):
        x = 60 + i * 245; on = i <= step
        d.rounded_rectangle((x, 90, x + 225, 160), radius=30, fill=(255, 42, 42) if i == step else ((255, 255, 255) if on else (80, 80, 80)))
        d.text((x + 112, 125), n, font=sv.font("black", 40), fill=WHITE if i == step else BLK, anchor="mm")
    T(d, (W / 2, 260), l2, 96, YEL); band(img, fr, 360)
    return img
designs.append(("8 進行バー+章", "上に4つの章。今どこか・答えまであと少しかが分かり、途中で抜けにくい", d8(HOOK, 0, "PSA10なら200万!?"), d8(RES, 3, "PSA 9")))

# 9 チャット風(本人の言葉をトークの吹き出しで積む)
def d9(fr, msgs):
    img = blurbg(fr); d = ImageDraw.Draw(img); band(img, fr, 160)
    y = 860
    for who, s in msgs:
        f = sv.font("black", 52); tw = d.textlength(s, font=f)
        if who == "me":
            d.rounded_rectangle((W - 120 - tw - 60, y, W - 120, y + 110), radius=50, fill=(120, 230, 120)); d.text((W - 150 - tw, y + 55), s, font=f, fill=BLK, anchor="lm")
        else:
            d.rounded_rectangle((90, y, 90 + tw + 60, y + 110), radius=50, fill=WHITE); d.text((120, y + 55), s, font=f, fill=BLK, anchor="lm")
        y += 150
    return img
designs.append(("9 チャット風", "本人の言葉をトークの吹き出しで積む。字幕より会話っぽく読める", d9(HOOK, [("me", "2,000円で買いました"), ("me", "10取れたら200万とか"), ("you", "結果は…？")]), d9(RES, [("me", "せーの"), ("me", "素晴らしい、9点ですね"), ("me", "10は幻なんで")])))

# 10 鑑定ラベル風の枠(画面上部をラベルに見立て、等級の欄が ？→9)
def d10(fr, cb, grade, price):
    img = Image.new("RGB", (W, H), (245, 245, 245)); d = ImageDraw.Draw(img)
    d.rectangle((40, 120, 1040, 420), fill=WHITE, outline=(200, 30, 40), width=14)
    d.text((90, 200), "MEWTWO / 拡張シート", font=sv.font("black", 50), fill=BLK, anchor="lm")
    d.text((90, 290), "仕入れ 2,000円", font=sv.font("black", 50), fill=(60, 120, 80), anchor="lm")
    d.text((90, 370), price, font=sv.font("dela", 50), fill=(200, 30, 40), anchor="lm")
    d.rectangle((760, 160, 1000, 380), fill=(200, 30, 40)); d.text((880, 270), grade, font=sv.font("dela", 150), fill=WHITE, anchor="mm")
    c = card(fr, cb); k = 1180 / c.height; c = c.resize((int(c.width * k), 1180))
    d.rectangle(((W - c.width) // 2 - 16, 460, (W + c.width) // 2 + 16, 1660), fill=(200, 200, 205)); img.paste(c, ((W - c.width) // 2, 470))
    return img
designs.append(("10 鑑定ラベル風の枠", "画面全体を鑑定ケースに見立てる。等級の欄が ？ → 9 に変わる(ロゴは使わない)", d10(HOOK, C_HOOK, "？", "PSA10なら 約200万円"), d10(RES, C_RES, "9", "鑑定後 160,000円")))

for _, _, a, b in designs:
    for im in (a, b): ui(ImageDraw.Draw(im))
PW, PH = 300, 533
out = Image.new("RGB", (40 + len(designs) * (2 * PW + 60), PH + 330), WHITE); od = ImageDraw.Draw(out)
od.text((20, 14), "Shorts デザイン 追加5案(6〜10)・左=冒頭 右=結果・水色=Shorts の UI", font=sv.font("black", 30), fill=BLK)
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
