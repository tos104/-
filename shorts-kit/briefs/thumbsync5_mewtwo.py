# サムネ(assets/thumb_mewtwo_v2.png)のテイスト(全面カード・集中線・白/黄の極太文字)を保ったまま、動画の見せ方を5通りに。
# 各案: 左=冒頭(サムネと同じ) 中=タメ 右=結果。素材は元動画のコマ、文字は台本と字幕の事実だけ。
#   python3 briefs/thumbsync5_mewtwo.py <src.mp4> <out.png>
import sys, subprocess, io, math
sys.path.insert(0, ".")
from PIL import Image, ImageDraw, ImageFilter
import storyboard_variants as sv
W, H = 1080, 1920
WH, YE, RE, BK, GR = (255, 255, 255), (255, 230, 0), (255, 42, 42), (0, 0, 0), (60, 200, 110)
src = sys.argv[1]
ENH = "delogo=x=1:y=1:w=205:h=68,hqdn3d=3:3:4:4,{crop},scale={w2}:{h2}:flags=lanczos,scale={w}:{h}:flags=lanczos,unsharp=5:5:0.9:5:5:0.0,eq=contrast=1.06:saturation=1.12"

def get(t, crop, w, h):
    cw, ch = [int(v) for v in crop.split(":")[1:3]] if crop.startswith("crop=") else (0, 0)
    vf = ENH.format(crop=crop, w2=cw * 2, h2=ch * 2, w=w, h=h)
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-ss", str(t), "-i", src, "-frames:v", "1", "-vf", vf, "-f", "image2pipe", "-vcodec", "png", "-"], capture_output=True, check=True).stdout
    return Image.open(io.BytesIO(raw)).convert("RGBA")

def full(t, cx=215):  # 縦いっぱい(字幕帯を外した上 290px)
    cw = 164; return get(t, f"crop={cw}:290:{int(cx - cw / 2)}:3", W, H)

