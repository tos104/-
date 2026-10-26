#!/usr/bin/env python3
"""写真だけで作るリール(飲食・宿向け)。無音で書き出し、曲は投稿アプリで付ける。

スタイルは PLAYBOOK.md 4.85。乱数は固定(同じ台本からは毎回同じ映像)。

台本(JSON):
{
  "assets": "../../output/tangatable/assets",    # 台本からの相対パス
  "shots": [
    {"img": "a.jpg", "dur": 2.3, "cam": "pullback|push|pan", "layout": "full|band",
     "fx": "hook|count|wipe|cards|sparkle|cta", "trans": "whip|flash|rise|fade", ... 各 fx の値,
     "note": "なぜこのカットがあるか"}
  ]
}
  python3 photo_short.py script.json --board sb.png     # 絵コンテ(各カット 3 コマ。実際の画面と同じ合成)
  python3 photo_short.py script.json --out out.mp4
"""
import argparse, math, json, os, re, subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H, FPS = 1080, 1920, 30
HERE = os.path.dirname(os.path.abspath(__file__))
F_HEAD = os.path.join(HERE, "fonts", "ShipporiMincho-ExtraBold.ttf")
F_BODY = os.path.join(HERE, "fonts", "ShipporiMincho-Medium.ttf")
F_NOTE = os.path.join(HERE, "fonts", "MPLUSRounded1c-Bold.ttf")
CREAM, INK, ACCENT, WHITE = (245, 239, 230), (42, 33, 29), (142, 42, 34), (255, 255, 255)
ROSE = (233, 161, 150)  # 写真の上の強調色(ACCENT は暗い写真に沈むため明るくした)
TRANS = 0.25   # 切り替えの長さ(秒)
BAND_H = 1000  # 横長写真の帯の高さ
BAND_Y = 700   # 帯の上端(文字は帯より上の安全域 230〜650 に置く)


def font(path, size, _cache={}):
    if (path, size) not in _cache:
        _cache[path, size] = ImageFont.truetype(path, size)
    return _cache[path, size]


def out_cubic(k):
    k = min(1.0, max(0.0, k))
    return 1 - (1 - k) ** 3


def out_back(k, s=1.7):
    k = min(1.0, max(0.0, k)) - 1
    return 1 + k * k * ((s + 1) * k + s)


def prog(t, start, dur):
    return min(1.0, max(0.0, (t - start) / dur))


# ---------- 写真とカメラ ----------

def cover(img, w, h):
    s = max(w / img.width, h / img.height)
    img = img.resize((round(img.width * s), round(img.height * s)), Image.LANCZOS)
    x, y = (img.width - w) // 2, (img.height - h) // 2
    return img.crop((x, y, x + w, y + h))


class Shot:
    """写真 1 枚分の静的な層を先に作っておき、毎コマはカメラの切り出しだけ行う。"""

    def __init__(self, path, layout, cam):
        self.im = Image.open(path).convert("RGB")
        self.layout, self.cam = layout, cam
        if layout == "band":
            self.bg = cover(self.im, W, H).filter(ImageFilter.GaussianBlur(45)).point(lambda v: int(v * 0.42))
            bw = max(round(self.im.width * BAND_H / self.im.height), W)
            self.band = self.im.resize((bw, round(self.im.height * bw / self.im.width)), Image.LANCZOS)
        else:
            self.full = cover(self.im, round(W * 1.15), round(H * 1.15))

    def frame(self, t, dur):
        k = t / dur
        if self.layout == "band":
            img = self.bg.copy()
            b = self.band
            y0 = (b.height - BAND_H) // 2
            if self.cam == "pan":   # 帯の中で左から右へ流す
                x = round((b.width - W) * (0.1 + 0.9 * out_cubic(k)))
                crop = b.crop((x, y0, x + W, y0 + BAND_H))
            else:                   # 帯の中でゆっくり寄る
                s = 1 + 0.07 * k
                cw, ch = W / s, BAND_H / s
                x0, yy = (b.width - cw) / 2, (b.height - ch) / 2
                crop = b.resize((W, BAND_H), Image.BICUBIC, box=(x0, yy, x0 + cw, yy + ch))
            img.paste(crop, (0, BAND_Y))
            return img
        f = self.full
        s = {"pullback": 1.15 - 0.15 * out_cubic(k), "push": 1.0 + 0.08 * k}.get(self.cam, 1.0)
        cw, ch = W * 1.15 / s, H * 1.15 / s
        x0, y0 = (f.width - cw) / 2, (f.height - ch) / 2
        return f.resize((W, H), Image.BICUBIC, box=(x0, y0, x0 + cw, y0 + ch))


