#!/usr/bin/env python3
"""同じ素材で、構成とデザインがまったく違う絵コンテ・動画を複数案つくる。

  python3 storyboard_variants.py plan.json source.mp4 --out-dir output/            # 絵コンテ(静止画の見本)
  python3 storyboard_variants.py plan.json source.mp4 --out-dir output/ --video A B # 動画も書き出す
plan.json: {"name", "variants": [{"key","name","structure","design",
            "beats":[{"t","cx","cy","zoom","cuts":[{"a":[開始,終了],"jet","se"}],"texts":{...},"say"}]}]}
各案は「上に重ねる絵(RGBA)」と「元動画を流す枠(slot)」に分けて描く。静止画は枠に1コマを貼り、動画は枠に元動画を流す。
デザインは key ごと(A 全画面 / B 上下分割 / C クイズ / D レシート / E 吹き出し)。数字・発言は設計図に書いたものだけ。
"""
import argparse, json, os, subprocess, tempfile
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
import se
import rich_short as rs
import panel_short as ps
from make_short import to_sec

HERE = os.path.dirname(os.path.abspath(__file__))
F = {k: os.path.join(HERE, "fonts", v) for k, v in {
    "dela": "DelaGothicOne-Regular.ttf", "black": "MPLUSRounded1c-Black.ttf",
    "xb": "MPLUSRounded1c-ExtraBold.ttf", "bold": "MPLUSRounded1c-Bold.ttf"}.items()}
W, H = 1080, 1920
SR = rs.SR
_cache = {}


def font(k, s):
    return ImageFont.truetype(F[k], s)


def frame(src, t):
    if t not in _cache:
        with tempfile.NamedTemporaryFile(suffix=".png") as f:
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{t:.2f}", "-i", src, "-frames:v", "1", f.name], check=True)
            im = Image.open(f.name).convert("RGB"); im.load()
        _cache[t] = im
    return _cache[t]


def crop_box(sw, sh, w, h, cx=320, cy=180, zoom=1.0):
    """元動画(sw x sh)から w:h の比で切り抜く範囲(x, y, cw, ch)。"""
    ch = sh / zoom
    cw = ch * w / h
    if cw > sw:
        cw = sw; ch = cw * h / w
    x = min(max(cx - cw / 2, 0), sw - cw); y = min(max(cy - ch / 2, 0), sh - ch)
    return int(x), int(y), int(cw) // 2 * 2, int(ch) // 2 * 2


def slot(t, x, y, w, h, b, **kw):
    """元動画を流す枠。kw: cx, cy, zoom, blur, dim(0〜1)。"""
    s = {"t": t, "x": x, "y": y, "w": w, "h": h, "cx": b.get("cx", 320), "cy": b.get("cy", 180), "zoom": b.get("zoom", 1.0)}
    s.update(kw)
    return s


def ctext(d, xy, text, f, fill, stroke=0, sfill=(0, 0, 0), anchor="mm"):
    d.text(xy, text, font=f, fill=fill, anchor=anchor, stroke_width=stroke, stroke_fill=sfill)


def hole(img, box, shape="rect"):
    """不透明な絵に、元動画が見える穴をあける。"""
    m = Image.new("L", img.size, 255)
    md = ImageDraw.Draw(m)
    (md.ellipse if shape == "circle" else md.rectangle)(box, fill=0)
    img.putalpha(Image.fromarray(np.minimum(np.array(img.getchannel("A")), np.array(m))))


# ---- A: 全画面ドキュメント(縦いっぱいの映像+下に大きな字幕+左上に小さな章) ----
def layer_A(b):
    tx = b["texts"]
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    for i in range(700):
        d.line((0, H - i, W, H - i), fill=(0, 0, 0, int(200 * (1 - i / 700))))
    if tx.get("chapter"):
        d.rounded_rectangle((60, 120, 60 + d.textlength(tx["chapter"], font=font("bold", 40)) + 50, 190), radius=35, fill=(255, 255, 255))
        d.text((85, 155), tx["chapter"], font=font("bold", 40), fill=(20, 20, 20), anchor="lm")
    for k, line in enumerate(tx.get("cap", [])):
        ctext(d, (W / 2, H - 430 + k * 120), line, font("black", 92 if k else 78), (255, 230, 0) if k else (255, 255, 255), 6)
    return img, [slot(b["t"], 0, 0, W, H, b)]


