"""スターダスト D改の導入2秒案(5案)を、0.0/0.5/1.0/1.5/2.0秒のコマで見せる。数字・発言は元動画の声と字幕のみ。"""
import sys, json
sys.path.insert(0, '/home/user/-/shorts-kit')
import storyboard_variants as sv
from PIL import Image, ImageDraw
SRC = '/tmp/claude-0/-home-user--/3ec279b8-9246-59e0-9d53-65132b4b4ed6/scratchpad/src3/src.mp4'
OUT = '/home/user/-/output/hook2s'
R = ["スターダスト・ドラゴン", "旧レリーフ / ARS鑑定"]


def base(t, copy, rows, total=None):
    return sv.still(SRC, 'D2', {"t": t, "texts": {"copy": copy, "head": R[0], "sub": R[1], "rows": rows, **({"total": total} if total else {})}})


def stamp(img, text, y, size=170, col=(220, 40, 50), ang=7):
    d = ImageDraw.Draw(img); f = sv.font('dela', size); tw = d.textlength(text, font=f)
    sp = Image.new('RGBA', (int(tw) + 100, int(size * 1.6)), (0, 0, 0, 0)); sd = ImageDraw.Draw(sp)
    sd.rounded_rectangle((6, 6, sp.width - 7, sp.height - 7), radius=28, fill=(255, 255, 250, 240), outline=col, width=14)
    sd.text((sp.width / 2, sp.height / 2 + 4), text, font=f, fill=col, anchor='mm')
    sp = sp.rotate(ang, resample=Image.BICUBIC, expand=True)
    img.paste(sp, (int(540 - sp.width / 2), int(y - sp.height / 2)), sp); return img


def label(img, text, y, col=(255, 255, 255), bg=(20, 20, 20)):
    d = ImageDraw.Draw(img); f = sv.font('dela', 54); tw = d.textlength(text, font=f)
    d.rounded_rectangle((540 - tw / 2 - 30, y - 50, 540 + tw / 2 + 30, y + 50), radius=16, fill=bg)
    d.text((540, y), text, font=f, fill=col, anchor='mm'); return img


def choices(img, y, lit=None):
    d = ImageDraw.Draw(img)
    for k, v in enumerate(["10", "9"]):
        cx = 330 + k * 420; on = lit == k
        d.ellipse((cx - 120, y - 120, cx + 120, y + 120), fill=(255, 215, 0) if on else (255, 255, 255), outline=(220, 40, 50), width=12)
        d.text((cx, y), v, font=sv.font('dela', 140), fill=(220, 40, 50), anchor='mm')
    d.text((540, y), "or", font=sv.font('dela', 60), fill=(255, 255, 255), anchor='mm', stroke_width=5, stroke_fill=(0, 0, 0)); return img


