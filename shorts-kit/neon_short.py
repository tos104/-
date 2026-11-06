#!/usr/bin/env python3
"""図解ネオン(白版)のショートを書き出す。1 つの舞台で通し、物を足して色と位置を変える(PLAYBOOK 4.861)。

台本(JSON): {"scene": "fx_spread", "fps": 60, "shots": [{"dur", "caption", "final", "sfx", "note"}, ...]}
  python3 neon_short.py scripts/fx_spread_1107_v2.json --out out.mp4 [--frames 0,2.5,...]
字幕・効果音は台本のカットごと。物の動きは SCENES[scene](im, t, cuts) が全体の時刻 t で描く。
"""
import argparse, json, os, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from neon_stage import *          # noqa


def k_(t, t0, d=0.3):
    return ease((t - t0) / d)


def fade(im, fn, a):
    """fn(tmp) で描いたものを透明度 a で重ねる。"""
    if a <= 0:
        return im
    tmp = im.copy()
    fn(tmp)
    return tmp if a >= 1 else Image.blend(im, tmp, a)


def cursor(im, x, y, press=0.0):
    d = ImageDraw.Draw(im)
    s = 1 - 0.15 * press
    pts = [(0, 0), (0, 60), (16, 46), (30, 74), (40, 68), (26, 42), (46, 40)]
    d.polygon([(x + px * s, y + py * s) for px, py in pts], fill=(255, 255, 255), outline=INK, width=3)


# ---- fx_spread(1107 ①)-------------------------------------------------
CX, BAND_Y = 540, 450
L_PTS = [(80 + i * 66, 1200) for i in range(5)]
R_PTS = [(736 + i * 66, 1200) for i in range(5)]
L_STAY = [(120, 1200), (186, 1200), (153, 1110)]           # 残って積み上がる
L_LEAVE = [(420, 1265), (490, 1285)]                       # 去る(ストップを置く人)。右下へ(ユーザー指定 2026-11-06)


def mini_band(im, cx, gap, col, label, k=1.0, dim=0.0):
    if k <= 0:
        return
    g = gap * back(k)
    top = SHELF_Y - 40 - g
    c = tuple(int(a + (b - a) * dim) for a, b in zip(col, (205, 210, 218)))
    layer = Image.new("RGBA", im.size, (0, 0, 0, 0))
    ImageDraw.Draw(layer).rectangle((cx - 120, top, cx + 120, top + g), fill=c + (int(60 - 35 * dim),))
    im.paste(layer, (0, 0), layer)
    glow(im, lambda d, cc: (d.line((cx - 120, top, cx + 120, top), fill=cc, width=6),
                            d.line((cx - 120, top + g, cx + 120, top + g), fill=cc, width=6)), c, 12, 0.35)
    ImageDraw.Draw(im).text((cx, SHELF_Y + 30), label, font=F(54), anchor="ma", fill=c)