def bgcard(t, box=(143, 0, 250, 300), size=(900, 1080), y=330):  # ぼかし背景+カード全体を中央に(サムネと同じ)
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-ss", str(t), "-i", src, "-frames:v", "1", "-vf", f"delogo=x=1:y=1:w=205:h=68,scale={W}:{H},boxblur=30:3,eq=brightness=-0.05", "-f", "image2pipe", "-vcodec", "png", "-"], capture_output=True).stdout
    bg = Image.open(io.BytesIO(raw)).convert("RGBA")
    x, y0, cw, ch = box
    c = get(t, f"crop={cw}:{ch}:{x}:{y0}", *size); bg.paste(c, ((W - size[0]) // 2, y)); return bg

T, L = sv.thick, sv.speed_lines
designs = []
HOOK = lambda: bgcard(756.5)

def hook():
    im = HOOK(); L(im, 1.0); d = ImageDraw.Draw(im)
    T(d, (W / 2, 560), "2,000円が…", 120, WH); T(d, (W / 2, 1330), "200万円に", 190, YE); T(d, (W / 2, 1530), "化ける!?", 190, YE); return im

# A 王道: 全編サムネと同じ組み(上白・下黄)。区切りごとに文字だけ替える
def A2():
    im = full(846.0); L(im, 1.6); d = ImageDraw.Draw(im); T(d, (W / 2, 560), "2,000円で買って…", 120, WH); T(d, (W / 2, 1330), "結果は…!?", 190, YE); return im
def A3():
    im = full(868.6, 225); L(im, 2.0); d = ImageDraw.Draw(im); T(d, (W / 2, 560), "2,000円が…", 120, WH); T(d, (W / 2, 1330), "16万円に", 190, YE); T(d, (W / 2, 1530), "化けた!", 190, YE); return im
designs.append(("A 王道(全編サムネの組み)", "全区切りが同じ組み。文字だけ替わる。一番シンプルで、見た目のブレがない", hook(), A2(), A3()))

# B 値段メーター: サムネの下の文字を金額の数字に。2,000→16万に数字が駆け上がる
def B2():
    im = full(846.0); L(im, 1.6); d = ImageDraw.Draw(im); T(d, (W / 2, 560), "鑑定後の値段は…", 120, WH); T(d, (W / 2, 1400), "2,000円 → ？", 170, YE)
    d.rounded_rectangle((140, 1580, 940, 1640), radius=30, fill=(40, 40, 40)); d.rounded_rectangle((140, 1580, 300, 1640), radius=30, fill=GR); return im
def B3():
    im = full(868.6, 225); L(im, 2.0); d = ImageDraw.Draw(im); T(d, (W / 2, 560), "PSA 9", 140, RE); T(d, (W / 2, 1400), "160,000円", 200, YE)
    d.rounded_rectangle((140, 1580, 940, 1640), radius=30, fill=(40, 40, 40)); d.rounded_rectangle((140, 1580, 760, 1640), radius=30, fill=RE); d.text((900, 1530), "200万", font=sv.font("black", 40), fill=WH, anchor="mm"); return im
designs.append(("B 値段メーター", "下の黄色を金額の数字に。数字が 2,000円から駆け上がり、ゲージが200万に近づく", hook(), B2(), B3()))

# C ラベル隠し: サムネのカード構図のまま、ラベル部分に「？」の札を貼り、結果で剥がす
def C2():
    im = bgcard(866.6, (165, 0, 250, 300)); L(im, 1.6); d = ImageDraw.Draw(im)
    d.rounded_rectangle((180, 300, 900, 520), radius=30, fill=(110, 40, 140), outline=BK, width=10); T(d, (W / 2, 410), "PSA ？", 150, WH)
    T(d, (W / 2, 1530), "結果は…!?", 190, YE); return im
def C3():
    im = bgcard(869.0, (165, 0, 250, 300)); L(im, 2.0); d = ImageDraw.Draw(im)
    d.rounded_rectangle((180, 300, 900, 520), radius=30, fill=RE, outline=BK, width=10); T(d, (W / 2, 410), "PSA 9", 150, WH)
    T(d, (W / 2, 1530), "16万円に化けた!", 150, YE); return im
designs.append(("C ラベル隠し", "カードの構図はサムネのまま、ラベルの所に「？」の札。結果で札が赤に変わる", hook(), C2(), C3()))

# D 白黒→カラー: タメまでは白黒+集中線、結果の瞬間に色が戻る(本物の色で答えを見せる)
def D2():
    im = full(846.0).convert("L").convert("RGBA"); L(im, 1.6); d = ImageDraw.Draw(im); T(d, (W / 2, 560), "2,000円で買って…", 120, WH); T(d, (W / 2, 1330), "結果は…!?", 190, WH); return im
def D3():
    im = full(868.6, 225); L(im, 2.0); d = ImageDraw.Draw(im); T(d, (W / 2, 1330), "PSA 9", 220, RE); T(d, (W / 2, 1560), "16万円", 170, YE); return im
designs.append(("D 白黒→カラー", "タメまでは白黒、結果の瞬間に色が戻る。カードの紫が一番映える所で答え", hook(), D2(), D3()))

# E 2択の吹き出し: サムネの問い「化ける!?」に YES/NO を出して予想させる
def E2():
    im = full(846.0); L(im, 1.6); d = ImageDraw.Draw(im); T(d, (W / 2, 560), "化けると思う?", 130, WH)
    for x, s, c in [(300, "化ける", YE), (780, "化けない", WH)]:
        d.rounded_rectangle((x - 210, 1250, x + 210, 1430), radius=50, fill=c, outline=BK, width=10); d.text((x, 1340), s, font=sv.font("dela", 80), fill=BK, anchor="mm")
    return im
def E3():
    im = full(868.6, 225); L(im, 2.0); d = ImageDraw.Draw(im); T(d, (W / 2, 560), "PSA 9 で", 130, WH)
    d.rounded_rectangle((90, 1250, 510, 1430), radius=50, fill=YE, outline=RE, width=14); d.text((300, 1340), "化けた", font=sv.font("dela", 80), fill=BK, anchor="mm")
    T(d, (W / 2, 1580), "2,000円→16万円", 120, YE); return im
designs.append(("E 2択で予想", "サムネの問い「化ける!?」に 化ける/化けない の2択。コメントで答え合わせを誘う", hook(), E2(), E3()))

for _, _, *ims in designs:
    for im in ims:
        d = ImageDraw.Draw(im); d.rectangle((960, 1080, W, 1720), outline=(80, 200, 255), width=3); d.rectangle((0, 1720, W, H), outline=(80, 200, 255), width=3)
PW, PH = 220, 391
out = Image.new("RGB", (30 + len(designs) * (3 * PW + 50), PH + 300), WH); od = ImageDraw.Draw(out)
od.text((20, 14), "サムネ連動 デザイン5案(左=冒頭・中=タメ・右=結果)・水色=Shorts の UI", font=sv.font("black", 30), fill=BK)
for k, (name, note, *ims) in enumerate(designs):
    x = 20 + k * (3 * PW + 50)
    for j, im in enumerate(ims): out.paste(im.convert("RGB").resize((PW, PH), Image.LANCZOS), (x + j * (PW + 6), 70))
    od.text((x, PH + 85), name, font=sv.font("dela", 30), fill=(200, 30, 30))
    line, yy = "", PH + 135
    for ch in note:
        if od.textlength(line + ch, font=sv.font("bold", 22)) > 3 * PW: od.text((x, yy), line, font=sv.font("bold", 22), fill=(60, 60, 60)); yy += 30; line = ch
        else: line += ch
    od.text((x, yy), line, font=sv.font("bold", 22), fill=(60, 60, 60))
out.save(sys.argv[2]); print(out.size)
