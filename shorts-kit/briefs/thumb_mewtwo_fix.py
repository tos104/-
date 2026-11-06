# サムネイルの作り直し: 元動画のコマ(実物のカード・ラベルの等級が写らない 13:06)から、ユーザー作サムネと同じ文字・配置・集中線で。
#   python3 briefs/thumb_mewtwo_fix.py <src.mp4> <out.png>
import sys, subprocess, io
sys.path.insert(0, ".")
from PIL import Image, ImageDraw
import storyboard_variants as sv
src, out = sys.argv[1], sys.argv[2]
W, H = 1080, 1920
def get(vf):
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-ss", "756.5", "-i", src, "-frames:v", "1", "-vf", vf, "-f", "image2pipe", "-vcodec", "png", "-"], capture_output=True, check=True).stdout
    return Image.open(io.BytesIO(raw)).convert("RGBA")
# 背景: 同じコマをぼかして全面 / 主役: カード全体(スラブごと・ラベルの等級は写らない 12:36)を拡大して中央に
bg = get(f"delogo=x=1:y=1:w=205:h=68,scale={W}:{H},boxblur=30:3,eq=brightness=-0.05")
card = get("delogo=x=1:y=1:w=205:h=68,hqdn3d=3:3:4:4,crop=250:300:143:0,scale=500:600:flags=lanczos,scale=900:1080:flags=lanczos,unsharp=5:5:0.9:5:5:0.0,eq=contrast=1.06:saturation=1.12")
img = bg; img.paste(card, ((W - 900) // 2, 330))
sv.speed_lines(img, 1.0, seed=1)
d = ImageDraw.Draw(img)
sv.thick(d, (W / 2, 560), "2,000円が…", 120, (255, 255, 255))
sv.thick(d, (W / 2, 1330), "200万円に", 190, (255, 230, 0))
sv.thick(d, (W / 2, 1530), "化ける!?", 190, (255, 230, 0))
img.convert("RGB").save(out); print(out, img.size)