# ---- B: 上下分割(上=過去、下=今。結果から巻き戻す) ----
def layer_B(b):
    tx = b["texts"]
    img = Image.new("RGBA", (W, H), (16, 16, 18, 255))
    hole(img, (0, 90, W - 1, 949)); hole(img, (0, 970, W - 1, 1829))
    d = ImageDraw.Draw(img)
    for (y0, flag) in [(90, tx.get("dim_top")), (970, tx.get("dim_bot"))]:
        if flag:
            d.rectangle((0, y0, W, y0 + 860), fill=(0, 0, 0, 140))
    d.rectangle((0, 950, W, 970), fill=(255, 255, 255))
    for (y, lab, col) in [(90, tx.get("tag_top", "BEFORE"), (90, 90, 96)), (970, tx.get("tag_bot", "AFTER"), (220, 40, 50))]:
        d.rectangle((0, y, 300, y + 80), fill=col)
        d.text((150, y + 40), lab, font=font("dela", 46), fill=(255, 255, 255), anchor="mm")
    if tx.get("top"):
        ctext(d, (W / 2, 90 + 760), tx["top"], font("black", 76), (255, 255, 255), 6)
    if tx.get("bot"):
        ctext(d, (W / 2, 970 + 760), tx["bot"], font("black", 84), (255, 235, 60), 6)
    if tx.get("center"):
        f = font("dela", 120); tw = d.textlength(tx["center"], font=f)
        d.rounded_rectangle((W / 2 - tw / 2 - 40, 880, W / 2 + tw / 2 + 40, 1040), radius=20, fill=(220, 40, 50))
        ctext(d, (W / 2, 960), tx["center"], f, (255, 255, 255))
    bot = {"cx": b.get("cx2", b.get("cx", 320)), "cy": b.get("cy2", 180), "zoom": b.get("zoom2", b.get("zoom", 1.0))}
    return img, [slot(b["t"], 0, 90, W, 860, b), slot(b.get("t2", b["t"]), 0, 970, W, 860, bot)]


# ---- C: クイズ(問題文+映像の窓+選択肢2つ+残り時間の棒) ----
def layer_C(b):
    tx = b["texts"]
    img = Image.new("RGBA", (W, H), (24, 28, 70, 255)); d = ImageDraw.Draw(img)
    for i in range(0, H, 6):
        d.line((0, i, W, i), fill=(28, 33, 82))
    hole(img, (80, 430, W - 81, 1049)); d = ImageDraw.Draw(img)
    d.rounded_rectangle((60, 120, W - 60, 380), radius=30, fill=(255, 255, 255))
    ctext(d, (W / 2, 190), tx.get("q1", ""), font("xb", 56), (40, 40, 60))
    ctext(d, (W / 2, 300), tx.get("q2", ""), font("dela", 84), (230, 50, 60))
    d.rectangle((80, 430, W - 80, 1050), outline=(255, 215, 0), width=8)
    for k, (lab, val) in enumerate(tx.get("choices", [])):
        x0 = 80 + k * 470; y0 = 1120
        hi = tx.get("answer") == k; lo = tx.get("answer") is not None and not hi
        col = (255, 215, 0) if hi else ((90, 90, 110) if lo else (255, 255, 255))
        d.rounded_rectangle((x0, y0, x0 + 440, y0 + 230), radius=28, fill=col)
        d.ellipse((x0 + 25, y0 + 65, x0 + 125, y0 + 165), fill=(230, 50, 60))
        ctext(d, (x0 + 75, y0 + 115), lab, font("dela", 60), (255, 255, 255))
        ctext(d, (x0 + 285, y0 + 115), val, font("dela", 96), (30, 30, 50))
    if tx.get("bar") is not None:
        d.rounded_rectangle((80, 1420, W - 80, 1460), radius=20, fill=(60, 66, 120))
        d.rounded_rectangle((80, 1420, 80 + (W - 160) * tx["bar"], 1460), radius=20, fill=(255, 215, 0))
    for k, line in enumerate(tx.get("hint", [])):
        ctext(d, (W / 2, 1540 + k * 90), line, font("xb", 58 if k else 50), (255, 255, 255) if k else (180, 190, 255))
    return img, [slot(b["t"], 80, 430, W - 160, 620, b)]


