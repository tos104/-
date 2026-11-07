"""1107 のりラジオ: 5 案の絵コンテ(ブラッシュアップ反映版 2026-11-07)。

反映したこと(① で決めたこと → ②〜⑤ にも当てる):
- 見ている人の疑問の順に組む(PLAYBOOK 4.9986): 入口 → 結論を先に → 用語の意味(絵で)→ 根拠 → 入り方/決済 → まとめ → 保存
- 冒頭はネガティブ訴求(4.31)を大きく(96px)・引っかかる語を赤に。見出しと絵を合わせる(見出しの言葉がそのまま絵になる)
- 説明の字幕は上(小見出しのすぐ下)。文字はしっぽり明朝。数字は出さない(4.45)
- 関連動画の案内の札は入れない。最後は保存をすすめる画面(「次のトレードで試す」)。声は VOICEVOX(青山龍星)予定
- 元動画に無い補足の説明は「補足(要承認)」と書いて分ける
"""
import os, subprocess, sys
sys.path.insert(0, "/home/user/-/shorts-kit")
from neon_stage import *
from PIL import Image, ImageDraw

SRC = "/home/user/-/output/src_1107/src.mp4"
OUT = "/home/user/-/output/sb_1107"
CAP_Y = 290
PY = 560                 # チャート・図を置く上端(字幕の下)


def grab(t):
    p = f"{OUT}/src_{t}.png"
    if not os.path.exists(p):
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(t), "-i", SRC, "-frames:v", "1", p], check=True)
    return Image.open(p).convert("RGB")


def chart(im, t, box, marks=()):
    """元動画のコマの box を拡大して置く(仮。本番は高画質の画像)。marks = [(種類, x, y, 文字)] は box 内の割合。"""
    fr = grab(t).crop(box)
    w = 1000
    h = round(w * fr.height / fr.width)
    fr = fr.resize((w, h), Image.LANCZOS)
    im.paste(fr, (40, PY))
    d = ImageDraw.Draw(im)
    d.rectangle((40, PY, 40 + w, PY + h), outline=GRID, width=3)
    for kind, rx, ry, *rest in marks:
        x, y = 40 + rx * w, PY + ry * h
        if kind == "ring":
            glow(im, lambda dd, c: dd.ellipse((x - 46, y - 46, x + 46, y + 46), outline=c, width=7), RED, 10, 0.3)
        elif kind == "sticker":
            sticker(im, x, y, rest[0], col=rest[1] if len(rest) > 1 else RED, angle=-6)
        elif kind == "arrow":
            arrow(im, x, y, 40 + rest[0] * w, PY + rest[1] * h, rest[2] if len(rest) > 2 else RED)
    return PY + h


def zig(im, pts, col=INK, w=7):
    glow(im, lambda d, c: d.line(pts, fill=c, width=w, joint="curve"), col, 8, 0.25)


def line(im, a, b, col, w=6):
    glow(im, lambda d, c: d.line((a, b), fill=c, width=w), col, 10, 0.3)


def end_card(im):
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, W, H), fill=(255, 255, 255))
    d.text((540, 760), "保存して、次のトレードで試す", font=F(64), anchor="mm", fill=(31, 104, 176))
    for n, l in enumerate(["教育目的であり、金融・投資助言では", "ありません。取引判断はご自身で", "行ってください。"]):
        d.text((540, 930 + n * 84), l, font=F(52), anchor="mm", fill=INK)


def summary(im, head, items):
    header(im, "まとめ", y=200)
    d = ImageDraw.Draw(im)
    h = 200 + 140 * len(items)
    d.rounded_rectangle((90, 560, 990, 560 + h), 36, fill=(232, 248, 242), outline=GREEN, width=6)
    d.text((540, 640), head, font=F(46), anchor="mm", fill=INK)
    size = 56
    while size > 36 and max(F(size).getlength(it) for it in items) > 800:
        size -= 2                      # 一番長い行が箱に入る大きさに(全行そろえる)
    for n, it in enumerate(items):
        d.text((150, 780 + n * 140), it, font=F(size), anchor="lm", fill=GREEN)


