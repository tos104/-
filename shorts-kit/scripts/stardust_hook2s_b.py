"""スターダスト D改の導入2秒案 その2(案6〜10)。0.0〜2.0秒を0.5秒ごと。数字・発言は元動画の声と字幕のみ。"""
import sys
sys.path.insert(0, '/home/user/-/shorts-kit')
sys.path.insert(0, '/home/user/-/shorts-kit/scripts')
import storyboard_variants as sv
from stardust_hook2s import base, stamp, label, Q, OUT
from PIL import Image, ImageDraw, ImageFilter

S = 1080 / 640; VY = sv.VID_Y2


def buttons(img, y, lit=None):
    d = ImageDraw.Draw(img)
    for k, (t, col) in enumerate([("買う", (220, 40, 50)), ("見送る", (60, 90, 160))]):
        x0 = 110 + k * 450; on = lit == k
        d.rounded_rectangle((x0, y, x0 + 410, y + 150), radius=30, fill=col if on else (255, 255, 255), outline=col, width=10)
        d.text((x0 + 205, y + 75), t, font=sv.font('dela', 72), fill=(255, 255, 255) if on else col, anchor='mm')
    return img


def quote(img, text, sub):
    o = Image.new('RGBA', img.size, (0, 0, 0, 0)); d = ImageDraw.Draw(o)
    d.rectangle((0, VY, 1080, VY + 608), fill=(0, 0, 0, 170))
    img = Image.alpha_composite(img.convert('RGBA'), o).convert('RGB'); d = ImageDraw.Draw(img)
    for k, line in enumerate(text.split('|')):
        d.text((540, VY + 230 + k * 120), line, font=sv.font('dela', 92), fill=(255, 255, 255), anchor='mm', stroke_width=6, stroke_fill=(0, 0, 0))
    d.text((540, VY + 520), sub, font=sv.font('xb', 40), fill=(255, 220, 60), anchor='mm'); return img


