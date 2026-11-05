# ミュウツー(scripts/mewtwo_psa.json の v3・6カット)を型C(サムネ特化)で組んだ絵コンテ。
# 文字は台本の copy / rows / total / cta をそのまま使う(作らない)。素材は灰色の枠(元動画のコマに置き換える)。
import json, sys
from PIL import Image, ImageDraw, ImageFont
F = "/home/user/-/shorts-kit/fonts/"
DELA, MPB = F + "DelaGothicOne-Regular.ttf", F + "MPLUSRounded1c-Black.ttf"
W, H = 1080, 1920
WHITE, YEL, RED, GRN, BLK = (255, 255, 255), (255, 230, 0), (255, 42, 42), (60, 200, 110), (0, 0, 0)
SAFE_R = 940   # 右の Shorts ボタン(x>=960)にかけない

def f(p, s): return ImageFont.truetype(p, s)
def sec(ts):
    m, s = ts.split(":"); return int(m) * 60 + float(s)

def ph(d, box, label, base=118):
    x0, y0, x1, y1 = box
    d.rectangle(box, fill=(base, base, base + 6))
    for k in range(x0 - (y1 - y0), x1, 60):
        d.line([(k, y1), (k + (y1 - y0), y0)], fill=(base + 14,) * 3, width=3)
    for i, ln in enumerate(label.split("|")):
        d.text(((x0 + x1) / 2, (y0 + y1) / 2 - 30 + i * 54), ln, font=f(MPB, 40), fill=(235, 235, 235), anchor="mm")

def t3(d, xy, s, fo, fill, anchor="mm"):
    x, y = xy
    d.text((x + 8, y + 10), s, font=fo, fill=BLK, anchor=anchor, stroke_width=8, stroke_fill=BLK)
    d.text((x, y), s, font=fo, fill=fill, anchor=anchor, stroke_width=8, stroke_fill=BLK)

def fit(d, s, base, maxw, path=DELA):
    size = base
    while size > 40 and d.textlength(s, font=f(path, size)) + 16 > maxw: size -= 4
    return f(path, size)

def ui(d):
    d.rectangle((960, 1080, W, 1720), outline=(80, 200, 255), width=3)
    d.rectangle((0, 1720, W, H), outline=(80, 200, 255), width=3)

def side(d, label, lines):  # 型C: 左にカード(白フチ)、右(640〜940)に短い行
    d.rectangle((0, 0, W, H), fill=(40, 34, 30))
    d.rectangle((30, 440, 530, 1360), fill=WHITE)
    ph(d, (46, 456, 514, 1344), label)
    step = 150
    y = 900 - (len(lines) - 1) * step / 2
    for s, c, size in lines:
        t3(d, (745, y), s, fit(d, s, size, SAFE_R - 560), c); y += step

def full(d, label, cap1, cap2, c2=YEL):  # 中盤: 全面の映像 + 下に字幕2行
    d.rectangle((0, 0, W, H), fill=(40, 34, 30))
    ph(d, (0, 240, W, 1420), label)
    if cap1: t3(d, (W / 2, 1500), cap1, fit(d, cap1, 70, 900, MPB), WHITE)
    if cap2: t3(d, (W / 2, 1620), cap2, fit(d, cap2, 92, 900), c2)

sc = json.load(open(sys.argv[1]))["variants"][0]["beats"]
frames, notes = [], []
for i, b in enumerate(sc):
    tx = b["texts"]; c1, c2 = tx["copy"]
    dur = sum(sec(c["a"][1]) - sec(c["a"][0]) for c in b["cuts"])
    src = "・".join(c["a"][0][:5] for c in b["cuts"])
    im = Image.new("RGB", (W, H)); d = ImageDraw.Draw(im)
    if i == 0:   # 1コマ目 = サムネ
        side(d, f"元動画 {src}|ミュウツーの接写", [("昔の", WHITE, 120), ("カード", WHITE, 120), ("PSA10", WHITE, 120), ("なら", WHITE, 100), ("200万!?", RED, 130)])
        note = "サムネ兼フック。左カード+右5行(台本の『昔のカード』『PSA10なら200万!?』を区切っただけ)"
    elif i == 4:  # 結果: 前半「せーの…」→ ラベル
        full(d, f"元動画 {src}|PSA ラベルが見える所", "せーの…", c2, RED)
        note = "結果。ラベルが見えた瞬間に PSA 9(実際の結果)。歓声なし"
    elif i == 5:  # 締め = 型C に戻る
        side(d, "元動画 14:36|PSA ケースのミュウツー", [("仕入れ", WHITE, 90), ("2,000円", GRN, 90), ("鑑定後", WHITE, 90), ("16万円", RED, 120)])
        cta = tx.get("cta", ["", ""])
        t3(d, (W / 2, 1530), cta[0], fit(d, cta[0], 60, 900, MPB), WHITE)
        t3(d, (W / 2, 1630), cta[1] + " ▼", fit(d, cta[1] + " ▼", 70, 900, MPB), YEL)
        note = "締め。最初と同じ左右の型に戻る(=ループの継ぎ目)。誘導は下に小さく"
    else:
        full(d, f"元動画 {src}", c1, c2, RED if "激ムズ" in c2 else YEL)
        note = {1: "カード紹介。キラッ+シャキーン(台本 fx)", 2: "難易度。傷の場所に赤い丸", 3: "タメ。四隅を暗く・最後にドラムロール"}[i]
    ui(d)
    frames.append(im); notes.append(f"Cut{i+1} {dur:.1f}秒 {note}")

PW, PH, COLS = 300, 533, 3
rows = (len(frames) + COLS - 1) // COLS
out = Image.new("RGB", (40 + COLS * (PW + 30), 110 + rows * (PH + 180)), WHITE)
od = ImageDraw.Draw(out)
od.text((20, 14), "ミュウツー 2,000円→PSA9(型C サムネ特化)", font=f(MPB, 28), fill=BLK)
od.text((20, 50), "台本 mewtwo_psa.json v3 / 灰色=元動画のコマ / 水色=UI / 文字は台本のまま", font=f(MPB, 22), fill=(60, 60, 60))
for k, (im, n) in enumerate(zip(frames, notes)):
    x, y = 20 + (k % COLS) * (PW + 30), 110 + (k // COLS) * (PH + 180)
    out.paste(im.resize((PW, PH), Image.LANCZOS), (x, y))
    for j in range(0, len(n), 14):
        od.text((x, y + PH + 8 + (j // 14) * 28), n[j:j + 14], font=f(MPB, 21), fill=(200, 30, 30))
out.save(sys.argv[2]); print(out.size, sum(float(n.split()[1][:-1]) for n in notes), "秒")