def fx_spread(im, t, cuts, sc=None):
    c = cuts                         # 各カットの開始秒
    end = c[-1]                      # 最後のカット(保存の画面)
    ttl = (sc or {}).get("title", "FX会社は\n何もしなくても稼げる")
    has_pill = (sc or {}).get("pill", True)
    hook_stay = (sc or {}).get("hook") == "stay"     # 冒頭で「残る」人を先に見せる(案1)
    # 冒頭の題 → 小見出し(2 カット目の頭で入れ替え)
    a = k_(t, c[1], 0.3)
    if a < 1:
        im = fade(im, lambda x: title(x, ttl, y=190), 1 - a)
    if a > 0 and t < end:
        im = fade(im, lambda x: header(x, "FX会社の稼ぎ方"), a)
    # 棚と会社(1〜6 カット)。7 カット目の頭で消える
    gone = k_(t, c[6], 0.3)
    if gone < 1:
        def stage(x):
            shelf(x)
            building(x, CX, SHELF_Y)
        im = fade(im, stage, 1 - gone) if gone > 0 else (stage(im) or im)
    if gone >= 1:
        shelf(im)
    # 値段の 2 本(1〜5 カット)。2 カット目で「？」→「スプレッド」
    if t < c[5] + 0.3 and (not hook_stay or t >= c[1]):
        p = 1.0 if hook_stay else k_(t, c[1] + 0.1, 0.35)
        out = k_(t, c[5], 0.3) if not hook_stay else 1 - k_(t, c[1], 0.3) * (1 - k_(t, c[5], 0.3))
        im = fade(im, lambda x: spread_band(x, CX, BAND_Y, 640, 110, fill_k=p, q=1 - p,
                                            label="スプレッド" if p > 0.5 else None, dashed=p < 0.5), 1 - out)
    # 冒頭(案1): 残る人の山・右下へ去る人・札「残る」を 1コマ目から見せる。2 カット目の頭で消える
    if hook_stay and t < c[1] + 0.3:
        def hook(x):
            people(x, L_STAY, RED)
            people(x, L_LEAVE, (205, 210, 218))
            people(x, R_PTS, BLUE)
            ImageDraw.Draw(x).text((455, 1130), "ストップ", font=F(36), anchor="ma", fill=SUB)
            sticker(x, 153, 940, "残る", col=RED, angle=-8)
        im = fade(im, hook, 1 - k_(t, c[1], 0.3))
    # 取り分の矢印(2 カット目)
    ar = k_(t, c[1] + 0.8, 0.3) * (1 - k_(t, c[2], 0.25))
    if ar > 0:
        def f(x):
            arrow(x, CX, BAND_Y + 130, CX, SHELF_Y - 340, INK, k=min(1, k_(t, c[1] + 0.8, 0.3)))
            ImageDraw.Draw(x).text((CX + 30, BAND_Y + 140), "取り分", font=F(44), anchor="la", fill=INK)
        im = fade(im, f, ar)
    # 人(3〜5 カット)
    if c[2] <= t < c[5] + 0.3:
        out = k_(t, c[5], 0.3)
        def ppl(x):
            d = ImageDraw.Draw(x)
            mv = k_(t, c[4] + 0.2, 0.9)                     # 5 カット目: 去る人・積み上がる人へ動く
            pts_l, cols_l = [], []
            for i, (px, py) in enumerate(L_PTS):
                kk = back((t - c[2] - 0.3 - 0.1 * i) / 0.3)
                if kk <= 0:
                    continue
                if i < 3:
                    tx, ty = L_STAY[i]
                    pts_l.append((px + (tx - px) * mv, py + (ty - py) * mv - 30 * (1 - min(1, kk))))
                else:
                    tx, ty = L_LEAVE[i - 3]
                    q = (px + (tx - px) * mv, py + (ty - py) * mv)
                    col = tuple(int(a + (b - a) * mv) for a, b in zip(RED, (205, 210, 218)))
                    people(x, [q], col)
            if pts_l:
                people(x, pts_l, RED)
            pts_r = [(px, py) for i, (px, py) in enumerate(R_PTS) if t >= c[2] + 0.6 + 0.1 * i]
            if pts_r:
                people(x, pts_r, BLUE)
            if t >= c[2] + 0.3:
                d.text((212, 1215), "買う人", font=F(40), anchor="ma", fill=RED)
                d.text((868, 1215), "売る人", font=F(40), anchor="ma", fill=BLUE)
                if t < c[4]:
                    note(x, "雇用統計の前", x=40, y=1060)
            if mv > 0.5:
                d.text((455, 1130), "ストップ", font=F(36), anchor="ma", fill=SUB)
        im = fade(im, ppl, 1 - out)
    # カバー(4 カット目)
    if c[3] <= t < c[4] + 0.3:
        out = k_(t, c[4], 0.25)
        def cov(x):
            p = k_(t, c[3] + 0.2, 0.6)
            arrow(x, 340, 1120, 450, 960, RED, k=p)
            arrow(x, 740, 1120, 630, 960, BLUE, k=p)
            sticker(x, CX, 1060, "カバー", col=GREEN, angle=-6, k=(t - c[3] - 0.8) / 0.35)
        im = fade(im, cov, 1 - out)
    # 残る(5 カット目)
    if c[4] <= t < c[5] + 0.3:
        im = fade(im, lambda x: sticker(x, 153, 940, "残る", col=RED, angle=-8, k=(t - c[4] - 1.4) / 0.35), 1 - k_(t, c[5], 0.3))
    # 昔と今(6 カット目)
    if c[5] <= t < c[6] + 0.3:
        out = k_(t, c[6], 0.3)
        def oldnew(x):
            p = k_(t, c[5] + 0.05, 0.4)
            spread_band(x, 290, 420, 380, max(2, 220 * p), label="昔" if p > 0.6 else None)
            q = k_(t, c[5] + 0.8, 0.35)
            if q > 0:
                spread_band(x, 790, 495, 380, max(2, 70 * q), label=None)
                ImageDraw.Draw(x).text((790, 530), "今", font=F(54), anchor="mm", fill=INK)
        im = fade(im, oldnew, 1 - out)
    # 通貨 3 つ(7〜8 カット)
    if c[6] <= t < end:
        mini_band(im, 180, 50, BLUE, "ドル円", k=(t - c[6] - 0.2) / 0.35)
        mini_band(im, 540, 60, BLUE, "ユーロドル", k=(t - c[6] - 0.5) / 0.35)
        mini_band(im, 900, 240, RED, "マイナー通貨", k=(t - c[6] - 0.8) / 0.35, dim=k_(t, c[6] + 1.0, 0.4))
        sticker(im, 300, 770, "狭い！", col=GREEN, angle=-8, k=(t - c[6] - 1.2) / 0.35)
        if t >= c[6] + 1.2:
            note(im, "※幅は形だけ(数字ではない)", x=40, y=1100)
    # 案内の札+カーソル(8 カット目)
    if has_pill and c[7] <= t < end:
        pk = k_(t, c[7] + 0.2, 0.3)
        pill(im, "関連動画で 待てる人の入り方", y=330, k=pk)
        if t >= c[7] + 0.6:
            m = k_(t, c[7] + 0.6, 0.5)
            x0, y0 = 980, 640
            x1, y1 = 830, 400
            press = 1.0 if c[7] + 1.15 <= t < c[7] + 1.35 else 0.0
            cursor(im, x0 + (x1 - x0) * m, y0 + (y1 - y0) * m, press)
    # 最後: 保存をすすめる画面(テクニカル動画と同じ終わり方)
    if t >= end:
        a = k_(t, end, 0.25)
        def end(x):
            d = ImageDraw.Draw(x)
            d.rectangle((0, 0, W, H), fill=(255, 255, 255))
            d.text((540, 760), "保存して、次のトレードで試す", font=F(64), anchor="mm", fill=(31, 104, 176))
            for i, line in enumerate(["教育目的であり、金融・投資助言では", "ありません。取引判断はご自身で", "行ってください。"]):
                d.text((540, 930 + i * 84), line, font=F(52), anchor="mm", fill=INK)
        im = fade(im, end, a)
    return im


