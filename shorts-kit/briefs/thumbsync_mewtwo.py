# サムネイル(assets/mewtwo_thumb.png)と同じテイストで組んだ絵コンテ。全面のカード+集中線+白/黄の極太文字。
# 素材は元動画のコマ、文字は台本と字幕の事実だけ。  python3 briefs/thumbsync_mewtwo.py <src.mp4> <out.png>
import sys, math, subprocess, io
sys.path.insert(0, ".")
from PIL import Image, ImageDraw, ImageFilter
import storyboard_variants as sv
W, H = 1080, 1920
WHITE, YEL, RED, BLK = (255, 255, 255), (255, 230, 0), (255, 42, 42), (0, 0, 0)
src = sys.argv[1]

def grab(t):
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-ss", str(t), "-i", src, "-frames:v", "1", "-f", "image2pipe", "-vcodec", "png", "-"], capture_output=True).stdout
    return Image.open(io.BytesIO(raw)).convert("RGB")

def full(t, cx, cy=180, zoom=1.0):  # 元動画をカード中心で縦いっぱいに(サムネと同じ全面)
    fr = grab(t)
    if cy < 170:  # 上端を使うとき(ラベル)は、元動画の左上の番組ロゴをぼかして目立たなくする
        patch = fr.crop((0, 0, 205, 70)).filter(ImageFilter.GaussianBlur(10)); fr.paste(patch, (0, 0))
    ch = 360 / zoom; cw = ch * 9 / 16
    x0 = min(max(cx - cw / 2, 0), 640 - cw); y0 = min(max(cy - ch / 2, 0), 360 - ch)
    return fr.crop((int(x0), int(y0), int(x0 + cw), int(y0 + ch))).resize((W, H), Image.LANCZOS)

def lines(img, n=90, inner=0.42, seed=1, strength=1.0):  # 集中線(中央を空ける)
    import random
    r = random.Random(seed); d = ImageDraw.Draw(img); cx, cy = W / 2, H * 0.47; R = 1500
    for i in range(n):
        a = 2 * math.pi * i / n + r.uniform(-0.02, 0.02); w = r.uniform(0.006, 0.02) * strength
        rin = R * (inner + r.uniform(0, 0.15))
        p = [(cx + R * math.cos(a - w), cy + R * math.sin(a - w)), (cx + R * math.cos(a + w), cy + R * math.sin(a + w)), (cx + rin * math.cos(a), cy + rin * math.sin(a))]
        d.polygon(p, fill=BLK)
    return img

def T(d, xy, s, size, fill, maxw=1000, stroke=14):
    while d.textlength(s, font=sv.font("dela", size)) > maxw: size -= 4
    x, y = xy
    d.text((x + 6, y + 10), s, font=sv.font("dela", size), fill=BLK, anchor="mm", stroke_width=stroke, stroke_fill=BLK)
    d.text((x, y), s, font=sv.font("dela", size), fill=fill, anchor="mm", stroke_width=stroke, stroke_fill=BLK)

def frame(t, cx, cy, zoom, l1, l2, c2=YEL, ln=True, s=1.0, extra=None, y2=1330):
    img = full(t, cx, cy, zoom)
    if ln: lines(img, strength=s)
    d = ImageDraw.Draw(img)
    if l1: T(d, (W / 2, 560), l1, 120, WHITE)
    y = y2
    for k, s_ in enumerate(l2):
        T(d, (W / 2, y + k * 200), s_, 190, c2); 
    if extra: extra(d)
    d.rectangle((960, 1080, W, 1720), outline=(80, 200, 255), width=3); d.rectangle((0, 1720, W, H), outline=(80, 200, 255), width=3)
    return img

def cta(d):
    d.rounded_rectangle((W / 2 - 340, 1560, W / 2 + 340, 1660), radius=24, fill=(240, 192, 120), outline=BLK, width=6)
    d.text((W / 2, 1610), "残り47枚は関連動画 ▼", font=sv.font("black", 56), fill=(32, 96, 64), anchor="mm")

P = [
 ("サムネ(ユーザー作)", None, "参考。このテイストに合わせる"),
 ("1 フック 0〜4秒", frame(786.0, 215, 213, 1.22, "2,000円が…", ["200万円に", "化ける!?"]), "サムネと同じ1コマ目(文字・配置・集中線)で入る。声「10取れたら200万とかやったかな」。0秒に白フラッシュ+ドン"),
 ("2 カード紹介 4〜11秒", frame(790.0, 215, 213, 1.22, "剥がすタイプの", ["拡張シート"], ln=False), "集中線を外して見せる。声「剥がすやつ、ペリペリって…拡張シートのミュウツー」。キラッ"),
 ("3 なぜ難しい 11〜22秒", frame(820.5, 160, 213, 1.22, "剥がし跡・初期傷で", ["10は", "激ムズ!!"], c2=RED, ln=False), "裏面の傷を本人が見せる場面。声「機械で擦れるんですよ」"),
 ("4 タメ 22〜30秒", frame(846.0, 200, 213, 1.22, "2,000円で買って…", ["結果は…!?"], s=1.6), "集中線が濃く・速く。声「2,000円で買いました…8でも9でもいいから」。最後にドラムロール"),
 ("5 結果 30〜34秒", frame(868.6, 225, 155, 1.16, "", ["PSA 9"], c2=RED, s=2.0), "ラベルが見えた瞬間に白フラッシュ+ドン、集中線が一気に開く。声「せーの…素晴らしい、9点ですね」"),
 ("6 着地 34〜39秒", frame(876.5, 270, 150, 1.16, "2,000円が…", ["16万円に", "化けた!"], extra=cta, y2=1200), "サムネの問い「200万円に化ける!?」に事実で答えて輪を閉じる。声「10は幻なんで」。レジ音"),
]
thumb = Image.open("assets/mewtwo_thumb.png").convert("RGB").resize((W, H))
PW, PH = 270, 480
out = Image.new("RGB", (30 + len(P) * (PW + 20), PH + 360), WHITE); od = ImageDraw.Draw(out)
od.text((20, 14), "ミュウツー サムネ連動版(全面カード+集中線+白/黄の極太文字)・水色=Shorts の UI", font=sv.font("black", 30), fill=BLK)
for k, (name, im, note) in enumerate(P):
    x = 20 + k * (PW + 20)
    out.paste((thumb if im is None else im).resize((PW, PH), Image.LANCZOS), (x, 70))
    od.text((x, PH + 85), name, font=sv.font("dela", 24), fill=(200, 30, 30))
    line, yy = "", PH + 125
    for ch in note:
        if od.textlength(line + ch, font=sv.font("bold", 20)) > PW: od.text((x, yy), line, font=sv.font("bold", 20), fill=(60, 60, 60)); yy += 27; line = ch
        else: line += ch
    od.text((x, yy), line, font=sv.font("bold", 20), fill=(60, 60, 60))
out.save(sys.argv[2]); print(out.size)