# ---- D: レシート(ぼかした映像の上に紙。行が上から増える) ----
def layer_D(b):
    tx = b["texts"]
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    px0, px1, py0 = 140, W - 140, 720
    rows = tx.get("rows", [])
    py1 = py0 + 240 + 96 * len(rows) + (170 if tx.get("total") else 0)
    d.rectangle((px0, py0, px1, py1), fill=(252, 251, 246))
    for x in range(px0, px1, 30):  # ギザギザの下端
        d.polygon([(x, py1), (x + 15, py1 + 22), (x + 30, py1)], fill=(252, 251, 246))
    ctext(d, (W / 2, py0 + 70), tx.get("head", "RECEIPT"), font("dela", 54), (30, 30, 30))
    ctext(d, (W / 2, py0 + 130), tx.get("sub", ""), font("bold", 32), (120, 120, 120))
    d.line((px0 + 40, py0 + 175, px1 - 40, py0 + 175), fill=(150, 150, 150), width=3)
    for k, (a, v) in enumerate(rows):
        y = py0 + 230 + 96 * k
        d.text((px0 + 50, y), a, font=font("xb", 46), fill=(40, 40, 40), anchor="lm")
        d.text((px1 - 50, y), v, font=font("dela", 52), fill=(200, 40, 50) if v.startswith("ARS") else (40, 40, 40), anchor="rm")
    if tx.get("total"):
        y = py1 - 110
        d.line((px0 + 40, y - 60, px1 - 40, y - 60), fill=(40, 40, 40), width=4)
        d.text((px0 + 50, y), tx["total"][0], font=font("dela", 56), fill=(40, 40, 40), anchor="lm")
        d.text((px1 - 50, y), tx["total"][1], font=font("dela", 70), fill=(200, 40, 50), anchor="rm")
    if tx.get("cap"):
        ctext(d, (W / 2, 1800), tx["cap"], font("black", 64), (255, 255, 255), 6)
    win = {"cx": b.get("cx", 320), "cy": b.get("wcy", b.get("cy", 180)), "zoom": b.get("wzoom", b.get("zoom", 1.0))}
    return img, [slot(b["t"], 0, 0, W, H, b, blur=True, dim=0.35), slot(b["t"], 160, 110, 760, 560, win)]