def mosaic(img, box_src):
    x0, y0, x1, y1 = [int(v * S) for v in box_src]; y0 += VY; y1 += VY
    reg = img.crop((x0, y0, x1, y1)); w, h = reg.size
    reg = reg.resize((max(1, w // 28), max(1, h // 28)), Image.NEAREST).resize((w, h), Image.NEAREST)
    img.paste(reg, (x0, y0)); d = ImageDraw.Draw(img)
    d.rounded_rectangle((x0, y0, x1, y1), radius=10, outline=(255, 220, 60), width=8)
    d.text(((x0 + x1) / 2, (y0 + y1) / 2), "？", font=sv.font('dela', 110), fill=(255, 220, 60), anchor='mm', stroke_width=6, stroke_fill=(0, 0, 0)); return img


def countdown(img, n, bar):
    d = ImageDraw.Draw(img)
    d.ellipse((780, VY + 30, 1020, VY + 270), fill=(220, 40, 50), outline=(255, 255, 255), width=10)
    d.text((900, VY + 150), str(n), font=sv.font('dela', 150), fill=(255, 255, 255), anchor='mm')
    d.rounded_rectangle((60, VY + 620, 1020, VY + 650), radius=15, fill=(60, 60, 60))
    d.rounded_rectangle((60, VY + 620, 60 + 960 * bar, VY + 650), radius=15, fill=(255, 220, 60)); return img


LBL = (40, 215, 285, 295)  # 945.6 秒のラベル(元動画の px)
P = [["仕入れ", "50,000円"], ["鑑定結果", "…"]]
IDEAS = [
 ("6", "判断を迫る(あなたなら買う？)", "見る人に『店の値付け5万円、買う？見送る？』と選ばせ、本人の判断と結果を最後に見せる",
  "声: 「5万円で買いましたからね…5万かって悩んだんですけど」(15:52)",
  [lambda: buttons(base(923.7, ["お店の値付け 5万円", "あなたなら買う？"], [["価格", "50,000円"]]), 1350),
   lambda: buttons(base(924.2, ["お店の値付け 5万円", "あなたなら買う？"], [["価格", "50,000円"]]), 1350, 0),
   lambda: buttons(base(924.7, ["お店の値付け 5万円", "あなたなら買う？"], [["価格", "50,000円"]]), 1350, 1),
   lambda: buttons(base(925.2, ["本人は悩んだ末に", "買った"], [["価格", "50,000円"]]), 1350, 0),
   lambda: base(925.7, ["本人は悩んだ末に", "買った。その結果は"], Q)]),
 ("7", "本人の一言を大写し", "0秒は映像を暗くして本人の言葉だけを大きく見せる。言葉の意味(買った理由)が2秒目で分かる",
  "声: 「これ鑑定に出したら10取れそうだなと思って」(16:03)から開始",
  [lambda: quote(base(963.0, ["", ""], [["仕入れ", "50,000円"]]), "「10取れそうだな|と思って」", "5万円で買った理由"),
   lambda: quote(base(963.5, ["", ""], [["仕入れ", "50,000円"]]), "「10取れそうだな|と思って」", "5万円で買った理由"),
   lambda: base(964.0, ["5万円で買った理由は", "「10取れそう」"], [["仕入れ", "50,000円"], ["鑑定結果", "？"]]),
   lambda: base(964.5, ["5万円で買った理由は", "「10取れそう」"], [["仕入れ", "50,000円"], ["鑑定結果", "？"]]),
   lambda: base(965.0, ["読みは当たったのか", "鑑定結果は"], [["仕入れ", "50,000円"], ["鑑定結果", "？"]])]),
 ("8", "ラベルを隠す(答えを見せて隠す)", "結果のラベルが見える瞬間を0秒に置き、点数の部分だけモザイク。答えが画面にあるのに見えない",
  "声: 「おっ」(15:45)→『シュッ』→「10だったら相当嬉しい…」",
  [lambda: mosaic(base(945.6, ["この下に", "点数が書いてある"], P), LBL),
   lambda: mosaic(base(945.6, ["この下に", "点数が書いてある"], P), LBL),
   lambda: mosaic(base(945.6, ["5万円で買った旧レリーフ", "10か9か"], P), LBL),
   lambda: base(325.5, ["5万円で買った旧レリーフ", "10か9か、本人も知らない"], Q),
   lambda: base(326.0, ["5万円で買った旧レリーフ", "10か9か、本人も知らない"], Q)]),
 ("9", "難しさを先に言う", "本人の『旧レリーフで10はホントにすごい』を0秒に置き(声は15:07、映像はスターダスト)、10を取る難しさ(期待の高さ)を先に伝える",
  "声: 「レリーフは10点でホントにすごいんで」(15:07)から開始",
  [lambda: base(923.7, ["", "旧レリーフで10は"], [["仕入れ", "50,000円"]]),
   lambda: base(924.2, ["本人いわく", "「10でホントにすごい」"], [["仕入れ", "50,000円"]]),
   lambda: base(924.7, ["本人いわく", "「10でホントにすごい」"], [["仕入れ", "50,000円"], ["鑑定結果", "？"]]),
   lambda: base(925.0, ["5万円で買った", "このスターダストは"], [["仕入れ", "50,000円"], ["鑑定結果", "？"]]),
   lambda: base(925.5, ["5万円で買った", "このスターダストは"], [["仕入れ", "50,000円"], ["鑑定結果", "？"]])]),
 ("10", "カウントダウン(結果まで3秒)", "裏返す直前から始め、右上に3→2→1と下の進み棒。2秒で裏返り、結果の直前で止める",
  "声: 「頼むぞ、よいしょ」(15:43)から開始",
  [lambda: countdown(base(942.5, ["5万円の旧レリーフ", "結果まであと3秒"], P), 3, 0.0),
   lambda: countdown(base(943.0, ["5万円の旧レリーフ", "結果まであと3秒"], P), 3, 0.17),
   lambda: countdown(base(943.5, ["5万円の旧レリーフ", "結果まであと2秒"], P), 2, 0.33),
   lambda: countdown(base(944.0, ["5万円の旧レリーフ", "結果まであと2秒"], P), 2, 0.5),
   lambda: countdown(base(944.5, ["5万円の旧レリーフ", "結果まであと1秒"], P), 1, 0.67)]),
]
for key, name, how, voice, frames in IDEAS:
    ims = [f().resize((360, 640), Image.LANCZOS) for f in frames]
    sheet = Image.new('RGB', (16 + 5 * 376, 640 + 300), 'white'); d = ImageDraw.Draw(sheet)
    d.text((20, 16), f"導入2秒 案{key}  {name}", font=sv.font('dela', 44), fill=(30, 30, 30))
    d.text((20, 78), "手法: " + how, font=sv.font('bold', 26), fill=(60, 60, 60))
    d.text((20, 116), voice, font=sv.font('bold', 26), fill=(60, 60, 60))
    for k, im in enumerate(ims):
        x = 16 + k * 376; sheet.paste(im, (x, 170))
        d.text((x + 6, 176), f"{k * 0.5:.1f}秒", font=sv.font('dela', 30), fill=(255, 40, 40), stroke_width=4, stroke_fill=(255, 255, 255))
    sheet.save(f"{OUT}/hook2s_{key}.png"); print(key)
