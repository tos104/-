#!/usr/bin/env python3
"""チャートのスクリーンショットやリプレイの画面録画を順に重ねて、線が描き足されていくように見せるショート(FX解説向け)。

スタイルは PLAYBOOK.md 4.86(見本「NEW TRADER VS PRO TRADER」を実測)。乱数は使わない(同じ台本からは毎回同じ映像)。
無音で書き出す(音の方針はブリーフで決める)。

台本(JSON):
{
  "assets": "../../output/fx_usdjpy_box/assets",   # 台本からの相対パス
  "header": "固定の見出し", "footer": "常に出す小さな注記(免責など)",
  "look": "vivid", "fps": 60, "type_cps": 22,      # 省略時は乗算で溶かす v2 の見た目・30fps・16 文字/秒
  "rec_file": "replay.mov",                         # 画面録画(assets からの相対パス)。録画を素材にするカットで使う
  "shots": [
    {"img": "2.png", "dur": 3.0,
     "crop": [cx, cy, w], "crop_end": [cx, cy, w],   # 位置はボックス基準(x はボックス幅、y はボックス高さを 1 とする)
     "anchor": "2.png",                              # ボックスが写っていない画像は、同じ表示範囲の画像で位置を合わせる
     "label": "見出しの下の役名", "color": "blue|red|ink",
     "tag": "10/19(月) 16:59", "caption": "下の説明文(\\n で改行)", "type": false,   # false で打ち出さず最初から全文
     "badges": [["TP 25.2 pips", "green"], ...],
     "note": "なぜこのカットがあるか"},
    {"rec": [33.0], "rect": [cx, cy, w], ...},       # 録画の 33.0 秒を静止画で。rect は録画の画素(中心 x, y と幅)
    {"rec": [33.0, 27.5], "rect": [...], "rect_end": [...], "rec_tag": true,   # 33.0→27.5 秒をカットの長さに合わせて流す(逆向き可)
     "mark": [870, 250],                             # 録画の画素の位置に × 印(見送り例)
     "trans": "wipe",                                # 前のカットから線が増えるとき、左から拭くように現す(既定は溶かす)
     "callouts": [[640, 285, "ボックス", "blue"]]},   # 録画の画素の位置に添える短い注記(見本の DEMAND ZONE のように)
    {"card": "免責などの全文", "dur": 2.0}            # チャートなしで文字だけ
  ]
}
  python3 chart_short.py script.json --board sb.png   # 絵コンテ(各カットの最後のコマ。実際の画面と同じ合成)
  python3 chart_short.py script.json --out out.mp4
"""
import argparse, json, os, subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

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
REC_WHITE = [(0, 0, 1280, 40), (0, 500, 1280, 588), (1215, 0, 1280, 588),   # 録画の画面上部・操作ボタン・価格目盛り
             (95, 60, 145, 105), (95, 400, 150, 455)]                          # チャート上のアイコン
REC_HEAD = (95, 5, 400, 38)   # 録画の日時表示(実物をそのまま時刻の表示に使う)
WIPE = 0.6                    # 線を左から拭くように現す長さ
FADE = 0.35                   # 前の画像から次の画像へ溶かす長さ(線が描き足されたように見せる)
TYPE_CPS = 16                 # 説明文を打ち出す速さ(文字/秒)


def font(path, size, _cache={}):
    if (path, size) not in _cache:
        _cache[path, size] = ImageFont.truetype(path, size)
    return _cache[path, size]