def cut(head=None, cap=None, final=False, ttl=None, draw=None):
    def f(im):
        if draw:
            draw(im)
        if head:
            header(im, head, y=200)
        if cap:
            caption(im, cap, y=CAP_Y, final=final)
        if ttl:
            title(im, ttl, y=170, size=96)
    return f


# ---------------------------------------------------------------- ② トライアングル → レジサポ転換
C_TRI = (30, 75, 300, 270)


def tri_def(im):        # トライアングル(高値が下がり安値が上がる)を線で
    zig(im, [(140, 700), (260, 980), (380, 740), (500, 950), (620, 780), (720, 910), (800, 820), (860, 860)])
    line(im, (120, 690), (900, 840), RED)
    line(im, (120, 1000), (900, 870), BLUE)
    ImageDraw.Draw(im).text((140, 650), "高値が下がる", font=F(40), fill=RED)
    ImageDraw.Draw(im).text((140, 1020), "安値が上がる", font=F(40), fill=BLUE)


def rs_def(im):         # レジサポ転換: 抑えていた線が支えに変わる
    line(im, (100, 860), (980, 860), (120, 170, 120), 8)
    ImageDraw.Draw(im).text((990, 860), "200", font=F(40), anchor="rm", fill=(60, 140, 80))
    zig(im, [(120, 1040), (220, 900), (300, 990), (400, 880), (470, 960), (560, 760), (640, 850), (720, 800), (820, 680), (940, 620)])
    sticker(im, 300, 800, "抵抗", col=RED, angle=-6)
    sticker(im, 700, 960, "支え", col=GREEN, angle=-6)
    arrow(im, 420, 800, 610, 900, INK)


P2 = ("② トライアングル → レジサポ転換 → 押し目買い(信頼動画・レジサポ転換は nori のショートで ×1.51)", [
    (2.4, cut(ttl="トライアングル、\n{抜けた瞬間}に\n買ってない？",
              draw=lambda im: chart(im, 809, C_TRI, [("ring", 0.65, 0.5), ("sticker", 0.66, 0.25, "抜けた瞬間")])),
     "【ネガティブ訴求】「あ、私やってる」。見出しの「抜けた瞬間」に赤丸", "13:20〜13:24"),
    (3.0, cut("結論", "抜けても飛び乗らない\n押してきた所で買う",
              draw=lambda im: chart(im, 857, C_TRI, [("ring", 0.73, 0.52), ("sticker", 0.75, 0.25, "押し", GREEN)])),
     "結論を先に →「なぜ待つの？」", "13:50「押してきたところで買っていきましょう」"),
    (3.0, cut("トライアングルとは", "高値は下がり 安値は上がる\n三角に縮んでいく形", draw=tri_def),
     "用語の意味を絵で。※補足の説明(要承認)", "13:30「下がってきてますよね」"),
    (3.0, cut("なぜ上目線？①", "上に抜けて\n下の安値を割っていない",
              draw=lambda im: chart(im, 827, C_TRI, [("arrow", 0.3, 0.85, 0.6, 0.6, BLUE), ("sticker", 0.25, 0.92, "安値を割らない", BLUE)])),
     "根拠1(ダウ理論で上)", "13:40「ダウ的にも上に抜けて、下の安値を下回ってない」"),
    (3.4, cut("なぜ上目線？② レジサポ転換", "200で抑えられていた線が\n抜けたら支えに変わる", draw=rs_def),
     "用語の意味を絵で(抵抗→支え)", "14:00〜14:10「200でずっと抑えられてた…レジサポ転換」"),
    (3.0, cut("入り方", "押してきた所で買い",
              draw=lambda im: chart(im, 851, C_TRI, [("ring", 0.73, 0.52), ("sticker", 0.75, 0.25, "ここで買い", GREEN)])),
     "実際のチャートで答え合わせ", "13:50"),
    (3.4, cut("決済", "トライアングルの角度でチャネル\n届かない時は逆側を引いて抜けで",
              draw=lambda im: chart(im, 875, C_TRI)),
     "決済の目安", "14:20〜14:40"),
    (3.0, lambda im: summary(im, "トライアングルを抜けたら", ["① 飛び乗らない", "② 安値を割らない+レジサポ転換", "③ 押してきた所で買う"]),
     "持ち帰る3つ(保存する理由)", "まとめ"),
    (2.0, end_card, "保存の画面", "-"),
])