# ---------- 文字 ----------

def segments(line):
    return [(s.strip("{}"), s.startswith("{")) for s in re.split(r"(\{[^}]*\})", line) if s]


def text_layer(lines, size, color=WHITE, hot=ROSE, path=F_HEAD, shadow=True, gap=22):
    """複数行の文字(RGBA)。{} は強調色。影は柔らかく 1 枚だけ。"""
    f = font(path, size)
    widths = [sum(f.getlength(t) for t, _ in segments(ln)) for ln in lines]
    lw, lh = int(max(widths)) + 40, len(lines) * (size + gap) + 40
    im = Image.new("RGBA", (lw, lh), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for i, ln in enumerate(lines):
        x, y = (lw - widths[i]) / 2, 20 + i * (size + gap)
        for t, h in segments(ln):
            d.text((x, y), t, font=f, fill=(hot if h else color) + (255,))
            x += f.getlength(t)
    if shadow:
        sh = Image.new("RGBA", im.size, (0, 0, 0, 0))
        sh.putalpha(im.getchannel("A").filter(ImageFilter.GaussianBlur(10)).point(lambda a: int(a * 0.75)))
        sh.alpha_composite(im)
        im = sh
    return im


def put(canvas, layer, x, y, alpha=1.0, scale=1.0):
    """RGBA を中心 (x, y) に、透明度と拡大率つきで重ねる。"""
    if alpha <= 0:
        return
    if scale != 1.0:
        layer = layer.resize((max(1, round(layer.width * scale)), max(1, round(layer.height * scale))), Image.BICUBIC)
    if alpha < 1:
        layer = layer.copy()
        layer.putalpha(layer.getchannel("A").point(lambda a: int(a * alpha)))
    canvas.alpha_composite(layer, (round(x - layer.width / 2), round(y - layer.height / 2)))


def wipe(layer, k):
    """左から右へ文字を出す(マスクリビール)。"""
    out = layer.copy()
    m = Image.new("L", out.size, 0)
    ImageDraw.Draw(m).rectangle((0, 0, round(out.width * out_cubic(k)), out.height), fill=255)
    out.putalpha(Image.composite(out.getchannel("A"), m, m))
    return out


def top_shade(canvas, h=760, strength=150):
    """文字の下だけ暗くする(上から帯状に。画面中央は暗くしない)。"""
    g = np.linspace(strength, 0, h).astype(np.uint8)
    shade = Image.new("RGBA", (W, h), (0, 0, 0, 0))
    shade.putalpha(Image.fromarray(np.repeat(g[:, None], W, 1), "L"))
    canvas.alpha_composite(shade, (0, 0))


# ---------- 演出(fx) ----------

def fx_hook(c, t, sh):
    """縦書きの 1 行目を 1 文字ずつ、2 行目は横書きで大きく。"""
    top_shade(c, 900, 120)
    x, y = 900, 250
    for i, ch in enumerate(sh["vertical"]):
        k = prog(t, 0.05 + i * 0.07, 0.25)
        if k <= 0:
            break
        dx, dy = (52, -58) if ch in "、。" else (0, 0)  # 縦書きの句読点は右上へ(横書き用の字形は左下にあるため)
        put(c, text_layer([ch], 86, gap=0), x + dx, y + i * 96 + dy + 18 * (1 - out_cubic(k)), alpha=out_cubic(k))
    k = prog(t, 0.65, 0.35)
    lay = text_layer([sh["horizontal"]], 104, color=CREAM, hot=CREAM)
    put(c, lay, 540, 1010, alpha=out_cubic(k), scale=1.12 - 0.12 * out_back(k))
    k2 = prog(t, 0.85, 0.4)  # 下線を引く
    if k2 > 0:
        x0 = 540 - lay.width / 2 + 30
        ImageDraw.Draw(c).line((x0, 1085, x0 + (lay.width - 60) * out_cubic(k2), 1085), fill=CREAM + (230,), width=4)


def fx_count(c, t, sh):
    """人数を数え上げる。2 つの数字の間に縦線を引く。"""
    top_shade(c, 720, 140)
    for i, (label, n, unit) in enumerate(sh["nums"]):
        cx = 300 + i * 480
        v = round(n * out_cubic(prog(t, 0.1 + i * 0.15, 0.9)))
        put(c, text_layer([label], 52, path=F_BODY), cx, 300, alpha=out_cubic(prog(t, i * 0.15, 0.25)))
        num = text_layer([f"{v}"], 190, color=CREAM)
        put(c, num, cx - 30, 470, alpha=out_cubic(prog(t, 0.1 + i * 0.15, 0.2)))
        put(c, text_layer([unit], 64, color=CREAM), cx + num.width / 2 - 10, 520,
            alpha=out_cubic(prog(t, 0.8 + i * 0.15, 0.2)))
    k = prog(t, 0.2, 0.5)
    if k > 0:
        ImageDraw.Draw(c).line((540, 300, 540, 300 + 260 * out_cubic(k)), fill=CREAM + (200,), width=3)


def fx_wipe(c, t, sh):
    """行ごとに左から右へ出す。"""
    top_shade(c, 720, 140)
    for i, ln in enumerate(sh["text"]):
        k = prog(t, 0.1 + i * 0.25, 0.4)
        if k > 0:
            put(c, wipe(text_layer([ln], 92, color=CREAM), k), 540, 330 + i * 130)


def polaroid(img, caption, size=440):
    card = Image.new("RGBA", (size + 44, size + 120), (252, 250, 246, 255))
    card.paste(cover(img, size, size), (22, 22))
    f = font(F_BODY, 38)
    ImageDraw.Draw(card).text(((card.width - f.getlength(caption)) / 2, size + 40), caption, font=f, fill=INK)
    return card


def fx_cards(c, t, sh, cache={}):
    """紙の上に、料理のカードを 1 枚ずつ落とす。値段は判子のように押す。"""
    key = id(sh)
    if key not in cache:
        rng = np.random.default_rng(7)
        paper = np.clip(np.array(CREAM, np.float32) + rng.normal(0, 4, (H, W, 1)), 0, 255).astype(np.uint8)
        cards = []
        for (img, cap), rot in zip(sh["cards"], (-6, 5, -2)):
            p = polaroid(Image.open(os.path.join(sh["_root"], img)).convert("RGB"), cap)
            s = Image.new("RGBA", (p.width + 80, p.height + 80), (0, 0, 0, 0))
            s.paste((0, 0, 0, 90), (40, 52, 40 + p.width, 52 + p.height))
            s = s.filter(ImageFilter.GaussianBlur(16))
            s.alpha_composite(p, (40, 40))
            cards.append(s.rotate(rot, Image.BICUBIC, expand=True))
        cache[key] = (Image.fromarray(paper).convert("RGBA"), cards)
    paper, cards = cache[key]
    c.alpha_composite(paper)
    for i, (card, (x, y)) in enumerate(zip(cards, ((290, 930), (790, 1190), (390, 1470)))):
        k = prog(t, 0.45 + i * 0.75, 0.35)
        if k > 0:
            put(c, card, x, y - 60 * (1 - out_cubic(k)), alpha=min(1, k * 2), scale=1.25 - 0.25 * out_back(k))
    put(c, text_layer(["税込"], 50, color=INK, path=F_BODY, shadow=False), 540, 270, alpha=out_cubic(prog(t, 0, 0.25)))
    k = prog(t, 0.08, 0.3)
    put(c, text_layer([sh["price"]], 170, color=ACCENT, shadow=False), 540, 400, alpha=min(1, k * 2.5),
        scale=1.5 - 0.5 * out_back(k, 1.2))
    put(c, wipe(text_layer([sh["sub"]], 70, color=INK, hot=ACCENT, shadow=False), prog(t, 0.35, 0.45)), 540, 560)


def fx_sparkle(c, t, sh):
    """乾杯の上で光が瞬く。文字は 1 行ずつ下から。"""
    top_shade(c, 720, 150)
    rng = np.random.default_rng(3)
    d = ImageDraw.Draw(c)
    for _ in range(16):
        x, y = rng.uniform(200, 900), rng.uniform(820, 1400)
        ph, r = rng.uniform(0, 2 * math.pi), rng.uniform(14, 30)
        a = max(0.0, math.sin(t * 5 + ph)) * prog(t, 0.2, 0.3)
        if a > 0.05:
            rr, q = r * (0.6 + 0.4 * a), r * 0.18
            d.polygon([(x, y - rr), (x + q, y - q), (x + rr, y), (x + q, y + q),
                       (x, y + rr), (x - q, y + q), (x - rr, y), (x - q, y - q)], fill=(255, 248, 225, int(230 * a)))
    for i, ln in enumerate(sh["text"]):
        k = prog(t, 0.1 + i * 0.3, 0.4)
        put(c, text_layer([ln], 92, color=CREAM), 540, 340 + i * 130 + 30 * (1 - out_cubic(k)), alpha=out_cubic(k))


def fx_cta(c, t, sh):
    """締切を出し、予約のハイライトの丸を描いて終える。"""
    top_shade(c, 720, 160)
    put(c, text_layer([sh["text"][0]], 88, color=CREAM), 540, 300, alpha=out_cubic(prog(t, 0.05, 0.35)))
    k = prog(t, 0.45, 0.6)
    cx, cy, r = 220, 520, 78
    if k > 0:
        d = ImageDraw.Draw(c)
        d.arc((cx - r, cy - r, cx + r, cy + r), -90, -90 + 360 * out_cubic(k), fill=ACCENT + (255,), width=10)
        d.ellipse((cx - r + 14, cy - r + 14, cx + r - 14, cy + r - 14), fill=CREAM + (int(255 * out_cubic(k)),))
        put(c, text_layer([sh["ring"]], 44, color=INK, shadow=False), cx, cy, alpha=out_cubic(prog(t, 0.8, 0.3)))
    put(c, text_layer([sh["text"][1]], 64, color=CREAM, path=F_BODY), 650, 520, alpha=out_cubic(prog(t, 0.9, 0.35)))


FX = {"hook": fx_hook, "count": fx_count, "wipe": fx_wipe, "cards": fx_cards, "sparkle": fx_sparkle, "cta": fx_cta}


# ---------- 切り替え ----------

def transition(kind, prev, cur, k):
    if prev is None or k >= 1:
        return cur
    e = out_cubic(k)
    if kind == "whip":     # 横に流れる(流れている間だけぼかす)
        blur = 30 * (1 - abs(2 * k - 1))
        img = Image.new("RGB", (W, H))
        img.paste(prev, (round(-W * e), 0))
        img.paste(cur, (round(W * (1 - e)), 0))
        return img.filter(ImageFilter.BoxBlur(blur)) if blur > 1 else img
    if kind == "flash":    # 白く飛ばしてから戻す
        return Image.blend(cur, Image.new("RGB", (W, H), WHITE), 0.85 * (1 - e))
    if kind == "rise":     # 次の画面が下からせり上がる
        img = prev.copy()
        img.paste(cur, (0, round(H * (1 - e))))
        return img
    return Image.blend(prev, cur, e)  # fade


# ---------- 書き出し ----------

def render(sc, root, times=None):
    """全コマを (カット番号, 秒, 画像) で返す。times を渡すと、その時刻のコマだけ(絵コンテ用)。"""
    total, prev_last = 0.0, None
    for idx, sh in enumerate(sc["shots"]):
        sh = dict(sh, _root=root)
        shot = Shot(os.path.join(root, sh["img"]), sh.get("layout", "full"), sh.get("cam", "push"))
        n = round(sh["dur"] * FPS)

        def draw(i):
            t = i / FPS
            c = shot.frame(t, sh["dur"]).convert("RGBA")
            FX[sh["fx"]](c, t, sh)
            img = c.convert("RGB")
            if sh.get("trans") and t < TRANS:
                img = transition(sh["trans"], prev_last, img, t / TRANS)
            return img

        frames = range(n) if times is None else sorted({min(n - 1, round(x * FPS)) for x in times[idx]})
        for i in frames:
            yield idx, total + i / FPS, draw(i)
        prev_last = draw(n - 1)
        total += n / FPS


def board(sc, root, out):
    """各カット 3 コマ(入り・途中・終わり)と、秒・演出・理由を並べる。"""
    times = [(0.12, sh["dur"] * 0.45, sh["dur"] - 0.05) for sh in sc["shots"]]
    got = {}
    for idx, t, img in render(sc, root, times):
        got.setdefault(idx, []).append((t, img))
    tw, th = 216, 384
    rowh = th + 50
    sheet = Image.new("RGB", (40 + 3 * (tw + 14) + 520, 30 + len(sc["shots"]) * rowh), (250, 250, 247))
    d = ImageDraw.Draw(sheet)
    fn, fb = font(F_NOTE, 22), font(F_NOTE, 26)
    start = 0.0
    for r, sh in enumerate(sc["shots"]):
        y = 30 + r * rowh
        for j, (t, img) in enumerate(got[r]):
            x = 20 + j * (tw + 14)
            sheet.paste(img.resize((tw, th), Image.LANCZOS), (x, y))
            d.text((x, y + th + 4), f"{t:.2f}s", font=fn, fill=(90, 90, 90))
        x = 20 + 3 * (tw + 14) + 10
        d.text((x, y), f"{start:.1f}s〜（{sh['dur']}秒）", font=fb, fill=(20, 20, 20))
        info = [f"写真: {sh['img']}", f"カメラ: {sh.get('cam', 'push')}・{sh.get('layout', 'full')}",
                f"演出: {sh['fx']}" + (f" / 入り: {sh['trans']}" if sh.get("trans") else "")]
        note = sh.get("note", "")
        info += [note[i:i + 20] for i in range(0, len(note), 20)]
        for j, ln in enumerate(info):
            d.text((x, y + 40 + j * 30), ln, font=fn, fill=(60, 60, 60))
        start += round(sh["dur"] * FPS) / FPS
    sheet.save(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("script")
    ap.add_argument("--out")
    ap.add_argument("--board")
    a = ap.parse_args()
    sc = json.load(open(a.script, encoding="utf-8"))
    root = os.path.join(os.path.dirname(os.path.abspath(a.script)), sc["assets"])
    if a.board:
        board(sc, root, a.board)
        print(a.board)
    if a.out:
        os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
        enc = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                                "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-crf", "17",
                                "-pix_fmt", "yuv420p", "-movflags", "+faststart", a.out], stdin=subprocess.PIPE)
        n = 0
        for _, _, img in render(sc, root):
            enc.stdin.write(img.tobytes())
            n += 1
        enc.stdin.close()
        enc.wait()
        print(f"{a.out} ({n / FPS:.1f}s, {len(sc['shots'])} shots, 無音)")


if __name__ == "__main__":
    main()
