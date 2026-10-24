#!/usr/bin/env python3
"""3段レイアウトのショート(上=見出し2行 / 中=元動画を横長のまま / 下=解説パネル)。本人の声・ジェットカット。

参考: ユーザー提供の見本(2026-10-24, 720x1280)を実測して 1080x1920 に拡大した寸法と色。

設計図(JSON):
{
  "speed": 1.0,
  "beats": [                                     # 見出しとパネルが変わる区切り
    {"cuts": [{"a": ["15:54.0", "15:58.05"], "v": "14:45.0", "jet": false, "zoom": [285, 190, 1.6]}],
     "head": ["30万で買った青眼が", "{化けるか！？}"], "tone": "red",      # 2行目の {} を強調色に
     "panel": {"pill": "30万 → 130万", "above": "", "below": "の勝負", "foot": "※撮影時の紹介相場", "pill_tone": "green"},
     "open": true,                                # 冒頭用: 背景に集中線
     "say": "30万か130万かのチャレンジ…せーの",    # 絵コンテ用(元動画の声)
     "why": "最初の1秒で賭け金を見せる"},
    {"panel": {"thumb": ["15:00.0", 190, 50, 190, 280], "lines": ["PSA10が150万の頃に", "{30万}で買えた"], "foot": "※本人談"}}
  ]
}
  python3 panel_short.py plan.json source.mp4 --board board.png   # 絵コンテ(実際の画面と同じ合成)
  python3 panel_short.py plan.json source.mp4 --out out.mp4
"""
import argparse, json, math, os, re, subprocess, tempfile
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import se
import rich_short as rs
from make_short import to_sec

SR = rs.SR
W, H = 1080, 1920
BAND = (400, 1110)          # 黒い帯
VID_Y, VID_H = 451, 608     # 元動画(16:9)
PANEL = (1110, 1590)
HERE = os.path.dirname(os.path.abspath(__file__))
F_HEAD = os.path.join(HERE, "fonts", "MPLUSRounded1c-ExtraBold.ttf")
F_BODY = os.path.join(HERE, "fonts", "MPLUSRounded1c-Bold.ttf")
F_BIG = os.path.join(HERE, "fonts", "MPLUSRounded1c-Black.ttf")
CREAM, EDGE_TOP, EDGE_BOT = (239, 239, 230), (186, 187, 172), (182, 183, 174)
INK, SUB = (26, 56, 48), (120, 126, 120)
TONE = {"red": (180, 35, 44), "green": (32, 96, 64)}
PILL = {"green": (210, 234, 96), "orange": (240, 192, 120)}
JET_MIN, JET_PAD = 0.15, 0.03


def font(path, size):
    return ImageFont.truetype(path, size)


def rich(d, cy, text, f, base, accent):
    """{...} を強調色にして、中央揃えで 1 行描く。"""
    parts = [(p.strip("{}"), accent if p.startswith("{") else base) for p in re.split(r"(\{.+?\})", text) if p]
    x = (W - sum(d.textlength(p, font=f) for p, _ in parts)) / 2
    for p, c in parts:
        d.text((x, cy), p, font=f, fill=c, anchor="lm")
        x += d.textlength(p, font=f)


def fit(d, text, path, size, width):
    while d.textlength(re.sub(r"[{}]", "", text), font=font(path, size)) > width and size > 30:
        size -= 2
    return font(path, size)


def grab(source, t, box=None):
    """元動画の 1 コマ(必要なら切り抜き)。"""
    with tempfile.NamedTemporaryFile(suffix=".png") as f:
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{to_sec(t):.3f}", "-i", source,
                        "-frames:v", "1", f.name], check=True)
        im = Image.open(f.name).convert("RGB")
        im.load()
    if box:
        x, y, w, h = box
        im = im.crop((x, y, x + w, y + h))
    return im


def background(open_lines=False):
    img = Image.new("RGB", (W, H), CREAM)
    px = np.array(img).astype(np.float32)
    y = np.arange(H)[:, None]
    top = np.clip(1 - y / 150, 0, 1)[..., None]
    bot = np.clip((y - PANEL[1]) / (H - PANEL[1]), 0, 1)[..., None]
    px = px * (1 - top) + np.array(EDGE_TOP) * top
    px = px * (1 - bot) + np.array(EDGE_BOT) * bot
    img = Image.fromarray(px.astype(np.uint8))
    if open_lines:  # 集中線(乱数は固定)
        rng = np.random.default_rng(7)
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(lay)
        cx, cy = W / 2, (BAND[0] + BAND[1]) / 2
        for k in range(90):
            a = 2 * math.pi * k / 90 + rng.uniform(-0.02, 0.02)
            r0, r1 = rng.uniform(560, 760), 1500
            w = rng.uniform(0.006, 0.016)
            pts = [(cx + r1 * math.cos(a - w), cy + r1 * math.sin(a - w)),
                   (cx + r0 * math.cos(a), cy + r0 * math.sin(a)),
                   (cx + r1 * math.cos(a + w), cy + r1 * math.sin(a + w))]
            d.polygon(pts, fill=(150, 152, 140, 150))
        img = Image.alpha_composite(img.convert("RGBA"), lay).convert("RGB")
    return img