# ---------------------------------------------------------------- ③ ウェッジ
C_WEDGE = (0, 95, 270, 290)


def wedge_def(im):
    zig(im, [(140, 1000), (260, 820), (340, 900), (460, 760), (540, 820), (660, 700), (720, 740), (780, 860), (860, 820), (960, 640)])
    line(im, (120, 1010), (760, 730), BLUE)
    line(im, (120, 860), (760, 680), RED)
    sticker(im, 790, 960, "一旦下に抜け", col=RED, angle=-6)
    sticker(im, 900, 600, "まだ上", col=GREEN, angle=-6)


P3 = ("③ 上昇の後のウェッジ(元の話が短く、理由の説明が無い → ② に入れるのを推奨)", [
    (2.4, cut(ttl="{下に抜けた}から\n売ってない？", draw=lambda im: chart(im, 897, C_WEDGE, [("ring", 0.55, 0.6), ("sticker", 0.6, 0.85, "下に抜けた")])),
     "【ネガティブ訴求】", "14:49"),
    (3.0, cut("結論", "上昇の後のウェッジは\n下に抜けても まだ上に注意", draw=lambda im: chart(im, 901, C_WEDGE)),
     "結論を先に →「なぜ？」", "14:49〜14:58"),
    (3.0, cut("ウェッジとは", "上がりながら\n幅が狭くなっていく形", draw=wedge_def),
     "用語の意味を絵で。※補足の説明(要承認)", "-"),
    (3.0, cut("なぜ注意？", "(元動画に理由の説明が無い)\n※本人に聞いて埋める", draw=wedge_def),
     "※ここが空く。理由が無いと学べない", "14:50「注意しないといけませんね」/「パターンはよくあります」"),
    (3.0, lambda im: summary(im, "上昇の後のウェッジ", ["① 下に抜けても売り急がない", "② まだ上に注意"]), "まとめ", "-"),
    (2.0, end_card, "保存の画面", "-"),
])

# ---------------------------------------------------------------- ④ 三尊(拡大っぽい形)
C_HS = (180, 72, 465, 278)


def hs_expand(im):
    pts = [(120, 900), (230, 760), (320, 880), (470, 620), (600, 940), (760, 700), (860, 1030)]
    zig(im, pts, RED)
    d = ImageDraw.Draw(im)
    for (x, y), t in [((230, 720), "左肩"), ((470, 580), "頭"), ((760, 660), "右肩")]:
        d.text((x, y), t, font=F(40), anchor="mb", fill=RED)
    line(im, (120, 760), (900, 700), SUB, 4)
    sticker(im, 860, 590, "右肩が上", col=RED, angle=-6)
    sticker(im, 860, 1100, "さらに下", col=RED, angle=-6)


P4 = ("④ 三尊でも注意が要る形(拡大っぽい時)・※三尊は休む方針(4.998)なので後回し", [
    (2.4, cut(ttl="{三尊だから売り}、\nで負けてない？", draw=lambda im: chart(im, 917, C_HS, [("sticker", 0.55, 0.12, "三尊？")])),
     "【ネガティブ訴求】", "15:10"),
    (3.0, cut("結論", "右肩が上に来る三尊は\n拡大っぽい時がある。注意", draw=hs_expand),
     "結論を先に →「拡大っぽいって？」", "15:10〜15:20「右肩がちょっと上に来て…拡大っぽい時もあるんで注意」"),
    (3.0, cut("三尊とは", "左肩・頭・右肩の\n3つの山", draw=lambda im: chart(im, 917, C_HS)),
     "用語の意味。※補足の説明(要承認)", "-"),
    (3.2, cut("拡大っぽいとは", "右肩が左肩より上に来て\nさらにその下まで下がる", draw=hs_expand),
     "形の違いを絵で", "15:10"),
    (3.0, cut("どう見る？", "真ん中あたりの三尊で\n抵抗を受けて下がった", draw=lambda im: chart(im, 935, C_HS)),
     "実際の値動き", "15:30〜15:38"),
    (3.0, cut("入り方", "リボンが抜けて\n押しをつけた所から入る", draw=lambda im: chart(im, 955, C_HS, [("ring", 0.8, 0.55)])),
     "入り方(1022 と同じ考え方)", "15:50〜15:55"),
    (3.0, lambda im: summary(im, "三尊に見えたら", ["① 右肩の高さを見る", "② リボン抜け+押しで入る"]), "まとめ", "-"),
    (2.0, end_card, "保存の画面", "-"),
])

