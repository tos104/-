#!/usr/bin/env python3
"""写真だけで作るリール(飲食・宿向け)。無音で書き出し、曲は投稿アプリで付ける。

スタイルは PLAYBOOK.md 4.85。乱数は使わない(同じ台本からは毎回同じ映像)。

台本(JSON):
{
  "assets": "../../output/tangatable/assets",       # 台本からの相対パス
  "shots": [
    {"img": "a.jpg", "dur": 2.3, "text": ["1行目", "{強調}"], "note": "なぜこのカットがあるか"},
    {"img": "b.jpg", "dur": 1.8, "cont": true}   # cont: 前の文字を出したまま写真だけ替える
  ]
}
  python3 photo_short.py script.json --out out.mp4 [--storyboard sb.png]
"""
import argparse, json, os, re, subprocess
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H, FPS = 1080, 1920, 30
HERE = os.path.dirname(os.path.abspath(__file__))
FONT = os.path.join(HERE, "fonts", "MPLUSRounded1c-ExtraBold.ttf")
CREAM, INK, ACCENT = (245, 239, 230), (42, 33, 29), (142, 42, 34)
TEXT_TOP, SIDE = 230, 80   # Instagram の UI を避ける安全域
ZOOM = 0.06                # 1 カットで寄る量
IN_SEC, IN_PX = 0.2, 24    # 文字が入る時間と距離
SIZE, LEAD = 76, 26


def base(path):
    """縦長は全面、横長・正方形は幅いっぱい+ぼかした同じ写真を背景に。"""
    im = Image.open(path).convert("RGB")
    def cover(img):
        s = max(W / img.width, H / img.height)
        img = img.resize((round(img.width * s), round(img.height * s)), Image.LANCZOS)
        x, y = (img.width - W) // 2, (img.height - H) // 2
        return img.crop((x, y, x + W, y + H))
    if im.height / im.width >= 1.25:
        return cover(im)
    bg = cover(im).filter(ImageFilter.GaussianBlur(40)).point(lambda v: int(v * 0.55))
    fg = im.resize((W, round(im.height * W / im.width)), Image.LANCZOS)
    bg.paste(fg, (0, (H - fg.height) // 2 + 120))
    return bg


def segments(line):
    """"{強調}" を [(文字, 強調か)] に分ける。"""
    return [(s.strip("{}"), s.startswith("{")) for s in re.split(r"(\{[^}]*\})", line) if s]


def card(lines):
    """クリームの文字帯(RGBA)。"""
    pad_x, pad_y = 44, 34
    size = SIZE
    while True:  # 安全域からはみ出す行があれば、全行そろえて小さくする
        font = ImageFont.truetype(FONT, size)
        widths = [sum(font.getlength(t) for t, _ in segments(ln)) for ln in lines]
        if max(widths) <= W - SIDE * 2 - pad_x * 2:
            break
        size -= 2
    cw = int(max(widths)) + pad_x * 2
    ch = pad_y * 2 + size * len(lines) + LEAD * (len(lines) - 1)
    im = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, cw - 1, ch - 1), 28, fill=CREAM + (240,))
    for i, ln in enumerate(lines):
        x = (cw - widths[i]) / 2
        y = pad_y + i * (size + LEAD) - 6
        for t, hot in segments(ln):
            d.text((x, y), t, font=font, fill=ACCENT if hot else INK)
            x += font.getlength(t)
    return im


def frame(b, t, dur, text, t_in):
    s = 1 + ZOOM * t / dur
    cw, ch = W / s, H / s
    x, y = (W - cw) / 2, (H - ch) / 2
    im = b.resize((W, H), Image.BICUBIC, box=(x, y, x + cw, y + ch))
    if text is not None:
        k = min(1.0, max(0.0, t_in / IN_SEC))
        k = 1 - (1 - k) ** 3
        layer = text.copy()
        layer.putalpha(layer.getchannel("A").point(lambda a: int(a * k)))
        im.paste(layer, ((W - text.width) // 2, TEXT_TOP + round(IN_PX * (1 - k))), layer)
    return im


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("script")
    ap.add_argument("--out", required=True)
    ap.add_argument("--storyboard")
    a = ap.parse_args()
    sc = json.load(open(a.script, encoding="utf-8"))
    root = os.path.join(os.path.dirname(os.path.abspath(a.script)), sc["assets"])
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    enc = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                            "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-crf", "17",
                            "-pix_fmt", "yuv420p", "-movflags", "+faststart", a.out], stdin=subprocess.PIPE)
    text, t_text, total, board = None, 0.0, 0.0, []
    for sh in sc["shots"]:
        b = base(os.path.join(root, sh["img"]))
        if not sh.get("cont"):
            text, t_text = (card(sh["text"]) if sh.get("text") else None), total
        n = round(sh["dur"] * FPS)
        for i in range(n):
            t = i / FPS
            im = frame(b, t, sh["dur"], text, total + t - t_text)
            enc.stdin.write(im.tobytes())
            if i == min(n - 1, round(0.6 * FPS)):
                board.append((total, sh, im))
        total += n / FPS
    enc.stdin.close()
    enc.wait()
    if a.storyboard:
        storyboard(board, a.storyboard)
    print(f"{a.out} ({total:.1f}s, {len(sc['shots'])} shots, 無音)")


def storyboard(board, out):
    """台本の各行の代表コマ(0.6 秒目)と、秒・素材・理由を並べる。"""
    tw, th, cols = 270, 480, 4
    rows = (len(board) + cols - 1) // cols
    font = ImageFont.truetype(os.path.join(HERE, "fonts", "MPLUSRounded1c-Bold.ttf"), 17)
    sheet = Image.new("RGB", (cols * (tw + 20) + 20, rows * (th + 120) + 20), (250, 250, 247))
    d = ImageDraw.Draw(sheet)
    for k, (t0, sh, im) in enumerate(board):
        x, y = 20 + (k % cols) * (tw + 20), 20 + (k // cols) * (th + 120)
        sheet.paste(im.resize((tw, th), Image.LANCZOS), (x, y))
        note = sh.get("note", "")
        lines = [f"{t0:.1f}s〜 {sh['dur']}s  {sh['img']}"] + [note[i:i + 15] for i in range(0, len(note), 15)][:4]
        for j, ln in enumerate(lines):
            d.text((x, y + th + 6 + j * 22), ln, font=font, fill=(40, 40, 40))
    sheet.save(out)


if __name__ == "__main__":
    main()
