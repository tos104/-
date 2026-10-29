#!/usr/bin/env python3
"""チャートのスクリーンショットやリプレイの画面録画を順に重ねて、線が描き足されていくように見せるショート(FX解説向け)。

スタイルは PLAYBOOK.md 4.86(見本「NEW TRADER VS PRO TRADER」を実測)。乱数は使わない(同じ台本からは毎回同じ映像)。
無音で書き出す(音の方針はブリーフで決める)。

台本(JSON):
{
  "assets": "../../output/fx_usdjpy_box/assets",   # 台本からの相対パス
  "header": "固定の見出し", "footer": "常に出す小さな注記(免責など)",
  "look": "vivid", "fps": 60, "type_cps": 22,      # 省略時は乗算で溶かす v2 の見た目・30fps・16 文字/秒
  "font_head": "MPLUSRounded1c-ExtraBold.ttf", "font_cap": "MPLUSRounded1c-Bold.ttf",   # 省略時は Dela Gothic One / Rounded M+ Black
  "font_tag": "ShipporiMincho-Medium.ttf", "bg": [255, 255, 255],   # bg 省略時は見本の青灰 #D4DDE5
  "panel_y": 520,                                   # チャートの帯の上端(省略時 420)                                               # 小さい文字(注記・役名の下)
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
     "callouts": [[640, 285, "ボックス", "blue"]],    # 録画の画素の位置に添える短い注記(見本の DEMAND ZONE のように)
     "sub": "役名の下の小さな見出し",
     "tate": "縦書きの\n大見出し", "tate_side": "right",   # 台本の "layout": "tate" のとき縦書きで出す(既定は左側)
     "markers": [{"type": "dot", "x": 863, "y": 288, "t": 0.2, "color": "red", "text": "買い"},      # 脈打つ点
                 {"type": "arrow", "x": 880, "y": 250, "x2": 896, "y2": 318, "t": 0.9, "color": "red"},   # 伸びる矢印
                 {"type": "ring", "x": 1098, "y": 298, "r": 30, "t": 2.0, "color": "red"},              # 丸で囲む
                 {"type": "hline", "x": 1095, "x2": 1140, "y": 298, "t": 1.5, "color": "red", "text": "損切り"}],  # 破線
     "reveal": {"x": [780, 870], "box": [300, 351, 1211]},   # rec の絵を左から x まで出していく(リアルタイムに見せる)。box は先に引いてあるボックスを右側にも描く
     "punch": [1.4],                                  # その秒にカメラが一瞬寄る(決め手の場面)
     "sfx": [["pop", 1.4, 0.5]]},                     # 効果音(se.py の名前, カット内の秒, 音量)。台本に "sfx" がなければ無音。台本の "loudness": {"peak_dbtp": -1} で全体のピークをそろえる
    {"diagram": "range_pullback_line", "dur": 3.0},  # 模式図(手順の形を線で描く。実際の価格ではない)
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
REC_HEAD = (95, 5, 400, 47)   # 録画の日時表示(実物をそのまま時刻の表示に使う)
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
        img = frames[j]
        if s.get("reveal"):
            # 足は左から x まで出す。右側は背景にし、先に引いてあったボックスだけを同じ色で描き直す
            rv = s["reveal"]
            out = np.asarray(img).copy()
            x0, x1 = rv["x"]
            edge = int(x0 + (x1 - x0) * min(1.0, t / rv.get("until", s["dur"])))
            out[:, edge + 1:] = BG
            if rv.get("box"):
                top, bottom, right = rv["box"]       # 録画の画素(上辺・下辺・右端)
                src = np.asarray(img)
                fill, line = src[(top + bottom) // 2, right - 20], src[top + 1, right - 20]
                if edge < right:
                    out[top:bottom, edge + 1:right] = fill
                    out[top:top + 4, edge + 1:right + 2] = line
                    out[bottom - 2:bottom + 2, edge + 1:right + 2] = line
                    out[top:bottom + 2, right - 1:right + 2] = line
            img = Image.fromarray(out)
        return charts.finish(rec_crop(img, view)), heads[j]
    return charts.finish(charts.view(s["img"], view, s.get("anchor"))), None


def start_key(s):
    return ("rec", s["rec"][0]) if "rec" in s else s.get("img")


def end_key(s):
    return ("rec", s["rec"][-1]) if "rec" in s else s.get("img")


def to_panel(x, y, cur):
    cx, cy, pw = cur
    ph = pw * PANEL_H / W
    return (x - cx + pw / 2) / pw * W, (y - cy + ph / 2) / ph * PANEL_H + PANEL_Y


def draw_markers(im, s, t, cur):
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for m in s.get("markers", []):
        p = (t - m["t"]) / 0.3
        if p <= 0:
            continue
        rgb = COLORS[m.get("color", "blue")]
        x, y = to_panel(m["x"], m["y"], cur)
        if m["type"] == "dot":
            r = 13 * ease(p)
            d.ellipse((x - r, y - r, x + r, y + r), fill=rgb + (255,), outline=(255, 255, 255, 255), width=4)
            ph = ((t - m["t"]) % 1.2) / 1.2      # 1.2 秒ごとに輪が広がる(視線を止める)
            rr = 16 + 40 * ph
            d.ellipse((x - rr, y - rr, x + rr, y + rr), outline=rgb + (int(200 * (1 - ph)),), width=5)
            if m.get("text"):   # 点の左上に置く(右側は値動きの続きがあるため)
                d.text((x - 26, y - 34), m["text"], font=font(F_HEAD, 40), anchor="rm", fill=rgb + (int(255 * min(1, p)),),
                       stroke_width=6, stroke_fill=BG + (255,))
        elif m["type"] == "ring":
            r = m.get("r", 30) * W / cur[2] * (0.85 + 0.15 * ease(p))
            d.ellipse((x - r, y - r, x + r, y + r), outline=rgb + (int(255 * min(1, p)),), width=8)
        elif m["type"] == "hline":    # 破線(損切りなど)を左から引き、右端に文字
            x2, _ = to_panel(m["x2"], m["y"], cur)
            ex = x + (x2 - x) * ease(p)
            xx = x
            while xx < ex:
                d.line((xx, y, min(xx + 22, ex), y), fill=rgb + (255,), width=7)
                xx += 36
            if m.get("text") and p >= 1:
                d.text((x2 + 14, y), m["text"], font=font(F_HEAD, 40), anchor="lm", fill=rgb + (255,),
                       stroke_width=6, stroke_fill=BG + (255,))
        elif m["type"] == "arrow":
            x2, y2 = to_panel(m["x2"], m["y2"], cur)
            k = ease(p)
            ex, ey = x + (x2 - x) * k, y + (y2 - y) * k
            d.line((x, y, ex, ey), fill=rgb + (255,), width=9)
            ang = np.arctan2(ey - y, ex - x)
            for da in (2.6, -2.6):
                d.line((ex, ey, ex + 30 * np.cos(ang + da), ey + 30 * np.sin(ang + da)), fill=rgb + (255,), width=9)
    im.paste(layer, (0, 0), layer)


TATE_ROT = set("ー－—―～〜…‥()（）「」『』[]［］-=＝")   # 縦書きで 90 度回す文字
TATE_SMALL = set("、。，．")                              # 縦書きで右上に寄せる文字


def draw_tate(im, text, f, fill, n, side="left", y_top=None):
    """縦書き(右の列から左へ)。n 文字目まで出す。読みやすいよう背景色のふちを付ける。"""
    size = f.size
    y_top = PANEL_Y + 20 if y_top is None else y_top
    cols = text.split("\n")
    pitch_x, pitch_y = size * 1.18, size * 1.04
    x_left = 96 if side == "left" else W - 96 - len(cols) * pitch_x
    layer = Image.new("RGBA", im.size, (0, 0, 0, 0))
    for c, col in enumerate(cols):
        x = x_left + (len(cols) - 1 - c) * pitch_x + size / 2
        for r, ch in enumerate(col.replace("→", "↓")):
            if n <= 0:
                break
            n -= 1
            y = y_top + r * pitch_y + size / 2
            tile = Image.new("RGBA", (size * 2, size * 2), (0, 0, 0, 0))
            ImageDraw.Draw(tile).text((size, size), ch, font=f, anchor="mm", fill=fill + (255,),
                                      stroke_width=max(4, size // 10), stroke_fill=BG + (255,))
            if ch in TATE_ROT:
                tile = tile.rotate(-90)
            dx, dy = (size * 0.32, -size * 0.32) if ch in TATE_SMALL else (0, 0)
            layer.alpha_composite(tile, (int(x - size + dx), int(y - size + dy)))
    im.paste(layer, (0, 0), layer)


def poly_part(pts, k):
    """折れ線を全長の k の割合まで返す(線を描いていくアニメーション用)。"""
    seg = [np.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(pts, pts[1:])]
    goal, out = sum(seg) * min(1, max(0, k)), [pts[0]]
    for (a, b), L in zip(zip(pts, pts[1:]), seg):
        if goal >= L:
            out.append(b)
            goal -= L
        else:
            out.append((a[0] + (b[0] - a[0]) * goal / L, a[1] + (b[1] - a[1]) * goal / L))
            break
    return out


def _traced(scale=1.0):
    """録画 0.5 秒(10/20 5:59)の全体チャートをなぞった図。座標は録画の画素で読み取り、帯の座標へ写す。
    scale < 1 で左に寄せて縮める(右側のショートのアイコンを避ける)。"""
    T = lambda x, y: (round(40 + (x - 395) * 1.42 * scale), round(60 + (y - 60) * 1.9 * scale))
    path = [(400, 230), (410, 213), (440, 290), (453, 317), (475, 300), (520, 257), (540, 300), (563, 327),
            (580, 250), (597, 300), (610, 262), (630, 330), (640, 315), (663, 165), (690, 270), (705, 262),
            (733, 307), (745, 330), (767, 320), (785, 370), (800, 263), (813, 310), (830, 243), (870, 235),
            (887, 293), (893, 313), (900, 247), (923, 217), (943, 182), (957, 203), (963, 237), (977, 197),
            (983, 137), (993, 173), (1000, 148), (1007, 117), (1027, 130), (1040, 83), (1060, 113), (1090, 80),
            (1110, 107)]
    fast = [(400, 240), (430, 245), (460, 270), (480, 295), (500, 305), (530, 300), (560, 290), (600, 290),
            (640, 293), (670, 282), (700, 268), (720, 252), (750, 285), (780, 300), (800, 308), (820, 300),
            (850, 270), (880, 250), (910, 240), (950, 230), (980, 205), (1010, 175), (1040, 138), (1070, 110),
            (1100, 95)]
    slow = [(400, 243), (430, 240), (460, 262), (500, 280), (530, 285), (560, 300), (600, 303), (640, 302),
            (660, 300), (690, 285), (720, 282), (750, 283), (780, 288), (810, 285), (840, 292), (880, 290),
            (900, 285), (930, 270), (960, 245), (990, 225), (1020, 195), (1050, 165), (1080, 140), (1100, 125)]
    return {
        "dy": 230, "box": T(400, 245) + T(1005, 310), "range_end": T(880, 0)[0],
        "path": [T(*p) for p in path], "ribbon_fast": [T(*p) for p in fast], "ribbon_slow": [T(*p) for p in slow],
        "line": (T(928, 145), T(997, 265)), "entry": T(970, 218), "stop": (T(950, 0)[0], T(1010, 0)[0], T(0, 252)[1]),
        # トレンドチャネルは平行。下の線の傾きをそのまま使い、上の線は 1 点(録画で読んだ上限の高値 1045,70)を通す
        "channel": ((T(928, 280), T(1118, 92)), (T(930, 70 + (280 - 92) / (1118 - 928) * (1045 - 930)), T(1045, 70))),
        "exit": T(1105, 103),
        "ribbon": True, "exit_dy": 60, "labels_below": True, "follow_path": True,
        "X": lambda x: T(x, 0)[0],
    }


DIAGRAMS_EXTRA = {"traced": _traced, "traced_small": lambda: _traced(0.78)}

# まとめの図を 1 段階ずつ見せる(ユーザー指定 2026-10-28)。x は録画の画素。各段階: 名前・開始秒・値動きを描き終える秒・止める秒
STAGES = [
    ("① レンジ", 0.0, 1.4, 400, 880),
    ("② リボンがレンジを抜ける", 1.8, 2.8, 880, 965),
    ("③ 押し目に切り下げライン", 4.0, 4.0, 965, 965),
    ("④ ライン抜けでエントリー", 4.8, 5.1, 965, 975),
    ("⑤ トレンドチャネルで決済", 6.3, 7.7, 975, 1110),
]


def clip_path_x(path, x):
    """折れ線を x までで切る。"""
    out = [path[0]]
    for a, b in zip(path, path[1:]):
        if b[0] <= x:
            out.append(b)
        else:
            if a[0] < x:
                out.append((x, a[1] + (b[1] - a[1]) * (x - a[0]) / (b[0] - a[0])))
            break
    return out


def draw_staged(im, t, dur, scale=0.78):
    """なぞった図を段階ごとに描き、各段階の終わりで止める。段階の名前を図の上に出す。
    各段階の開始秒は台本の "stage_starts" で変えられる(読み上げの長さに合わせる)。"""
    g = _traced(scale)
    X = g["X"]
    oy = PANEL_Y + 415          # 縦書き(上から y≈972 まで)の下に置く
    d = ImageDraw.Draw(im)
    st = max(i for i, s_ in enumerate(STAGES) if t >= s_[1])
    name, t0, t1, xa, xb = STAGES[st]
    x_now = X(xa) + (X(xb) - X(xa)) * (ease_io((t - t0) / (t1 - t0)) if t1 > t0 else 1.0)
    bx0, by0, bx1, by1 = g["box"]
    bk = ease(t / 0.4)
    d.rectangle((bx0, oy + by0, bx0 + (bx1 - bx0) * bk, oy + by1), fill=(198, 216, 236), outline=COLORS["blue"], width=5)
    d.text((bx0 + 12, oy + by1 + 16), "レンジ", font=font(F_HEAD, 38), fill=COLORS["blue"])
    draw_ribbon(im, g, x_now, oy, 1.0)
    d = ImageDraw.Draw(im)
    pts = [(x, oy + y) for x, y in clip_path_x(g["path"], x_now)]
    if len(pts) > 1:
        d.line(pts, fill=INK, width=7, joint="curve")
    if st >= 2:     # 切り下げライン
        (x0, y0), (x1, y1) = g["line"]
        p = ease((t - STAGES[2][1]) / 0.5)
        d.line((x0, oy + y0, x0 + (x1 - x0) * p, oy + y0 + (y1 - y0) * p), fill=(90, 90, 96), width=6)
    if st >= 3 and x_now >= g["entry"][0] - 1:   # エントリーと損切り
        x, y = g["entry"]
        p = ease((t - STAGES[3][2]) / 0.2)
        r = 15 * p
        d.ellipse((x - r, oy + y - r, x + r, oy + y + r), fill=COLORS["blue"], outline=(255, 255, 255), width=4)
        d.text((x + 34, oy + y - 4), "エントリー", font=font(F_HEAD, 34), fill=COLORS["blue"], anchor="lm",
               stroke_width=5, stroke_fill=BG)
        sx0, sx1, sy = g["stop"]
        xx = sx0
        while xx < sx0 + (sx1 - sx0) * p:
            d.line((xx, oy + sy, min(xx + 14, sx1), oy + sy), fill=COLORS["red"], width=5)
            xx += 24
        if p >= 1:
            d.text((sx1 + 10, oy + sy), "損切り", font=font(F_HEAD, 32), fill=COLORS["red"], anchor="lm")
    if st >= 4:     # トレンドチャネル
        p = ease((t - STAGES[4][1]) / 0.4)
        for (x0, y0), (x1, y1) in g["channel"]:
            d.line((x0, oy + y0, x0 + (x1 - x0) * p, oy + y0 + (y1 - y0) * p), fill=(90, 90, 96), width=5)
    if t >= STAGES[4][2]:
        x, y = g["exit"]
        d.text((x, oy + y + 50), "決済", font=font(F_HEAD, 38), fill=COLORS["green"], anchor="mm",
               stroke_width=5, stroke_fill=BG)
    # 段階の名前(図の右上。前の段階から切り替わるとき下から入る)
    p = ease((t - STAGES[st][1]) / 0.25)
    layer = Image.new("RGBA", (W, 90), (0, 0, 0, 0))
    ImageDraw.Draw(layer).text((50, 45 + 20 * (1 - p)), name, font=font(F_HEAD, 44), anchor="lm",
                               fill=INK + (int(255 * p),))
    im.paste(layer, (0, oy + 70), layer)     # 図の左上(レンジより上の空いた所)
    d = ImageDraw.Draw(im)
    d.text((W - 220, oy + by1 + 110), "模式図", font=font(F_TAG, 30), fill=(90, 96, 104), anchor="rm")
DIAGRAMS = {
    # 最初の図解(range_pullback_line)のレンジを右へ延ばし、押し目がレンジ上辺まで戻ってからエントリー(ユーザー指定 2026-10-28)
    "range_extended": {
        "dy": 150, "box": (90, 430, 800, 560), "range_end": 560,
        "path": [(60, 520), (130, 450), (190, 540), (260, 455), (330, 545), (400, 450), (470, 535), (560, 420),
                 (640, 330), (700, 360), (735, 345), (770, 428), (820, 330), (880, 270), (930, 290), (980, 215),
                 (1020, 225), (1040, 300)],
        "line": ((650, 300), (840, 420)), "entry": (790, 389), "stop": (720, 830, 452),
        "channel": (((790, 400), (1060, 160)), ((760, 330), (1040, 80))), "exit": (1040, 300), "ribbon": True, "exit_dy": 130,
    },
    # レンジ → 抜け → レンジ上限まで押し目 → 押し目の切り下げライン抜けでエントリー(損切りは押し目の下)→ トレンドチャネル → チャネル抜けで決済
    "range_retest": {
        "dy": 150, "box": (90, 430, 560, 560), "zone": (560, 430, 800, 560),
        "path": [(60, 520), (130, 450), (190, 540), (260, 455), (330, 545), (400, 450), (470, 535), (560, 440),
                 (620, 330), (660, 370), (690, 350), (730, 455), (790, 370), (850, 300), (880, 320), (940, 230),
                 (980, 250), (1030, 170), (1050, 250)],
        "line": ((600, 320), (800, 420)), "entry": (766, 403), "stop": (690, 790, 480),
        "channel": (((790, 383), (1060, 194)), ((790, 323), (1060, 134))), "exit": (1040, 208), "ribbon": True,
    },
    # レンジ → リボンごと上抜け → 押し目に切り下げライン → 抜けてエントリー → チャネル → 割れて決済(形だけ。価格ではない)
    "range_pullback_line": {
        "box": (90, 430, 560, 560),
        "path": [(60, 520), (130, 450), (190, 540), (260, 455), (330, 545), (400, 450), (470, 535), (560, 420),
                 (640, 330), (700, 360), (735, 345), (770, 395), (820, 330), (880, 270), (930, 290), (980, 215),
                 (1020, 225), (1040, 300)],
        "line": ((650, 300), (840, 420)), "entry": (808, 347),
        "channel": (((790, 400), (1060, 160)), ((760, 330), (1040, 80))), "exit": (1040, 300),
    }
}


def ribbon_lines(g):
    """模式図の値動き(折れ線)から、短期リボンの 2 本(遅れて追う移動平均)を作る。なぞった線があればそれを使う。"""
    if "ribbon_fast" in g:
        xs = np.arange(g["ribbon_fast"][0][0], g["ribbon_fast"][-1][0] + 1, 4)
        return xs, np.interp(xs, *zip(*g["ribbon_fast"])), np.interp(xs, *zip(*g["ribbon_slow"]))
    xs = np.arange(g["path"][0][0], g["path"][-1][0] + 1, 4)
    ys = np.interp(xs, [p[0] for p in g["path"]], [p[1] for p in g["path"]])
    def ma(n):     # 直近 n 点の平均(過去だけを見る)
        c = np.cumsum(np.insert(ys, 0, 0))
        return np.array([(c[i + 1] - c[max(0, i + 1 - n)]) / (i + 1 - max(0, i + 1 - n)) for i in range(len(ys))])
    return xs, ma(14), ma(28)


def draw_ribbon(im, g, x_now, oy, k):
    """短期リボン(帯)を、値動きが描けている所まで描く。上辺を抜けた所に丸と「リボンが抜ける」。"""
    xs, fast, slow = ribbon_lines(g)
    n = int(np.searchsorted(xs, x_now))
    if n < 2:
        return
    layer = Image.new("RGBA", im.size, (0, 0, 0, 0))
    dl = ImageDraw.Draw(layer)
    top = g["box"][1]
    for i in range(n - 1):     # 上向き(速い線が上)は赤、それ以外は青で帯を塗る
        up = fast[i] < slow[i]
        col = (220, 70, 60) if up else (60, 110, 200)
        dl.polygon([(xs[i], oy + fast[i]), (xs[i + 1], oy + fast[i + 1]), (xs[i + 1], oy + slow[i + 1]),
                    (xs[i], oy + slow[i])], fill=col + (70,))
    dl.line([(x, oy + y) for x, y in zip(xs[:n], fast[:n])], fill=(220, 70, 60, 255), width=5)
    dl.line([(x, oy + y) for x, y in zip(xs[:n], slow[:n])], fill=(60, 110, 200, 255), width=5)
    out = [i for i in range(n) if xs[i] > g.get("range_end", g["box"][2]) and max(fast[i], slow[i]) < top]
    if out:                    # 帯ごとレンジ上辺を抜けた最初の所
        i = out[0]
        cx, cy = xs[i], oy + (fast[i] + slow[i]) / 2
        dl.ellipse((cx - 44, cy - 44, cx + 44, cy + 44), outline=COLORS["red"] + (255,), width=7)
        if g.get("labels_below"):    # ボックスの下に文字を置き、丸から線で結ぶ
            yb = oy + g["box"][3] + 16
            dl.line((cx, cy + 44, cx, yb), fill=COLORS["red"] + (255,), width=3)
            dl.text((cx, yb + 4), "リボンがレンジを抜ける", font=font(F_HEAD, 34), fill=COLORS["red"] + (255,), anchor="ma")
        else:
            dl.multiline_text((cx - 52, cy + 10), "リボンが\nレンジを抜ける", font=font(F_HEAD, 34), fill=COLORS["red"] + (255,),
                              anchor="rd", align="right", stroke_width=5, stroke_fill=BG + (255,))
    im.paste(layer, (0, 0), layer)


SKETCH = {
    # ユーザーのスケッチ(2026-10-28): レンジの中でリボンが上がっていき、値動きは上に抜けて山 → レンジ右上の角(リボンが
    # 抜ける所)まで押す → 山からの切り下げラインを抜けてエントリー → 加速。座標は帯の中(幅 1080)
    "dy": 140, "box": (60, 330, 820, 560),
    "path": [(40, 520), (90, 545), (210, 345), (340, 550), (470, 350), (600, 548), (700, 200), (740, 290),
             (765, 265), (810, 335), (1040, 90)],
    "fast": [(70, 505), (300, 490), (520, 450), (700, 390), (810, 345), (1000, 190)],
    "slow": [(70, 535), (300, 520), (520, 485), (700, 420), (810, 362), (1000, 235)],
    "line": ((690, 190), (900, 430)), "ring": (810, 340), "stop": (770, 900, 385),
}


def draw_sketch(im, t, dur):
    g = SKETCH
    k = t / max(dur - 0.6, 0.1)
    oy = PANEL_Y + g["dy"]

    def P(x, y):               # 縦に 1.5 倍・横に 0.88 倍(右側にラベルの場所を空ける)
        return 40 + (x - 40) * 0.88, oy + 330 + (y - 330) * 1.5

    d = ImageDraw.Draw(im)
    (bx0, by0), (bx1, by1) = P(*g["box"][:2]), P(*g["box"][2:])
    bk = ease(k / 0.12)
    if bk > 0:
        d.rectangle((bx0, by0, bx0 + (bx1 - bx0) * bk, by1), fill=(214, 228, 245), outline=COLORS["blue"], width=5)
        d.text((bx0, by1 + 24), "レンジ", font=font(F_HEAD, 38), fill=COLORS["blue"])
    raw = poly_part(g["path"], (k - 0.1) / 0.72)
    x_now = raw[-1][0]
    xs = np.arange(g["fast"][0][0], g["fast"][-1][0] + 1, 4)
    fy = np.interp(xs, *zip(*g["fast"]))
    sy = np.interp(xs, *zip(*g["slow"]))
    n = int(np.searchsorted(xs, x_now))
    if n > 1:                  # リボン(2 本の線と帯)は値動きが描けている所まで
        layer = Image.new("RGBA", im.size, (0, 0, 0, 0))
        dl = ImageDraw.Draw(layer)
        top = [P(x, y) for x, y in zip(xs[:n], fy[:n])]
        bot = [P(x, y) for x, y in zip(xs[:n], sy[:n])]
        dl.polygon(top + bot[::-1], fill=(220, 70, 60, 70))
        dl.line(top, fill=(220, 70, 60, 255), width=5)
        dl.line(bot, fill=(60, 110, 200, 255), width=5)
        im.paste(layer, (0, 0), layer)
        d = ImageDraw.Draw(im)
        if k > 0.3:
            lx, ly = P(300, 505)
            d.text((lx - 30, by1 + 24), "リボン", font=font(F_HEAD, 38), fill=COLORS["red"])
            d.line((lx, by1 + 20, lx, ly), fill=COLORS["red"], width=3)
    if len(raw) > 1:
        d.line([P(x, y) for x, y in raw], fill=INK, width=8, joint="curve")
    rx, ry = P(*g["ring"])
    if x_now >= g["ring"][0]:  # レンジ右上の角(リボンが抜ける所)まで押した所
        p = ease((k - 0.62) / 0.08)
        r = 46 * (0.8 + 0.2 * p)
        d.ellipse((rx - r, ry - r, rx + r, ry + r), outline=COLORS["red"], width=7)
        d.line((rx, ry + r, rx, by1 + 18), fill=COLORS["red"], width=3)
        d.text((rx, by1 + 24), "リボンが抜けた所まで押す", font=font(F_HEAD, 34), fill=COLORS["red"], anchor="ma")
        (x0, y0), (x1, y1) = P(*g["line"][0]), P(*g["line"][1])
        p = ease((k - 0.64) / 0.1)
        d.line((x0, y0, x0 + (x1 - x0) * p, y0 + (y1 - y0) * p), fill=(90, 90, 96), width=6)
    if k > 0.76:               # 抜けてエントリー、損切りは押し目の下
        ex, ey = P(822, 322)
        d.ellipse((ex - 15, ey - 15, ex + 15, ey + 15), fill=COLORS["blue"], outline=(255, 255, 255), width=4)
        d.text((ex + 34, ey - 6), "エントリー", font=font(F_HEAD, 36), fill=COLORS["blue"], anchor="lm",
               stroke_width=5, stroke_fill=BG)
        (sx0, sy0), (sx1, _) = P(g["stop"][0], g["stop"][2]), P(g["stop"][1], g["stop"][2])
        xx = sx0
        while xx < sx1:
            d.line((xx, sy0, min(xx + 14, sx1), sy0), fill=COLORS["red"], width=5)
            xx += 24
        d.text((sx1 + 10, sy0), "損切り", font=font(F_HEAD, 34), fill=COLORS["red"], anchor="lm")
    if k > 0.92:               # 加速
        ax, ay = P(1000, 150)
        d.text((ax + 20, ay + 20), "加速", font=font(F_HEAD, 46), fill=COLORS["red"], anchor="lm",
               stroke_width=6, stroke_fill=BG)
    d.text((W - 40, by1 + 120), "模式図", font=font(F_TAG, 30), fill=(90, 96, 104), anchor="rm")


def draw_diagram(im, name, t, dur):
    if name == "sketch":
        return draw_sketch(im, t, dur)
    if name == "staged":
        return draw_staged(im, t, dur)
    if name.startswith("staged:"):           # "staged:0,1.8,3.6,5.6,7.3" = 各段階の開始秒
        starts = [float(v) for v in name.split(":")[1].split(",")]
        global STAGES
        base = STAGES
        STAGES = [(nm, s0, s0 + (t1 - t0), xa, xb) for (nm, t0, t1, xa, xb), s0 in zip(base, starts)]
        try:
            return draw_staged(im, t, dur)
        finally:
            STAGES = base
    g = DIAGRAMS_EXTRA[name]() if name in DIAGRAMS_EXTRA else DIAGRAMS[name]
    d = ImageDraw.Draw(im)
    k = t / max(dur - 0.6, 0.1)
    oy = PANEL_Y + g.get("dy", 0)
    if "zone" in g and k > 0.15:    # レンジの高さを右へ延ばす(押し目がレンジに戻る場所)
        zx0, zy0, zx1, zy1 = g["zone"]
        p = ease((k - 0.15) / 0.15)
        zx = zx0 + (zx1 - zx0) * p
        xx = zx0
        while xx < zx:
            for yy in (zy0, zy1):
                d.line((xx, oy + yy, min(xx + 16, zx), oy + yy), fill=COLORS["blue"], width=4)
            xx += 28
    bx0, by0, bx1, by1 = g["box"]
    bk = ease(k / 0.15)
    if bk > 0:      # レンジの帯を左から広げる
        d.rectangle((bx0, oy + by0, bx0 + (bx1 - bx0) * bk, oy + by1), fill=(198, 216, 236), outline=COLORS["blue"], width=5)
        if g.get("labels_below"):
            d.text((bx0 + 12, oy + by1 + 16), "レンジ", font=font(F_HEAD, 40), fill=COLORS["blue"])
        else:
            d.text((bx0 + 12, oy + by0 - 52), "レンジ", font=font(F_HEAD, 40), fill=COLORS["blue"])
    pts = [(x, oy + y) for x, y in poly_part(g["path"], (k - 0.1) / 0.75)]
    if g.get("ribbon") and len(pts) > 1:
        draw_ribbon(im, g, pts[-1][0], oy, k)
        d = ImageDraw.Draw(im)
    if len(pts) > 1:
        d.line(pts, fill=INK, width=8, joint="curve")
    x_now = pts[-1][0] if pts else 0
    done = poly_part(g["path"], (k - 0.1) / 0.75)[-1] == g["path"][-1]

    def due(k0, x_at, span=0.1):
        """線や印を出すか(0〜1)。follow_path の図は、値動きの線がその x まで来てから出す。"""
        if g.get("follow_path"):
            return 1.0 if done else min(1.0, max(0.0, (x_now - x_at) / 60))
        return min(1.0, max(0.0, (k - k0) / span)) if k > k0 else 0.0

    p = due(0.5, g["line"][0][0], 0.12)
    if p > 0:       # 押し目の切り下げライン
        (x0, y0), (x1, y1) = g["line"]
        p = ease(p)
        d.line((x0, oy + y0, x0 + (x1 - x0) * p, oy + y0 + (y1 - y0) * p), fill=(90, 90, 96), width=6)
    p = due(0.66, g["entry"][0], 0.08) if "stop" in g else 0
    if p > 0:       # 損切り(押し目の下)
        sx0, sx1, sy = g["stop"]
        p = ease(p)
        xx = sx0
        while xx < sx0 + (sx1 - sx0) * p:
            d.line((xx, oy + sy, min(xx + 14, sx1), oy + sy), fill=COLORS["red"], width=5)
            xx += 24
        if p >= 1:
            d.text((sx1 + 10, oy + sy), "損切り", font=font(F_HEAD, 36), fill=COLORS["red"], anchor="lm")
    if due(0.62, g["entry"][0], 0.06) > 0:
        x, y = g["entry"]
        r = 16 * ease(due(0.62, g["entry"][0], 0.06))
        d.ellipse((x - r, oy + y - r, x + r, oy + y + r), fill=COLORS["blue"], outline=(255, 255, 255), width=4)
        if g.get("dy"):    # 新しい図: 点の右下に置く(左はレンジを延ばした破線と重なる)
            d.text((x + 40, oy + y + 12), "エントリー", font=font(F_HEAD, 38), fill=COLORS["blue"], anchor="lm")
        else:
            d.text((x - 30, oy + y + 70), "エントリー", font=font(F_HEAD, 38), fill=COLORS["blue"], anchor="rm")
    p = due(0.72, g["channel"][0][0][0], 0.12)
    if p > 0:
        p = ease(p)
        for (x0, y0), (x1, y1) in g["channel"]:
            d.line((x0, oy + y0, x0 + (x1 - x0) * p, oy + y0 + (y1 - y0) * p), fill=(90, 90, 96), width=5)
    if (done if g.get("follow_path") else k > 0.95):
        x, y = g["exit"]
        d.text((x - 10, oy + y + g.get("exit_dy", 70 if g.get("dy") else 40)), "決済", font=font(F_HEAD, 40), fill=COLORS["green"], anchor="mm")
    d.text((W - 40, oy + PANEL_H - 40), "模式図", font=font(F_TAG, 32), fill=(90, 96, 104), anchor="rm")


def frame(sc, charts, i, t):
    s = sc["shots"][i]
    dur = s["dur"]
    vivid = charts.look == "vivid"
    k = ease_io(t / dur) if vivid else ease(t / dur)
    im = Image.new("RGB", (W, H), BG)
    head = None
    if s.get("diagram"):
        draw_diagram(im, s["diagram"], t, dur)
    elif "card" not in s:
        crop = s.get("crop", s.get("rect"))
        end = s.get("crop_end", s.get("rect_end", crop))
        cur = [a + (b - a) * k for a, b in zip(crop, end)]
        for tp in s.get("punch", []):     # 決め手の場面で一瞬寄って戻る
            q = min(1.0, max(0.0, (t - tp) / 0.4))
            cur[2] *= 1 - 0.07 * np.sin(np.pi * q)
        chart, head = source(sc, charts, s, t, cur)
        prev = sc["shots"][i - 1] if i else None
        same_view = prev and "card" not in prev and "diagram" not in prev and \
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
        draw_markers(im, s, t, cur)

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
    if s.get("cta"):            # 下の免責と同時に出す(ずらさない)
        centered(d, PANEL_Y + 120, s["cta"], font(F_HEAD, 58), COLORS["blue"])
    if s.get("rec_tag") and head is not None:
        hw, hh = head.size
        hm = (np.asarray(head).astype(np.float32) * np.array(BG, np.float32) / 255).astype(np.uint8)
        im.paste(Image.fromarray(hm).resize((round(hw * 1.3), round(hh * 1.3)), Image.LANCZOS), (40, PANEL_Y - 62))
    if s.get("label"):
        prev_label = sc["shots"][i - 1].get("label") if i else None
        p = 1.0 if not vivid or i == 0 or s["label"] == prev_label else ease(t / 0.28)   # 1 カット目は最初から出す
        f = font(F_HEAD, 84)
        ly = 186 if s.get("sub") else 210
        if p >= 1:
            centered(d, ly, s["label"], f, COLORS[s.get("color", "blue")])
        else:      # 役名が変わるときだけ、下から短く入る
            layer = Image.new("RGBA", (W, 140), (0, 0, 0, 0))
            ImageDraw.Draw(layer).text((W / 2 - f.getlength(s["label"]) / 2, 10 + 30 * (1 - p)), s["label"], font=f,
                                       fill=COLORS[s.get("color", "blue")] + (int(255 * p),))
            im.paste(layer, (0, ly - 10), layer)
    if s.get("sub"):    # 役名の下。役名は sub があるときだけ少し上げる(下の日時表示と重ねない)
        centered(d, 300, s["sub"], font(F_HEAD, 44), INK)
    if s.get("tag"):
        d.text((60, PANEL_Y - 56), s["tag"], font=font(F_TAG, 38), fill=(70, 76, 84))

    cap = s.get("caption", "")
    if sc.get("layout") == "tate" and s.get("tate"):
        tt = s["tate"]
        n = int(t * sc.get("type_cps", TYPE_CPS)) + 1 if s.get("type", True) else len(tt)
        draw_tate(im, tt, font(F_HEAD, 104), INK if s.get("color", "blue") != "red" else COLORS["red"], n,
                  s.get("tate_side", "left"))
        d = ImageDraw.Draw(im)
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
        src = s.get("img") or (f"録画 {s['rec'][0]}→{s['rec'][-1]}秒" if "rec" in s else
                               "模式図" if "diagram" in s else "文字のみ")
        info = f"#{i + 1} {t0:.1f}〜{t0 + s['dur']:.1f}秒  {src}\n" + s.get("note", "")
        for j, line in enumerate(wrap(info, f, pw - 16)[:10]):
            d.text((x + 8, y + ph + 6 + j * 22), line, font=f, fill=(20, 20, 20))
        t0 += s["dur"]
    sheet.save(out)
    print(f"{out} ({t0:.1f}秒・{n}カット)")


def sfx_track(sc):
    """各カットの "sfx"(効果音)・"say"(読み上げ)と台本の "bgm" を 1 本の音声にまとめる(すべて合成。外部素材なし)。
    "say": [["文", カット内の秒], ...]。読み上げの間は BGM を下げる。何もなければ None。"""
    events, says, t0 = [], [], 0.0
    for s in sc["shots"]:
        for name, at, vol in s.get("sfx", []):
            events.append((t0 + at, name, vol))
        for text, at in s.get("say", []):
            says.append((t0 + at, text))
        t0 += s["dur"]
    if not events and not says and not sc.get("bgm"):
        return None
    import se
    n_all = int((t0 + 1.5) * se.SR)
    mix = np.zeros(n_all)
    for at, name, vol in events:
        x = se.get(name) * vol
        i = int(at * se.SR)
        mix[i:i + len(x)] += x[:len(mix) - i]
    voice = np.zeros(n_all)
    if says:
        import narr_short
        assert narr_short.SR == se.SR
        speed = sc.get("say_speed", 1.25)
        for at, text in says:
            x = narr_short.tts(text, speed).astype(np.float64) / 32768
            i = int(at * se.SR)
            voice[i:i + len(x)] += x[:n_all - i]
        voice = voice / (np.max(np.abs(voice)) or 1) * 0.9
    if sc.get("bgm"):
        music = se.bgm(t0, sc["bgm"].get("bpm", 84)) * sc["bgm"].get("vol", 0.25)
        music = np.concatenate([music, np.zeros(n_all - len(music))])
        # 読み上げの間は BGM を下げる(前後 0.15 秒なめらかに)
        talk = (np.abs(voice) > 0.01).astype(float)
        w = int(0.15 * se.SR)
        talk = np.convolve(talk, np.ones(2 * w) / (2 * w), mode="same") > 0
        gain = np.where(talk, sc["bgm"].get("duck", 0.4), 1.0)
        gain = np.convolve(gain, np.ones(w) / w, mode="same")
        mix += music * gain
    mix += voice
    mix = mix[:int(t0 * se.SR)]
    if sc.get("loudness", {}).get("peak_dbtp") is not None and "lufs" not in sc["loudness"]:
        # ピークを目標(true peak の余裕 0.5dB を見て)まで上げる/下げる。YouTube は小さい音を上げないため
        target = 10 ** ((sc["loudness"]["peak_dbtp"] - 0.5) / 20)
        mix = mix * target / (np.max(np.abs(mix)) or 1)
    return mix, se


def render(sc, charts, out):
    track = sfx_track(sc)
    video = out if track is None else out + ".video.mp4"
    enc = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                            "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-crf", "18",
                            "-preset", "medium", "-pix_fmt", "yuv420p", "-movflags", "+faststart", video],
                           stdin=subprocess.PIPE)
    for i, s in enumerate(sc["shots"]):
        for fno in range(round(s["dur"] * FPS)):
            enc.stdin.write(frame(sc, charts, i, fno / FPS).tobytes())
    enc.stdin.close()
    enc.wait()
    if track is not None:      # 効果音を付けて書き出す
        mix, se = track
        wav = out + ".sfx.wav"
        se.write_wav(wav, mix)
        af = []
        if "lufs" in sc.get("loudness", {}):   # 統合ラウドネスを目標に合わせる(YouTube の目安 -14 LUFS・true peak -1 dBTP)
            L = sc["loudness"]
            af = ["-af", f"loudnorm=I={L['lufs']}:TP={L.get('peak_dbtp', -1.0)}:LRA=11"]
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", video, "-i", wav, "-c:v", "copy"] + af +
                       ["-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-shortest", "-movflags", "+faststart", out],
                       check=True)
        os.remove(video)
        os.remove(wav)
    print(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("script")
    ap.add_argument("--board")
    ap.add_argument("--out")
    a = ap.parse_args()
    sc = json.load(open(a.script, encoding="utf-8"))
    global FPS, F_HEAD, F_CAP, F_TAG, BG, PANEL_Y
    PANEL_Y = sc.get("panel_y", PANEL_Y)
    BG = tuple(sc.get("bg", BG))
    FPS = sc.get("fps", FPS)
    F_HEAD = os.path.join(HERE, "fonts", sc["font_head"]) if "font_head" in sc else F_HEAD
    F_CAP = os.path.join(HERE, "fonts", sc["font_cap"]) if "font_cap" in sc else F_CAP
    F_TAG = os.path.join(HERE, "fonts", sc["font_tag"]) if "font_tag" in sc else F_TAG
    charts = Charts(os.path.join(os.path.dirname(os.path.abspath(a.script)), sc["assets"]), sc.get("look"))
    charts.rec_path = lambda sc: os.path.join(charts.base, sc["rec_file"])
    if a.board:
        board(sc, charts, a.board)
    if a.out:
        render(sc, charts, a.out)


if __name__ == "__main__":
    main()
