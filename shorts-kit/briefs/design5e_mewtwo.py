# Shorts デザインの新しい5案(21〜25)。サムネ連動とは別。素材は元動画のコマ(ノイズ低減+段階拡大で整えた画質)、文字は台本と字幕の事実だけ。
#   python3 briefs/design5e_mewtwo.py <src.mp4> <out.png>
import sys
sys.argv = [sys.argv[0], sys.argv[1], "/dev/null"] + sys.argv[2:]
sys.path.insert(0, "."); sys.path.insert(0, "briefs")
from PIL import Image, ImageDraw
import storyboard_variants as sv
import importlib.util
spec = importlib.util.spec_from_file_location("ts5", "briefs/thumbsync5_mewtwo.py"); ts5 = importlib.util.module_from_spec(spec)
_src = open("briefs/thumbsync5_mewtwo.py", encoding="utf-8").read().split("T, L = sv.thick")[0]
exec(compile(_src, "ts5", "exec"), ts5.__dict__)
W, H, get, full, bgcard = ts5.W, ts5.H, ts5.get, ts5.full, ts5.bgcard
WH, YE, RE, BK, GR = (255, 255, 255), (255, 230, 0), (255, 42, 42), (0, 0, 0), (60, 200, 110)
T = sv.thick
out_path = sys.argv[3]
designs = []

# 21 値札: カードに紙の値札がぶら下がり、2,000円の札が 160,000円 に書き換わる
def tag(d, x, y, s, col, cross=None):
    d.line((x + 20, y - 120, x + 120, y), fill=(120, 90, 50), width=6)
    d.polygon([(x, y + 40), (x + 60, y), (x + 520, y), (x + 520, y + 220), (x + 60, y + 220), (x, y + 180)], fill=(250, 240, 210), outline=BK)
    d.ellipse((x + 50, y + 95, x + 80, y + 125), fill=(200, 200, 200), outline=BK)
    d.text((x + 300, y + 110), s, font=sv.font("dela", 92), fill=col, anchor="mm")
    if cross: d.line((x + 110, y + 150, x + 500, y + 70), fill=RE, width=14)
def d21a():
    im = bgcard(756.5); d = ImageDraw.Draw(im); tag(d, 470, 1150, "2,000円", BK); T(d, (W / 2, 200), "PSA10なら200万!?", 110, YE); return im
def d21b():
    im = bgcard(869.0, (165, 0, 250, 300)); d = ImageDraw.Draw(im); tag(d, 470, 1150, "2,000円", (120, 120, 120), cross=True)
    tag(d, 380, 1420, "160,000円", RE); T(d, (W / 2, 200), "PSA 9", 140, RE); return im
designs.append(("21 値札", "紙の値札がぶら下がる。結果で 2,000円 に赤線、下に 160,000円 の札", d21a(), d21b()))

# 22 斜めの分割: 左上=買った時(色あせ) / 右下=鑑定後(鮮やか)。結果で境目が動く
def split(ratio, lab2):
    a = full(806.0).convert("RGB"); a = Image.blend(a, Image.new("RGB", a.size, (120, 100, 70)), 0.35).convert("RGBA")
    b = full(868.6, 225); m = Image.new("L", (W, H), 0); md = ImageDraw.Draw(m)
    y0 = int(H * ratio); md.polygon([(0, y0 + 400), (W, y0 - 400), (W, H), (0, H)], fill=255)
    a.paste(b, (0, 0), m); d = ImageDraw.Draw(a); d.line((0, y0 + 400, W, y0 - 400), fill=WH, width=16)
    T(d, (330, 220), "買った時", 90, WH); T(d, (330, 340), "2,000円", 110, GR); T(d, (760, 1600), lab2, 110, YE); return a
designs.append(("22 斜めの分割", "左上=買った時(色あせ)、右下=鑑定後(鮮やか)。結果で境目が上へ動き、鑑定後が広がる", split(0.75, "鑑定後 ？"), split(0.42, "16万円")))

# 23 上に黒い見出し帯+全面映像(縦型のニュース見出し型)
def d23(t, cx, top, sub, big, col):
    im = full(t, cx); d = ImageDraw.Draw(im)
    d.rectangle((0, 0, W, 330), fill=(10, 10, 10)); d.rectangle((0, 330, W, 345), fill=YE)
    T(d, (W / 2, 120), top, 76, WH, stroke=6); T(d, (W / 2, 240), sub, 96, YE, stroke=6)
    if big: T(d, (W / 2, 1380), big, 200, col)
    return im
