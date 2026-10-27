#!/usr/bin/env python3
"""チャートのスクリーンショットを順に重ねて、線が描き足されていくように見せるショート(FX解説向け)。

スタイルは PLAYBOOK.md 4.86(見本「NEW TRADER VS PRO TRADER」を実測)。乱数は使わない(同じ台本からは毎回同じ映像)。
無音で書き出す(音の方針はブリーフで決める)。

台本(JSON):
{
  "assets": "../../output/fx_usdjpy_box/assets",   # 台本からの相対パス
  "header": "固定の見出し",
  "shots": [
    {"img": "2.png", "dur": 3.0,
     "crop": [cx, cy, w], "crop_end": [cx, cy, w],   # 位置はボックス基準(x はボックス幅、y はボックス高さを 1 とする)
     "anchor": "2.png",                              # ボックスが写っていない画像は、同じ表示範囲の画像で位置を合わせる
     "label": "見出しの下の役名", "color": "blue|red|ink",
     "tag": "10/19(月) 16:59", "caption": "下の説明文(\\n で改行)",
     "badges": [["TP 25.2 pips", "green"], ...],
     "note": "なぜこのカットがあるか"}
  ]
}
  python3 chart_short.py script.json --board sb.png   # 絵コンテ(各カットの最後のコマ。実際の画面と同じ合成)
  python3 chart_short.py script.json --out out.mp4
"""
import argparse, json, os, subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageFont

W, H, FPS = 1080, 1920, 30
HERE = os.path.dirname(os.path.abspath(__file__))
F_HEAD = os.path.join(HERE, "fonts", "DelaGothicOne-Regular.ttf")
F_CAP = os.path.join(HERE, "fonts", "MPLUSRounded1c-Black.ttf")
F_TAG = os.path.join(HERE, "fonts", "MPLUSRounded1c-Bold.ttf")
BG = (212, 221, 229)          # 見本の背景 #D4DDE5(実測)
INK = (16, 18, 20)
COLORS = {"blue": (31, 104, 176), "red": (150, 34, 32), "ink": INK, "green": (24, 140, 84)}
PANEL_Y, PANEL_H = 420, 780   # チャートを置く帯(横長のチャートで余白が出すぎないよう低めにする)
CAP_Y, CAP_W = 1270, 860      # 説明文(YouTube ショートの下部 UI より上に収める)
FADE = 0.35                   # 前の画像から次の画像へ溶かす長さ(線が描き足されたように見せる)
TYPE_CPS = 16                 # 説明文を打ち出す速さ(文字/秒)


def font(path, size, _cache={}):
    if (path, size) not in _cache:
        _cache[path, size] = ImageFont.truetype(path, size)
    return _cache[path, size]


def ease(k):
    k = min(1.0, max(0.0, k))
    return 1 - (1 - k) ** 3


def find_box(arr):
    """青いボックスの枠(左上 x, y, 幅, 高さ)を画素の色で探す。見つからなければ None。"""
    a = arr.astype(int)
    m = (abs(a[..., 0] - 45) < 30) & (abs(a[..., 1] - 125) < 30) & (abs(a[..., 2] - 200) < 35)
    rows = np.where(m.sum(1) > 600)[0]
    cols = np.where(m.sum(0) > 80)[0]
    if not len(rows) or not len(cols):
        return None
    return cols[0], rows[0], cols[-1] - cols[0], rows[-1] - rows[0]


class Charts:
    def __init__(self, base):
        self.base, self.cache = base, {}

    def get(self, name, anchor=None):
        if name not in self.cache:
            img = Image.open(os.path.join(self.base, name)).convert("RGB")
            arr = np.asarray(img)
            # 白地を見本の背景色に溶かす(乗算)。線やローソク足の色はほぼそのまま残る
            mul = (arr.astype(np.float32) * np.array(BG, np.float32) / 255).astype(np.uint8)
            self.cache[name] = [Image.fromarray(mul), find_box(arr)]
        img, box = self.cache[name]
        if box is None:
            box = self.get(anchor)[1] if anchor else None
            if box is None:
                raise SystemExit(f"{name}: ボックスが見つからない。anchor に同じ表示範囲の画像を指定する")
            self.cache[name][1] = box
        return img, box

    def view(self, name, crop, anchor=None):
        """ボックス基準の [cx, cy, w] を切り抜いて、帯の大きさにする。はみ出した所は背景色。"""
        img, (bx, by, bw, bh) = self.get(name, anchor)
        cx, cy, cw = crop
        pw = cw * bw
        ph = pw * PANEL_H / W
        x0, y0 = bx + cx * bw - pw / 2, by + cy * bh - ph / 2
        return img.transform((W, PANEL_H), Image.EXTENT, (x0, y0, x0 + pw, y0 + ph),
                             Image.BICUBIC, fillcolor=BG)


def edge_mask(_cache=[]):
    """帯の上下 70px を背景に溶かす(切り抜きの直線の縁を見せない)。"""
    if not _cache:
        ramp = np.clip(np.minimum(np.arange(PANEL_H), PANEL_H - 1 - np.arange(PANEL_H)) / 70, 0, 1)
        _cache.append(Image.fromarray((np.repeat(ramp[:, None], W, 1) * 255).astype(np.uint8), "L"))
    return _cache[0]