def ease_io(k):
    k = min(1.0, max(0.0, k))
    return k * k * (3 - 2 * k)


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
    def __init__(self, base, look=None):
        self.base, self.cache, self.look = base, {}, look

    def to_bg(self, arr):
        """白地を背景色にする。既定は乗算(全体が少し沈む)。vivid は白だけを抜いて、色の彩度を上げる。"""
        if self.look != "vivid":
            return (arr.astype(np.float32) * np.array(BG, np.float32) / 255).astype(np.uint8)
        out = []
        for a in (arr if arr.ndim == 4 else [arr]):
            sat = np.asarray(ImageEnhance.Color(Image.fromarray(a)).enhance(1.35)).astype(np.float32)
            alpha = np.clip((255 - a.min(2).astype(np.float32)) / 40, 0, 1)[..., None]
            out.append((sat * alpha + np.array(BG, np.float32) * (1 - alpha)).astype(np.uint8))
        return np.stack(out) if arr.ndim == 4 else out[0]

    def finish(self, img):
        return img.filter(ImageFilter.UnsharpMask(1.6, 70, 2)) if self.look == "vivid" else img

    def get(self, name, anchor=None):
        if name not in self.cache:
            img = Image.open(os.path.join(self.base, name)).convert("RGB")
            arr = np.asarray(img)
            # 白地を見本の背景色に溶かす(乗算)。線やローソク足の色はほぼそのまま残る
            self.cache[name] = [Image.fromarray(self.to_bg(arr)), find_box(arr)]
        img, box = self.cache[name]
        if box is None:
            box = self.get(anchor)[1] if anchor else None
            if box is None:
                raise SystemExit(f"{name}: ボックスが見つからない。anchor に同じ表示範囲の画像を指定する")
            self.cache[name][1] = box
        return img, box

    def rec(self, path, r0, r1, n):
        """録画の r0〜r1 秒から n コマを取り出す(r0 > r1 なら逆向き)。白地は背景色に溶かし、画面の部品は消す。"""
        key = (path, r0, r1, n)
        if key not in self.cache:
            lo, hi = min(r0, r1), max(r0, r1)
            span = max(hi - lo, 1e-3)
            rate = max(n - 1, 1) / span
            cmd = ["ffmpeg", "-v", "error", "-ss", f"{lo:.3f}", "-i", path, "-t", f"{span + 1 / rate:.3f}",
                   "-vf", f"fps={rate:.4f}", "-frames:v", str(n), "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
            raw = subprocess.run(cmd, capture_output=True, check=True).stdout
            arr = np.frombuffer(raw, np.uint8).reshape(-1, 588, 1280, 3).copy()
            heads = [Image.fromarray(a[REC_HEAD[1]:REC_HEAD[3], REC_HEAD[0]:REC_HEAD[2]]) for a in arr]
            for x0, y0, x1, y1 in REC_WHITE:
                arr[:, y0:y1, x0:x1] = 255
            frames = [Image.fromarray(m) for m in self.to_bg(arr)]
            if r0 > r1:
                frames, heads = frames[::-1], heads[::-1]
            self.cache[key] = frames, heads
        return self.cache[key]

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


def rec_crop(img, rect):
    cx, cy, pw = rect
    ph = pw * PANEL_H / W
    return img.transform((W, PANEL_H), Image.EXTENT, (cx - pw / 2, cy - ph / 2, cx + pw / 2, cy + ph / 2),
                         Image.BICUBIC, fillcolor=BG)


def rec_frames(sc, charts, s):
    r = s["rec"]
    n = 1 if len(r) == 1 else round(s["dur"] * FPS)
    return charts.rec(charts.rec_path(sc), r[0], r[-1], n)


def source(sc, charts, s, t, view):
    """カットの t 秒の絵(帯の大きさ)と、録画の日時表示(なければ None)。"""
    if "rec" in s:
        frames, heads = rec_frames(sc, charts, s)
        j = min(len(frames) - 1, int(t * FPS)) if len(frames) > 1 else 0
        return charts.finish(rec_crop(frames[j], view)), heads[j]
    return charts.finish(charts.view(s["img"], view, s.get("anchor"))), None


def start_key(s):
    return ("rec", s["rec"][0]) if "rec" in s else s.get("img")


def end_key(s):
    return ("rec", s["rec"][-1]) if "rec" in s else s.get("img")


def frame(sc, charts, i, t):
    s = sc["shots"][i]
    dur = s["dur"]
    vivid = charts.look == "vivid"
    k = ease_io(t / dur) if vivid else ease(t / dur)
    im = Image.new("RGB", (W, H), BG)
    head = None
    if "card" not in s:
        crop = s.get("crop", s.get("rect"))
        end = s.get("crop_end", s.get("rect_end", crop))
        cur = [a + (b - a) * k for a, b in zip(crop, end)]
        chart, head = source(sc, charts, s, t, cur)
        prev = sc["shots"][i - 1] if i else None
        same_view = prev and "card" not in prev and \
            prev.get("crop_end", prev.get("rect_end", prev.get("crop", prev.get("rect")))) == crop
        wipe = s.get("trans") == "wipe"
        if same_view and end_key(prev) != start_key(s) and t < (WIPE if wipe else FADE):
            # 同じ表示範囲で線が増えるときだけ溶かす(描き足しに見せる)。範囲が変わるときは切り替えて変化をはっきりさせる
            old, _ = source(sc, charts, prev, prev["dur"] - 1 / FPS, cur)
            if wipe:   # 左から右へ、縁をぼかして拭き取る(線が引かれていくように見せる)
                edge = ease_io(t / WIPE) * (W + 120) - 60
                ramp = np.clip((edge - np.arange(W)) / 60 + 0.5, 0, 1)
                mask = Image.fromarray((np.repeat(ramp[None, :], PANEL_H, 0) * 255).astype(np.uint8), "L")
                chart = Image.composite(chart, old, mask)
            else:
                chart = Image.blend(old, chart, ease(t / FADE))
        im.paste(chart, (0, PANEL_Y), edge_mask())
        if s.get("mark") and t > 0.4:
            x, y = s["mark"]
            cx, cy, pw = cur
            ph = pw * PANEL_H / W
            mx, my = (x - cx + pw / 2) / pw * W, (y - cy + ph / 2) / ph * PANEL_H + PANEL_Y
            r = 46 * (0.8 + 0.2 * ease((t - 0.4) / 0.15))
            dm = ImageDraw.Draw(im)
            for a, b in (((mx - r, my - r), (mx + r, my + r)), ((mx - r, my + r), (mx + r, my - r))):
                dm.line((a, b), fill=COLORS["red"], width=14)
        if s.get("callouts"):
            layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            dl = ImageDraw.Draw(layer)
            cx, cy, pw = cur
            ph = pw * PANEL_H / W
            for j, (x, y, text, color) in enumerate(s["callouts"]):
                p = ease((t - 0.3 - 0.15 * j) / 0.25)
                if p <= 0:
                    continue
                mx, my = (x - cx + pw / 2) / pw * W, (y - cy + ph / 2) / ph * PANEL_H + PANEL_Y + 18 * (1 - p)
                rgb = COLORS[color]
                dl.text((mx, my), text, font=font(F_HEAD, 44), anchor="mm", fill=rgb + (int(255 * p),),
                        stroke_width=7, stroke_fill=BG + (int(255 * p),))
            im.paste(layer, (0, 0), layer)

    d = ImageDraw.Draw(im)
    centered(d, 120, sc["header"], font(F_HEAD, 46), INK)
    if s.get("card"):
        f = font(F_CAP, 52)
        lines = wrap(s["card"], f, CAP_W)
        y0 = PANEL_Y + PANEL_H / 2 - len(lines) * 74 / 2
        for j, line in enumerate(lines):
            d.text((W / 2 - f.getlength(line) / 2, y0 + j * 74), line, font=f, fill=INK)
    if sc.get("footer"):
        centered(d, 1480, sc["footer"], font(F_TAG, 34), (70, 76, 84))
    if s.get("rec_tag") and head is not None:
        hw, hh = head.size
        hm = (np.asarray(head).astype(np.float32) * np.array(BG, np.float32) / 255).astype(np.uint8)
        im.paste(Image.fromarray(hm).resize((round(hw * 1.3), round(hh * 1.3)), Image.LANCZOS), (40, PANEL_Y - 62))
    if s.get("label"):
        prev_label = sc["shots"][i - 1].get("label") if i else None
        p = 1.0 if not vivid or s["label"] == prev_label else ease(t / 0.28)
        f = font(F_HEAD, 84)
        if p >= 1:
            centered(d, 210, s["label"], f, COLORS[s.get("color", "blue")])
        else:      # 役名が変わるときだけ、下から短く入る
            layer = Image.new("RGBA", (W, 140), (0, 0, 0, 0))
            ImageDraw.Draw(layer).text((W / 2 - f.getlength(s["label"]) / 2, 10 + 30 * (1 - p)), s["label"], font=f,
                                       fill=COLORS[s.get("color", "blue")] + (int(255 * p),))
            im.paste(layer, (0, 200), layer)
    if s.get("tag"):
        d.text((60, PANEL_Y - 56), s["tag"], font=font(F_TAG, 38), fill=(70, 76, 84))

    cap = s.get("caption", "")
    if cap:
        f = font(F_CAP, 60)
        n = int(t * sc.get("type_cps", TYPE_CPS)) + 1 if s.get("type", True) else len(cap)
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
        src = s.get("img") or (f"録画 {s['rec'][0]}→{s['rec'][-1]}秒" if "rec" in s else "文字のみ")
        info = f"#{i + 1} {t0:.1f}〜{t0 + s['dur']:.1f}秒  {src}\n" + s.get("note", "")
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
    global FPS
    FPS = sc.get("fps", FPS)
    charts = Charts(os.path.join(os.path.dirname(os.path.abspath(a.script)), sc["assets"]), sc.get("look"))
    charts.rec_path = lambda sc: os.path.join(charts.base, sc["rec_file"])
    if a.board:
        board(sc, charts, a.board)
    if a.out:
        render(sc, charts, a.out)


if __name__ == "__main__":
    main()