Q = [["仕入れ", "50,000円"], ["鑑定結果", "？"]]
IDEAS = [
 ("1", "結果から始める(コールドオープン)", "動画でいちばん強い瞬間(紙吹雪+ARS10)を0秒に置き、1.5秒で『5万円で買った日』へ巻き戻す",
  "声: 「おっ、10」(15:45)→巻き戻しの『シュッ』→「10だったら相当嬉しい…」",
  [lambda: stamp(base(945.8, ["", "ARS 10"], [["仕入れ", "50,000円"], ["鑑定結果", "ARS 10"]]), "ARS 10", 680),
   lambda: stamp(base(946.3, ["", "ARS 10"], [["仕入れ", "50,000円"], ["鑑定結果", "ARS 10"]], ["鑑定後", "90,000円"]), "ARS 10", 680),
   lambda: base(946.8, ["5万円の旧レリーフが", "鑑定後9万円に"], [["仕入れ", "50,000円"], ["鑑定結果", "ARS 10"]], ["鑑定後", "90,000円"]),
   lambda: label(base(325.5, ["5万円の旧レリーフが", "鑑定後9万円に"], Q), "巻き戻し：買った日", 660),
   lambda: base(326.0, ["5万円で買った旧レリーフ", "10か9か、本人も知らない"], Q)]),
 ("2", "動きの途中から(開封の直前)", "あいさつ・前置きなし。手がケースを持ち上げ『9点やったら困るな』の瞬間から入り、2秒目で何の話かを足す",
  "声: 「うわ、9点やったら困るな、頼むぞ」(15:41)から開始",
  [lambda: base(941.3, ["", "「9点やったら困るな」"], [["仕入れ", "50,000円"], ["鑑定結果", "…"]]),
   lambda: base(941.8, ["", "「9点やったら困るな」"], [["仕入れ", "50,000円"], ["鑑定結果", "…"]]),
   lambda: base(942.3, ["5万円で買った旧レリーフ", "「9点やったら困るな」"], [["仕入れ", "50,000円"], ["鑑定結果", "…"]]),
   lambda: base(942.8, ["5万円で買った旧レリーフ", "「頼むぞ」"], [["仕入れ", "50,000円"], ["鑑定結果", "…"]]),
   lambda: base(943.3, ["5万円で買った旧レリーフ", "10か9か、裏返すと"], [["仕入れ", "50,000円"], ["鑑定結果", "…"]])]),
 ("3", "数字ドン(無音でも伝わる)", "0秒で画面中央に大きな『5万円』の判子。音を消して見る人にも金額と争点が伝わる",
  "声: 「5万円で買いましたからね」(15:52)から開始",
  [lambda: stamp(base(923.7, ["", ""], [["仕入れ", "50,000円"]]), "5万円", 660, 200),
   lambda: stamp(base(924.2, ["旧レリーフ1枚に", "5万円"], [["仕入れ", "50,000円"]]), "5万円", 660, 200),
   lambda: base(924.7, ["旧レリーフ1枚に", "5万円"], [["仕入れ", "50,000円"], ["鑑定結果", "？"]]),
   lambda: base(925.2, ["5万円の旧レリーフ", "鑑定で何円になる？"], [["仕入れ", "50,000円"], ["鑑定結果", "？"]]),
   lambda: base(925.7, ["5万円の旧レリーフ", "鑑定で何円になる？"], [["仕入れ", "50,000円"], ["鑑定結果", "？"]], ["鑑定後", "？円"])]),
 ("4", "二択の問い(予想させる)", "『10か9か』を大きな丸2つで見せ、見る人に選ばせる。答えは最後まで出さない(オープンループ)",
  "声: 「10だったら相当嬉しいんですけど、もしかしたら9かもしれない」(05:29)",
  [lambda: choices(base(325.5, ["", "何点だと思う？"], Q), 1360),
   lambda: choices(base(326.0, ["5万円の旧レリーフ", "何点だと思う？"], Q), 1360, 0),
   lambda: choices(base(326.5, ["5万円の旧レリーフ", "何点だと思う？"], Q), 1360, 1),
   lambda: choices(base(327.0, ["5万円の旧レリーフ", "何点だと思う？"], Q), 1360),
   lambda: choices(base(327.5, ["答えは最後に", "10か、9か"], Q), 1360)]),
 ("5", "違和感(え？なんで？)", "『鑑定に出した本人が、点数の設定を覚えていない』という意外な事実を0秒で出す",
  "声: 「僕が9でいいってしてたかもしれない、覚えてないですね」(05:33)から開始",
  [lambda: base(333.0, ["", "本人が覚えてない"], [["仕入れ", "50,000円"], ["ミニマム", "9？ 10？"]]),
   lambda: base(333.5, ["9点でもOKにしたか", "本人が覚えてない"], [["仕入れ", "50,000円"], ["ミニマム", "9？ 10？"]]),
   lambda: base(334.0, ["9点でもOKにしたか", "本人が覚えてない"], [["仕入れ", "50,000円"], ["ミニマム", "9？ 10？"]]),
   lambda: label(base(334.5, ["5万円で買った旧レリーフ", "10か9か、本人も知らない"], Q), "ミニマム＝この点数未満は返却", 700, (255, 235, 60)),
   lambda: base(335.0, ["5万円で買った旧レリーフ", "10か9か、本人も知らない"], Q)]),
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