# ---------------------------------------------------------------- ⑤ N・M チャネル
C_CH = (220, 70, 465, 247)


def nm_def(im):
    zig(im, [(140, 1040), (360, 760), (480, 880), (760, 600)], BLUE)
    ImageDraw.Draw(im).text((420, 1040), "N", font=F(72), anchor="mm", fill=BLUE)
    zig(im, [(560, 1040), (660, 760), (740, 900), (840, 760), (960, 1040)], RED)
    ImageDraw.Draw(im).text((760, 1100), "M", font=F(72), anchor="mm", fill=RED)


P5 = ("⑤ N・M のチャネルで決済(視聴者の質問に答える形)・※三尊に近い話", [
    (2.4, cut(ttl="{決済}、\nどこでしてる？", draw=lambda im: chart(im, 1013, C_CH)),
     "【ネガティブ訴求】決済に迷う人へ", "16:00「どう引きます？」"),
    (3.0, cut("結論", "形を決めて\nチャネルで決済の目安を引く", draw=lambda im: chart(im, 1007, C_CH)),
     "結論を先に", "16:06〜16:54"),
    (3.0, cut("NとMとは", "N=一度押して上がる形\nM=山が2つの形", draw=nm_def),
     "用語の意味を絵で。※補足の説明(要承認・書籍の定義を確認)", "書籍 p.147〜(決済用チャネル N・MW・三尊)"),
    (3.0, cut("どっちで引く？", "大きく見ればM\nここで入ったらN", draw=lambda im: chart(im, 983, C_CH)),
     "見る大きさで形が変わる", "16:10〜16:23"),
    (3.0, cut("三尊みたいな時", "右肩の幅の倍が\n目安でもOK", draw=lambda im: chart(im, 1001, C_CH)),
     "視聴者の案に本人が OK", "16:40〜16:47"),
    (3.0, cut("効いてる？", "伸ばしてみると\nまだ効いている", draw=lambda im: chart(im, 1013, C_CH)),
     "実際に効いているか", "16:50"),
    (3.0, lambda im: summary(im, "決済の目安", ["① 形(N・M)を決める", "② チャネルを伸ばして見る"]), "まとめ", "-"),
    (2.0, end_card, "保存の画面", "-"),
])


def board(key, title_, cuts_):
    TW, TH = 300, 533
    cols = 5
    rows = (len(cuts_) + cols - 1) // cols
    b = Image.new("RGB", (cols * (TW + 20) + 20, 140 + rows * (TH + 200)), (236, 238, 240))
    bd = ImageDraw.Draw(b)
    bd.text((20, 20), title_, font=F(34), fill=INK)
    total = sum(c[0] for c in cuts_)
    bd.text((20, 74), f"計 {total:.1f} 秒・{len(cuts_)}カット・チャートは元動画 640x360 の拡大(仮)", font=F(26), fill=RED)
    t0 = 0
    for k, (dur, fn, why, src) in enumerate(cuts_):
        im = background()
        fn(im)
        x, y = 20 + (k % cols) * (TW + 20), 140 + (k // cols) * (TH + 200)
        b.paste(im.resize((TW, TH), Image.LANCZOS), (x, y))
        cap = f"#{k+1} {t0:.1f}〜{t0+dur:.1f}秒\n{why}\n元動画 {src}"
        lines = []
        for para in cap.split("\n"):
            cur = ""
            for ch in para:
                if F(19, F_MED).getlength(cur + ch) > TW:
                    lines.append(cur); cur = ""
                cur += ch
            lines.append(cur)
        bd.multiline_text((x, y + TH + 8), "\n".join(lines[:7]), font=F(19, F_MED), fill=INK, spacing=3)
        t0 += dur
    b.save(f"{OUT}/all_{key}.png")
    print(key, total)


for key, (tt, cc) in {"2_triangle": P2, "3_wedge": P3, "4_hs": P4, "5_channel": P5}.items():
    board(key, tt, cc)