designs.append(("23 黒い見出し帯", "上に黒帯の固定見出し(テーマ)、下は全面の映像。見出しは最後まで変えず、下の大文字だけ替える", d23(786.0, 215, "2,000円の拡張シート", "PSA10なら200万!?", "", YE), d23(868.6, 225, "2,000円の拡張シート", "PSA鑑定の結果", "PSA 9", RE)))

# 24 通知カード: 画面上から「鑑定結果が届きました」の通知が降りてくる(実在アプリのロゴ・名前は使わない)
def notif(d, y, head, body, col=WH):
    d.rounded_rectangle((60, y, 1020, y + 230), radius=46, fill=(245, 245, 245, 235))
    d.rounded_rectangle((100, y + 40, 200, y + 140), radius=24, fill=RE); d.text((150, y + 90), "鑑", font=sv.font("dela", 64), fill=WH, anchor="mm")
    d.text((240, y + 65), head, font=sv.font("black", 44), fill=(60, 60, 60), anchor="lm")
    d.text((240, y + 150), body, font=sv.font("dela", 62), fill=BK if col == WH else col, anchor="lm")
def d24(t, cx, items):
    im = full(t, cx); d = ImageDraw.Draw(im, "RGBA")
    for k, (h, b, c) in enumerate(items): notif(d, 120 + k * 260, h, b, c)
    return im
designs.append(("24 通知カード", "上から通知が1枚ずつ降りてくる。最後の通知が「PSA 9」。ロゴは使わない", d24(846.0, 200, [("いま", "2,000円で買ったカード", WH), ("鑑定結果", "まもなく届きます…", WH)]),
               d24(868.6, 225, [("いま", "2,000円で買ったカード", WH), ("鑑定結果", "PSA 9", RE), ("鑑定後の値段", "160,000円", (200, 140, 0))])))

# 25 カウントダウン: タメの最後に 3・2・1 の数字(本人の「せーの」と同じ拍)
def d25(t, cx, num, col, sub):
    im = full(t, cx); d = ImageDraw.Draw(im)
    d.ellipse((W / 2 - 330, 660, W / 2 + 330, 1320), fill=(0, 0, 0, 0), outline=WH, width=24)
    T(d, (W / 2, 990), num, 360, col); T(d, (W / 2, 1500), sub, 110, YE); return im
designs.append(("25 カウントダウン", "タメの最後に 3・2・1 を拍で出し、0 の所で答え。本人の「せーの」と同じ拍に合わせる", d25(862.0, 200, "1", WH, "結果は…"), d25(868.6, 225, "9", RE, "PSA 9 = 16万円")))

for _, _, *ims in designs:
    for im in ims:
        d = ImageDraw.Draw(im); d.rectangle((960, 1080, W, 1720), outline=(80, 200, 255), width=3); d.rectangle((0, 1720, W, H), outline=(80, 200, 255), width=3)
PW, PH = 300, 533
out = Image.new("RGB", (40 + len(designs) * (2 * PW + 60), PH + 300), WH); od = ImageDraw.Draw(out)
od.text((20, 14), "Shorts デザイン 新しい5案(21〜25)・左=冒頭/タメ 右=結果・画質を整えた元動画・水色=Shorts の UI", font=sv.font("black", 30), fill=BK)
for k, (name, note, *ims) in enumerate(designs):
    x = 20 + k * (2 * PW + 60)
    for j, im in enumerate(ims): out.paste(im.convert("RGB").resize((PW, PH), Image.LANCZOS), (x + j * (PW + 10), 80))
    od.text((x, PH + 100), name, font=sv.font("dela", 36), fill=(200, 30, 30))
    line, yy = "", PH + 155
    for ch in note:
        if od.textlength(line + ch, font=sv.font("bold", 24)) > 2 * PW: od.text((x, yy), line, font=sv.font("bold", 24), fill=(60, 60, 60)); yy += 32; line = ch
        else: line += ch
    od.text((x, yy), line, font=sv.font("bold", 24), fill=(60, 60, 60))
out.save(out_path); print(out.size)