def overlay(beat, source):
    """1 区切り分の静止レイヤー(帯の中は黒。動画は後から重ねる)。"""
    img = background(beat.get("open"))
    d = ImageDraw.Draw(img)
    d.rectangle((0, BAND[0], W, BAND[1]), fill=(0, 0, 0))
    l1, l2 = beat["head"]
    tone = TONE[beat.get("tone", "green")]
    rich(d, 215, l1, fit(d, l1, F_HEAD, 70, W - 120), INK, tone)
    rich(d, 318, l2, fit(d, l2, F_BIG, 100, W - 100), tone, tone)

    p = beat.get("panel", {})
    # パネルの中身は縦方向の中央にそろえる(先に高さを測る)
    pill_f = fit(d, p["pill"], F_BIG, p.get("pill_size", 96), W - 260) if p.get("pill") else None
    hgt = ((240 + 50) if p.get("thumb") else 0) + (95 if p.get("above") else 0) \
        + ((int(pill_f.size * 1.55) + 45) if pill_f else 0) + 92 * len(p.get("lines", [])) \
        + (90 if p.get("below") else 0) + (45 if p.get("foot") else 0)
    y = PANEL[0] + max(30, (PANEL[1] - PANEL[0] - hgt) // 2)
    if p.get("thumb"):
        t, *box = p["thumb"]
        th = grab(source, t, box)
        th = th.resize((int(th.width * 240 / th.height), 240), Image.LANCZOS)
        sh = Image.new("RGBA", (th.width + 30, th.height + 30), (0, 0, 0, 0))
        ImageDraw.Draw(sh).rectangle((15, 19, th.width + 15, th.height + 19), fill=(0, 0, 0, 70))
        sh = sh.filter(ImageFilter.GaussianBlur(6))
        x = (W - th.width) // 2
        img.paste(sh, (x - 15, y - 15), sh)
        img.paste(th, (x, y))
        y += 240 + 50
    if p.get("above"):
        rich(d, y + 35, p["above"], font(F_HEAD, 62), INK, TONE["red"]); y += 95
    if pill_f:
        tw = d.textlength(p["pill"], font=pill_f)
        ph = int(pill_f.size * 1.55)
        x0 = (W - tw) / 2 - 48
        d.rounded_rectangle((x0, y, W - x0, y + ph), radius=24, fill=PILL[p.get("pill_tone", "green")])
        d.text((W / 2, y + ph / 2 + 2), p["pill"], font=pill_f, fill=TONE["green"], anchor="mm")
        y += ph + 45
    for k, line in enumerate(p.get("lines", [])):
        f = font(F_HEAD, 74 if k else 62)
        rich(d, y + 40, line, f, INK, TONE[p.get("tone", "red")]); y += 92
    if p.get("below"):
        rich(d, y + 35, p["below"], font(F_HEAD, 66), INK, INK); y += 90
    if p.get("foot"):
        d.text((W / 2, y + 20), p["foot"], font=font(F_BODY, 32), fill=SUB, anchor="mm")
    return img


def vid_filter(beat_cut, src_w, src_h, speed):
    z = beat_cut.get("zoom")
    if z:
        cx, cy, k = z
        cw, ch = int(src_w / k) // 2 * 2, int(src_h / k) // 2 * 2
        x = min(max(cx - cw / 2, 0), src_w - cw); y = min(max(cy - ch / 2, 0), src_h - ch)
        crop = f"crop={cw}:{ch}:{x:.0f}:{y:.0f},"
    else:
        crop = ""
    return f"{crop}scale={W}:{VID_H}:flags=lanczos,unsharp=5:5:0.4,setpts=PTS/{speed},fps=30"


def board(plan, source, out):
    """実際の合成と同じ画面で、各区切りの 1 コマを並べる。"""
    src_w, src_h = rs.probe(source)
    tiles = []
    for i, b in enumerate(plan["beats"]):
        img = overlay(b, source)
        c = b["cuts"][0]
        t = c.get("v", c["a"][0])
        fr = grab(source, to_sec(t) + b.get("board_dt", 0.5))
        z = c.get("zoom")
        if z:
            cx, cy, k = z
            cw, ch = src_w / k, src_h / k
            x = min(max(cx - cw / 2, 0), src_w - cw); y = min(max(cy - ch / 2, 0), src_h - ch)
            fr = fr.crop((int(x), int(y), int(x + cw), int(y + ch)))
        img.paste(fr.resize((W, VID_H), Image.LANCZOS), (0, VID_Y))
        tile = Image.new("RGB", (W // 3, H // 3 + 260), "white")
        tile.paste(img.resize((W // 3, H // 3), Image.LANCZOS), (0, 0))
        d = ImageDraw.Draw(tile)
        fb = font(F_BODY, 22)
        txt = [f"#{i + 1}  元 {c['a'][0]}〜{b['cuts'][-1]['a'][1]}", "声: " + b.get("say", ""), "狙い: " + b.get("why", "")]
        yy = H // 3 + 10
        for s in txt:
            line = ""
            for ch in s:
                if d.textlength(line + ch, font=fb) > W // 3 - 20:
                    d.text((10, yy), line, font=fb, fill=(40, 40, 40)); yy += 30; line = ch
                else:
                    line += ch
            d.text((10, yy), line, font=fb, fill=(40, 40, 40)); yy += 34
        tiles.append(tile)
    cols = 5
    rows = math.ceil(len(tiles) / cols)
    tw, th = tiles[0].size
    sheet = Image.new("RGB", (cols * (tw + 16) + 16, rows * (th + 16) + 16), (225, 225, 220))
    for k, t in enumerate(tiles):
        sheet.paste(t, (16 + (k % cols) * (tw + 16), 16 + (k // cols) * (th + 16)))
    sheet.save(out)
    print(out, sheet.size)


def render(plan, source, out):
    speed = plan.get("speed", 1.0)
    src_w, src_h = rs.probe(source)
    rs.JET_MIN, rs.JET_PAD = JET_MIN, JET_PAD
    with tempfile.TemporaryDirectory() as td:
        parts, audio, t = [], [], 0.0
        for i, b in enumerate(plan["beats"]):
            bg = os.path.join(td, f"bg{i:02d}.png")
            overlay(b, source).save(bg)
            for j, c in enumerate(b["cuts"]):
                a0, a1 = to_sec(c["a"][0]), to_sec(c["a"][1])
                spans = rs.speech_spans(source, a0, a1) if c.get("jet", True) else [(a0, a1)]
                voice = np.concatenate([rs.source_audio(source, s0, s1) for s0, s1 in spans])
                vsegs = [(to_sec(c["v"]), to_sec(c["v"]) + len(voice) / SR)] if c.get("v") else spans
                frames = 0
                for k, (v0, v1) in enumerate(vsegs):
                    d = v1 - v0
                    n = max(1, round(d / speed * 30))
                    p = os.path.join(td, f"p{i:02d}_{j:02d}_{k:02d}.mp4")
                    fc = (f"[1:v]{vid_filter(c, src_w, src_h, speed)},tpad=stop_mode=clone:stop_duration=1[v];"
                          f"[0:v][v]overlay=0:{VID_Y},format=yuv420p")
                    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-framerate", "30", "-i", bg,
                                    "-ss", f"{v0:.3f}", "-t", f"{d + 0.2:.3f}", "-i", source, "-an",
                                    "-filter_complex", fc, "-frames:v", str(n), "-c:v", "libx264", "-crf", "16", p],
                                   check=True)
                    parts.append(p)
                    frames += n
                audio.append((t, voice, c.get("se")))
                t += frames / 30
        total = t
        mix = np.zeros(int((total + 0.5) * SR), np.float32)
        for at, v, name in audio:
            raw = os.path.join(td, "v.wav"); fast = os.path.join(td, "f.raw")
            se.write_wav(raw, v)
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", raw, "-af", f"atempo={speed}",
                            "-ac", "1", "-ar", str(SR), "-f", "s16le", fast], check=True)
            x = np.fromfile(fast, np.int16).astype(np.float32) / 32768
            i0 = int(at * SR); mix[i0:i0 + len(x)] += x[: len(mix) - i0]
            if name:
                s_ = se.get(name) * 0.3
                mix[i0:i0 + len(s_)] += s_[: len(mix) - i0]
        mix = mix[: int(total * SR)]
        mix /= max(1.0, np.abs(mix).max() / 0.95)
        wav = os.path.join(td, "mix.wav"); se.write_wav(wav, mix)
        lst = os.path.join(td, "list.txt")
        open(lst, "w").write("".join(f"file '{p}'\n" for p in parts))
        os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst, "-i", wav,
                        "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-crf", "19", "-pix_fmt", "yuv420p",
                        "-af", "loudnorm=I=-14:TP=-1.0:LRA=11", "-c:a", "aac", "-b:a", "192k", "-shortest",
                        "-movflags", "+faststart", out], check=True)
    print(f"{out} ({total:.1f}s)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("plan")
    ap.add_argument("source")
    ap.add_argument("--out")
    ap.add_argument("--board")
    a = ap.parse_args()
    plan = json.load(open(a.plan, encoding="utf-8"))
    if a.board:
        board(plan, a.source, a.board)
    if a.out:
        render(plan, a.source, a.out)


if __name__ == "__main__":
    main()