# ---- E: 心の声(上に丸いワイプ、下にチャットの吹き出しが積み上がる) ----
def layer_E(b):
    tx = b["texts"]
    r = 380
    img = Image.new("RGBA", (W, H), (236, 229, 221, 255))
    hole(img, (W // 2 - r, 200, W // 2 + r, 200 + 2 * r), "circle")
    d = ImageDraw.Draw(img)
    d.rectangle((0, 0, W, 150), fill=(70, 120, 90))
    ctext(d, (W / 2, 85), tx.get("title", ""), font("xb", 48), (255, 255, 255))
    d.ellipse((W // 2 - r, 200, W // 2 + r, 200 + 2 * r), outline=(255, 255, 255), width=10)
    y = 1060
    for side, msg in tx.get("bubbles", []):
        f = font("dela", 64) if side == "sys" else font("xb", 58)
        lines = msg.split("|")
        bw = max(d.textlength(l, font=f) for l in lines) + 80; bh = 78 * len(lines) + 50
        if side == "me":
            x0 = W - 60 - bw; col = (140, 220, 120)
        elif side == "sys":
            x0 = (W - bw) / 2; col = (220, 40, 50)
        else:
            x0 = 60; col = (255, 255, 255)
        d.rounded_rectangle((x0, y, x0 + bw, y + bh), radius=36, fill=col)
        for k, l in enumerate(lines):
            d.text((x0 + 40, y + 25 + 78 * k), l, font=f, fill=(255, 255, 255) if side == "sys" else (30, 30, 30))
        y += bh + 30
    return img, [slot(b["t"], W // 2 - r, 200, 2 * r, 2 * r, b)]


# ---- D2: レシート改(元動画は横幅いっぱい・拡大なし。上に続きが気になるコピー、下にレシート) ----
VID_Y2 = 380
def layer_D2(b):
    tx = b["texts"]
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    l1, l2 = tx.get("copy", ["", ""])
    if l1:
        ctext(d, (W / 2, 175), l1, font("xb", 62), (255, 255, 255), 6)
    f = font("dela", 96)
    while d.textlength(l2, font=f) > W - 80:
        f = font("dela", f.size - 4)
    ctext(d, (W / 2, 285), l2, f, (255, 220, 60), 8)
    vh = W * 9 // 16
    d.rectangle((0, VID_Y2 - 6, W, VID_Y2), fill=(255, 255, 255)); d.rectangle((0, VID_Y2 + vh, W, VID_Y2 + vh + 6), fill=(255, 255, 255))
    px0, px1, py0 = 120, W - 120, VID_Y2 + vh + 40
    rows = tx.get("rows", [])
    py1 = py0 + 200 + 84 * len(rows) + (150 if tx.get("total") else 0)
    d.rectangle((px0, py0, px1, py1), fill=(252, 251, 246))
    for x in range(px0, px1, 30):
        d.polygon([(x, py1), (x + 15, py1 + 22), (x + 30, py1)], fill=(252, 251, 246))
    ctext(d, (W / 2, py0 + 60), tx.get("head", ""), font("dela", 50), (30, 30, 30))
    ctext(d, (W / 2, py0 + 112), tx.get("sub", ""), font("bold", 30), (120, 120, 120))
    d.line((px0 + 40, py0 + 150, px1 - 40, py0 + 150), fill=(150, 150, 150), width=3)
    for k, (a, v) in enumerate(rows):
        y = py0 + 195 + 84 * k
        d.text((px0 + 50, y), a, font=font("xb", 44), fill=(40, 40, 40), anchor="lm")
        d.text((px1 - 50, y), v, font=font("dela", 50), fill=(200, 40, 50) if v.startswith("ARS") else (40, 40, 40), anchor="rm")
    if tx.get("total"):
        y = py1 - 95
        d.line((px0 + 40, y - 55, px1 - 40, y - 55), fill=(40, 40, 40), width=4)
        d.text((px0 + 50, y), tx["total"][0], font=font("dela", 54), fill=(40, 40, 40), anchor="lm")
        d.text((px1 - 50, y), tx["total"][1], font=font("dela", 68), fill=(200, 40, 50), anchor="rm")
    full = {"cx": 320, "cy": 180, "zoom": 1.0}
    return img, [slot(b["t"], 0, 0, W, H, b, blur=True, dim=0.55), slot(b["t"], 0, VID_Y2, W, vh, full)]


LAYER = {"A": layer_A, "B": layer_B, "C": layer_C, "D": layer_D, "E": layer_E, "D2": layer_D2}


def still(src, key, b):
    """絵コンテ用: 枠に元動画の1コマを貼り、上に絵を重ねる。"""
    over, slots = LAYER[key](b)
    img = Image.new("RGB", (W, H), (0, 0, 0))
    for s in slots:
        im = frame(src, s["t"])
        x, y, cw, ch = crop_box(*im.size, s["w"], s["h"], s["cx"], s["cy"], s["zoom"])
        p = im.crop((x, y, x + cw, y + ch)).resize((s["w"], s["h"]), Image.LANCZOS)
        if s.get("blur"):
            p = p.filter(ImageFilter.GaussianBlur(14))
        if s.get("dim"):
            p = Image.blend(p, Image.new("RGB", p.size, (20, 20, 20)), s["dim"])
        img.paste(p, (s["x"], s["y"]))
    return Image.alpha_composite(img.convert("RGBA"), over).convert("RGB")


def board(p, src, out_dir):
    for v in p["variants"]:
        frames = [still(src, v["key"], b).resize((W // 3, H // 3), Image.LANCZOS) for b in v["beats"]]
        tw, th = frames[0].size
        sheet = Image.new("RGB", (16 + len(frames) * (tw + 16), th + 330), "white")
        d = ImageDraw.Draw(sheet)
        d.text((20, 18), f"案{v['key']}  {v['name']}", font=font("dela", 44), fill=(30, 30, 30))
        d.text((20, 80), "構成: " + v["structure"], font=font("bold", 26), fill=(60, 60, 60))
        d.text((20, 118), "デザイン: " + v["design"], font=font("bold", 26), fill=(60, 60, 60))
        for k, (fr, b) in enumerate(zip(frames, v["beats"])):
            x = 16 + k * (tw + 16)
            sheet.paste(fr, (x, 170))
            line, yy = "", 170 + th + 10
            for ch in f"{k + 1}. 声: " + b.get("say", ""):
                if d.textlength(line + ch, font=font("bold", 21)) > tw:
                    d.text((x, yy), line, font=font("bold", 21), fill=(70, 70, 70)); yy += 27; line = ch
                else:
                    line += ch
            d.text((x, yy), line, font=font("bold", 21), fill=(70, 70, 70))
        out = os.path.join(out_dir, f"variant_{p['name']}_{v['key']}.png")
        sheet.save(out); print(out, sheet.size)


def render(p, v, src, out):
    """1案を動画にする。各区切り: 声(元動画・間詰め)の長さだけ、枠に元動画を流して絵を重ねる。"""
    src_w, src_h = rs.probe(src)
    rs.JET_MIN, rs.JET_PAD = ps.JET_MIN, ps.JET_PAD
    with tempfile.TemporaryDirectory() as td:
        parts, audio, t = [], [], 0.0
        for i, b in enumerate(v["beats"]):
            voices, sfx = [], []
            for j, c in enumerate(b["cuts"]):
                a0, a1 = to_sec(c["a"][0]), to_sec(c["a"][1])
                spans = ps.voice_spans(src, a0, a1) if c.get("jet", True) else [(a0, a1)]
                at = sum(len(x) for x in voices) / SR
                voices.append(np.concatenate([rs.source_audio(src, s0, s1) for s0, s1 in spans]))
                if c.get("se"):
                    sfx.append((at, c["se"]))
            voice = np.concatenate(voices)
            n = max(1, round(len(voice) / SR * 30))
            dur = n / 30
            if i > 0:
                sfx.insert(0, (-0.15, "whoosh"))
            audio.append((t, voice, sfx))
            over, slots = LAYER[v["key"]](b)
            png = os.path.join(td, f"o{i:02d}.png"); over.save(png)
            args, fc, last = [], [f"color=c=black:s={W}x{H}:r=30:d={dur + 1:.3f}[base]"], "base"
            for k, s in enumerate(slots):
                args += ["-ss", f"{s['t']:.3f}", "-t", f"{dur + 0.5:.3f}", "-i", src]
                x, y, cw, ch = crop_box(src_w, src_h, s["w"], s["h"], s["cx"], s["cy"], s["zoom"])
                f = f"[{k}:v]crop={cw}:{ch}:{x}:{y},scale={s['w']}:{s['h']}:flags=lanczos,setsar=1,fps=30"
                if s.get("blur"):
                    f += ",boxblur=24:2"
                if s.get("dim"):
                    f += f",eq=brightness={-s['dim'] * 0.5:.2f}"
                fc.append(f + f",setpts=PTS-STARTPTS,tpad=stop_mode=clone:stop_duration=2[s{k}]")
                fc.append(f"[{last}][s{k}]overlay={s['x']}:{s['y']}[b{k}]"); last = f"b{k}"
            args += ["-loop", "1", "-framerate", "30", "-i", png]
            fc.append(f"[{len(slots)}:v]format=rgba[ov];[{last}][ov]overlay=0:0,format=yuv420p")
            part = os.path.join(td, f"p{i:02d}.mp4")
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *args, "-an", "-filter_complex", ";".join(fc),
                            "-frames:v", str(n), "-c:v", "libx264", "-crf", "17", part], check=True)
            parts.append(part)
            t += dur
        total = t
        mix = np.zeros(int((total + 0.5) * SR), np.float32)
        for at, x, sfx in audio:
            i0 = int(at * SR); mix[i0:i0 + len(x)] += x[: len(mix) - i0]
            for dt, name in sfx:
                s_ = se.get(name) * 0.3
                j0 = max(0, int((at + dt) * SR)); mix[j0:j0 + len(s_)] += s_[: len(mix) - j0]
        mix = mix[: int(total * SR)]
        mix /= max(1.0, np.abs(mix).max() / 0.95)
        wav = os.path.join(td, "mix.wav"); se.write_wav(wav, mix)
        lst = os.path.join(td, "list.txt")
        open(lst, "w").write("".join(f"file '{q}'\n" for q in parts))
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst, "-i", wav,
                        "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-crf", "19", "-pix_fmt", "yuv420p",
                        "-af", "loudnorm=I=-14:TP=-1.0:LRA=11", "-c:a", "aac", "-b:a", "192k", "-shortest",
                        "-movflags", "+faststart", out], check=True)
    print(f"{out} ({total:.1f}s)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("plan"); ap.add_argument("source"); ap.add_argument("--out-dir", required=True)
    ap.add_argument("--video", nargs="*", help="動画にする案の key(例: A B)")
    a = ap.parse_args()
    p = json.load(open(a.plan, encoding="utf-8"))
    os.makedirs(a.out_dir, exist_ok=True)
    if a.video is None:
        board(p, a.source, a.out_dir)
        return
    for v in p["variants"]:
        if v["key"] in a.video:
            render(p, v, a.source, os.path.join(a.out_dir, f"variant_{p['name']}_{v['key']}.mp4"))


if __name__ == "__main__":
    main()