SCENES = {"fx_spread": fx_spread}


def frame(sc, t, cuts):
    im = background()
    im = SCENES[sc["scene"]](im, t, cuts, sc)
    i = max(j for j, c0 in enumerate(cuts) if t >= c0)
    s = sc["shots"][i]
    if s.get("caption"):
        same = i > 0 and sc["shots"][i - 1].get("caption") == s["caption"]
        p = 1.0 if same else k_(t, cuts[i], 0.18)
        im = fade(im, lambda x: caption(x, s["caption"], y=1320, final=s.get("final", False)), p)
    return im


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("script")
    ap.add_argument("--out")
    ap.add_argument("--frames", help="カンマ区切りの秒。その時刻の静止画を書き出す(確認用)")
    a = ap.parse_args()
    sc = json.load(open(a.script, encoding="utf-8"))
    cuts = list(np.cumsum([0] + [s["dur"] for s in sc["shots"]])[:-1])
    total = sum(s["dur"] for s in sc["shots"])
    if a.frames:
        base = os.path.splitext(a.out or a.script)[0]
        for tt in a.frames.split(","):
            frame(sc, float(tt), cuts).save(f"{base}_t{float(tt):05.2f}.png")
        return
    fps = sc.get("fps", 60)
    import chart_short as cs                       # 効果音のまとめは chart_short と同じ仕組み
    track = cs.sfx_track(sc)
    video = a.out if track is None else a.out + ".video.mp4"
    enc = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                            "-r", str(fps), "-i", "-", "-c:v", "libx264", "-crf", "18", "-preset", "medium",
                            "-pix_fmt", "yuv420p", "-movflags", "+faststart", video], stdin=subprocess.PIPE)
    for n in range(round(total * fps)):
        enc.stdin.write(frame(sc, n / fps, cuts).tobytes())
    enc.stdin.close()
    enc.wait()
    if track is not None:
        mix, se = track
        wav = a.out + ".sfx.wav"
        se.write_wav(wav, mix)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", video, "-i", wav, "-c:v", "copy", "-c:a", "aac",
                        "-b:a", "192k", "-ar", "48000", "-shortest", "-movflags", "+faststart", a.out], check=True)
        os.remove(video)
        os.remove(wav)
    print(a.out)


if __name__ == "__main__":
    main()