def wrap(text, f, width):
    lines = []
    for para in text.split("\n"):
        cur = ""
        for ch in para:
            if f.getlength(cur + ch) > width and cur:
                lines.append(cur)
                cur = ""
            cur += ch
        lines.append(cur)
    return lines


def centered(d, y, text, f, fill):
    d.text((W / 2 - f.getlength(text) / 2, y), text, font=f, fill=fill)


def frame(sc, charts, i, t):
    s = sc["shots"][i]
    dur = s["dur"]
    k = ease(t / dur)
    crop = s["crop"]
    end = s.get("crop_end", crop)
    cur = [a + (b - a) * k for a, b in zip(crop, end)]
    chart = charts.view(s["img"], cur, s.get("anchor"))
    prev = sc["shots"][i - 1] if i else None
    if prev and prev["img"] != s["img"] and t < FADE:
        # 前の画像を同じ位置で切り抜いて溶かす。表示範囲がずれても、ボックスの位置で揃う
        old = charts.view(prev["img"], cur, prev.get("anchor"))
        chart = Image.blend(old, chart, ease(t / FADE))

    im = Image.new("RGB", (W, H), BG)
    im.paste(chart, (0, PANEL_Y), edge_mask())
    d = ImageDraw.Draw(im)
    centered(d, 120, sc["header"], font(F_HEAD, 46), INK)
    if s.get("label"):
        centered(d, 210, s["label"], font(F_HEAD, 84), COLORS[s.get("color", "blue")])
    if s.get("tag"):
        d.text((60, PANEL_Y - 56), s["tag"], font=font(F_TAG, 38), fill=(70, 76, 84))

    cap = s.get("caption", "")
    if cap:
        f = font(F_CAP, 60)
        n = int(t * TYPE_CPS) + 1
        for j, line in enumerate(wrap(cap, f, CAP_W)):   # 改行位置は全文で決め、打ち出し中に文字が跳ねないようにする
            d.text((W / 2 - f.getlength(line) / 2, CAP_Y + j * 82), line[:max(0, n)], font=f, fill=INK)
            n -= len(line)
    for j, (text, color) in enumerate(s.get("badges", [])):
        start = 0.25 + j * 0.35
        if t < start:
            continue
        f = font(F_HEAD, 64)
        sc_k = 0.85 + 0.15 * ease((t - start) / 0.15)
        tw = f.getlength(text)
        bw, bh = (tw + 70) * sc_k, 104 * sc_k
        cy = CAP_Y + 52 + j * 124
        d.rounded_rectangle((W / 2 - bw / 2, cy - bh / 2, W / 2 + bw / 2, cy + bh / 2), radius=20,
                            fill=COLORS[color])
        fs = font(F_HEAD, max(10, int(64 * sc_k)))
        d.text((W / 2, cy), text, font=fs, fill=(255, 255, 255), anchor="mm")
    return im


def board(sc, charts, out):
    pw, ph, th, cols = 324, 576, 230, 4
    n = len(sc["shots"])
    rows = (n + cols - 1) // cols
    sheet = Image.new("RGB", (cols * pw, rows * (ph + th)), (255, 255, 255))
    d = ImageDraw.Draw(sheet)
    f = font(F_TAG, 17)
    t0 = 0.0
    for i, s in enumerate(sc["shots"]):
        x, y = (i % cols) * pw, (i // cols) * (ph + th)
        sheet.paste(frame(sc, charts, i, s["dur"] - 0.05).resize((pw, ph), Image.LANCZOS), (x, y))
        info = f"#{i + 1} {t0:.1f}〜{t0 + s['dur']:.1f}秒  {s['img']}\n" + s.get("note", "")
        for j, line in enumerate(wrap(info, f, pw - 16)[:10]):
            d.text((x + 8, y + ph + 6 + j * 22), line, font=f, fill=(20, 20, 20))
        t0 += s["dur"]
    sheet.save(out)
    print(f"{out} ({t0:.1f}秒・{n}カット)")


def render(sc, charts, out):
    enc = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                            "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-crf", "18",
                            "-preset", "medium", "-pix_fmt", "yuv420p", "-movflags", "+faststart", out],
                           stdin=subprocess.PIPE)
    for i, s in enumerate(sc["shots"]):
        for fno in range(round(s["dur"] * FPS)):
            enc.stdin.write(frame(sc, charts, i, fno / FPS).tobytes())
    enc.stdin.close()
    enc.wait()
    print(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("script")
    ap.add_argument("--board")
    ap.add_argument("--out")
    a = ap.parse_args()
    sc = json.load(open(a.script, encoding="utf-8"))
    charts = Charts(os.path.join(os.path.dirname(os.path.abspath(a.script)), sc["assets"]))
    if a.board:
        board(sc, charts, a.board)
    if a.out:
        render(sc, charts, a.out)


if __name__ == "__main__":
    main()
