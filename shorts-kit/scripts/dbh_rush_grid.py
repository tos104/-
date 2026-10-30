"""倍率ラッシュの冒頭用: 元動画から4枚のカードを切り抜き、2段に並べた1枚の絵を作る(中央の段の隙間に文字が乗る)。
  python3 scripts/dbh_rush_grid.py src.mp4 assets/dbh_rush_grid.png
"""
import subprocess, sys, io
from PIL import Image, ImageDraw
sys.path.insert(0, ".")
import storyboard_variants as sv

# (元動画の秒, 切り抜き範囲 x0,y0,x1,y1 / 640x360)。上の帯(元動画のタイトル字幕)は避ける
CARDS = [(905.0, (115, 85, 425, 285)), (985.0, (175, 30, 385, 335)), (741.0, (268, 32, 410, 240)), (1036.0, (190, 36, 398, 268))]


def grab(src, t):
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-ss", f"{t}", "-i", src, "-frames:v", "1", "-f", "image2pipe", "-vcodec", "png", "-"],
                         check=True, capture_output=True).stdout
    return Image.open(io.BytesIO(raw)).convert("RGB")


def main(src, out):
    cw, ch, gap = 480, 640, 330
    img = Image.new("RGB", (cw * 2 + 40, ch * 2 + gap), (14, 14, 18))
    d = ImageDraw.Draw(img)
    for k, (t, box) in enumerate(CARDS):
        c = grab(src, t).crop(box)
        s = min((cw - 30) / c.width, (ch - 30) / c.height)
        c = c.resize((int(c.width * s), int(c.height * s)), Image.LANCZOS)
        x0 = (k % 2) * (cw + 40) + (cw - c.width) // 2
        y0 = (k // 2) * (ch + gap) + (ch - c.height) // 2
        img.paste(c, (x0, y0))
        bx, by = x0 + c.width - 150, y0 + c.height - 95  # 右下に「？倍」
        d.rounded_rectangle((bx, by, bx + 170, by + 110), radius=24, fill=(200, 40, 50))
        d.text((bx + 85, by + 55), "？倍", font=sv.font("dela", 62), fill=(255, 255, 255), anchor="mm")
    img.save(out)
    print(out, img.size)


if __name__ == "__main__":
    main(*sys.argv[1:3])
