#!/usr/bin/env python3
"""演出入りショート(v2): VOICEVOX ナレーション + 合成SE + ズーム/フラッシュ/ポップ字幕/順位バッジ/進捗バー。

台本(JSON):
{
  "header": "青眼と交換した|カード{TOP3}",   # | で改行、{} はアクセント色
  "voice": 21,                                 # VOICEVOX の話者ID
  "lines": [
    {"src": "02:50", "say": "読み上げ", "cap": "字幕|{強調}", "badge": "第3位",
     "zoom": "punch|push|none", "se": ["kira"], "pre_se": "drumroll", "note": "絵コンテ用メモ"}
  ]
}
  python3 rich_short.py script.json source.mp4 --out out.mp4 [--storyboard sb.png] [--bgm bgm.wav]
VOICEVOX エンジンが http://127.0.0.1:50021 で起動している必要がある。
クレジット表記「VOICEVOX:話者名」を概要欄に入れること。
"""
import argparse, io, json, os, re, subprocess, tempfile, textwrap, urllib.parse, urllib.request, wave
import numpy as np
import se
from make_short import to_sec, ass_time
from narr_short import READINGS, probe

SR = 48000
GAP = 0.10
FREEZE = 0.35  # 順位発表の頭で映像を止める秒数
FG_TOP = 300
HERE = os.path.dirname(os.path.abspath(__file__))
FONTS = os.path.join(HERE, "fonts")
HEAD_FONT = "Dela Gothic One"
CAP_FONT = "Rounded Mplus 1c Black"
WHITE, BLACK, YELLOW, RED = "&H00FFFFFF&", "&H00000000&", "&H0000E6FF&", "&H002A2AFF&"
VV = "http://127.0.0.1:50021"


def reading(text):
    for k in sorted(READINGS, key=len, reverse=True):
        text = text.replace(k, READINGS[k])
    return text.replace("{", "").replace("}", "")


def voice(text, speaker, speed):
    q = json.load(urllib.request.urlopen(urllib.request.Request(
        f"{VV}/audio_query?speaker={speaker}&text={urllib.parse.quote(reading(text))}", method="POST"), timeout=60))
    q.update(speedScale=speed, intonationScale=1.15, prePhonemeLength=0.03, postPhonemeLength=0.05,
             outputSamplingRate=SR, outputStereo=False)
    data = urllib.request.urlopen(urllib.request.Request(
        f"{VV}/synthesis?speaker={speaker}", json.dumps(q).encode(), {"Content-Type": "application/json"}),
        timeout=120).read()
    with wave.open(io.BytesIO(data)) as w:
        return np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768


def speaker_name(speaker):
    for s in json.load(urllib.request.urlopen(f"{VV}/speakers", timeout=30)):
        if any(st["id"] == speaker for st in s["styles"]):
            return s["name"]
    return str(speaker)


def colorize(text, base, accent):
    """{...} をアクセント色に。| は改行。"""
    text = text.replace("|", "\\N")
    return re.sub(r"\{(.+?)\}", lambda m: f"{{\\c{accent}}}{m.group(1)}{{\\c{base}}}", text)


def pop_in(ms_in=160):
    return f"\\fscx45\\fscy45\\t(0,{ms_in},\\fscx112\\fscy112)\\t({ms_in},{ms_in + 90},\\fscx100\\fscy100)"


CROWN = "m 0 50 l 0 12 22 32 40 0 58 32 80 12 80 50"


def rect(x1, y1, x2, y2):
    return f"m {x1} {y1} l {x2} {y1} {x2} {y2} {x1} {y2}"


def build_ass(path, header, cuts, total, fg_bottom, hook=None):
    """cuts: [(start, end, line)]"""
    ev = []
    fg_mid = (FG_TOP + fg_bottom - 250) // 2
    # 冒頭フック: 大きな文字を3段で積む(0 / 0.4 / 0.8秒)
    if hook:
        end0 = min(cuts[0][1], 2.4)
        for k, word in enumerate(hook):
            y = fg_mid - 130 + k * 130
            ev.append(f"Dialogue: 8,{ass_time(k * 0.4)},{ass_time(end0)},Hook,,0,0,0,,"
                      f"{{\\an5\\pos(540,{y})\\frz-3{pop_in(150)}\\fad(0,150)}}{colorize(word, WHITE, YELLOW)}")
        ev.append(f"Dialogue: 7,{ass_time(0)},{ass_time(end0)},Box,,0,0,0,,"
                  f"{{\\an7\\pos(0,0)\\1c{BLACK}\\1a&H60&\\fad(0,150)\\p1}}{rect(0, FG_TOP, 1080, fg_bottom - 250)}{{\\p0}}")
    band_top = fg_bottom - 250
    cap_y = band_top + 125
    # 見出し(太い黒フチ1層。二重フチは極太書体だと字が潰れる)
    ev.append(f"Dialogue: 1,{ass_time(0)},{ass_time(total)},Head,,0,0,0,,"
              f"{{\\an8\\pos(540,46){pop_in(200)}}}{colorize(header, WHITE, YELLOW)}")
    # 字幕の下敷き帯(元動画のテロップを隠す)
    ev.append(f"Dialogue: 2,{ass_time(0)},{ass_time(total)},Box,,0,0,0,,"
              f"{{\\an7\\pos(0,0)\\1c{BLACK}\\1a&H00&\\p1}}m 0 {band_top} l 1080 {band_top} 1080 {fg_bottom} 0 {fg_bottom}{{\\p0}}")
    # ランキング表: 冒頭から「？？？」で並べ、順位の発表時に埋める
    board = sorted([(int(re.sub(r"\D", "", ln["badge"])), s, ln) for s, e, ln in cuts if ln.get("badge")])
    for row, (rank, s, ln) in enumerate(board):
        y = fg_bottom + 60 + row * 118
        label = f"第{rank}位"
        ev.append(f"Dialogue: 3,{ass_time(0)},{ass_time(s)},Board,,0,0,0,,{{\\an4\\pos(70,{y})\\1c&H00A0A0A0&}}{label}  ？？？")
        ev.append(f"Dialogue: 3,{ass_time(s)},{ass_time(total)},Board,,0,0,0,,"
                  f"{{\\an4\\pos(70,{y}){pop_in(140)}}}{{\\c{YELLOW}}}{label}{{\\c{WHITE}}}  {ln.get('board', ln['badge'])}")
        if rank == 1:  # 1位には王冠アイコン
            ev.append(f"Dialogue: 3,{ass_time(s)},{ass_time(total)},Box,,0,0,0,,"
                      f"{{\\an7\\pos(8,{y - 78})\\1c{YELLOW}\\3c{BLACK}\\bord4\\fscx60\\fscy60{pop_in(140)}\\p1}}{CROWN}{{\\p0}}")
    for i, (s, e, ln) in enumerate(cuts):
        # カット頭の白フラッシュ
        if i:
            ev.append(f"Dialogue: 5,{ass_time(s)},{ass_time(s + 0.12)},Box,,0,0,0,,"
                      f"{{\\an7\\pos(0,0)\\1c{WHITE}\\1a&H30&\\fad(0,110)\\p1}}m 0 0 l 1080 0 1080 1920 0 1920{{\\p0}}")
        # 字幕(ポップイン)
        cap = colorize(ln.get("cap", ln["say"]), WHITE, YELLOW if not ln.get("badge") else RED)
        ev.append(f"Dialogue: 4,{ass_time(s + 0.03)},{ass_time(e)},Cap,,0,0,0,,{{\\an5\\pos(540,{cap_y}){pop_in()}}}{cap}")
        # 順位バッジ(画面中央に叩きつけ→フェード)
        if ln.get("badge"):
            ev.append(f"Dialogue: 6,{ass_time(s + 0.02)},{ass_time(min(e, s + 1.3))},Badge,,0,0,0,,"
                      f"{{\\an5\\pos(540,{FG_TOP + 260})\\frz-6\\fad(0,180)"
                      f"\\fscx260\\fscy260\\t(0,140,\\fscx92\\fscy92)\\t(140,220,\\fscx100\\fscy100)}}{ln['badge']}")
        # 光のスイープ(カードの上を斜めの光が横切る)
        if ln.get("shine"):
            a0 = s + 0.25
            ev.append(f"Dialogue: 6,{ass_time(a0)},{ass_time(a0 + 0.7)},Box,,0,0,0,,"
                      f"{{\\an7\\clip({rect(0, FG_TOP, 1080, fg_bottom - 250)})\\move(-400,{FG_TOP},1300,{FG_TOP})"
                      f"\\1c{WHITE}\\1a&H70&\\blur30\\p1}}m 120 0 l 260 0 140 {fg_bottom - FG_TOP} 0 {fg_bottom - FG_TOP}{{\\p0}}")
        # 転調: クライマックスで画面全体を金色に寄せる
        if ln.get("tint"):
            ev.append(f"Dialogue: 2,{ass_time(s)},{ass_time(e)},Box,,0,0,0,,"
                      f"{{\\an7\\pos(0,0)\\1c&H0040B8FF&\\1a&HC8&\\fad(150,250)\\p1}}{rect(0, 0, 1080, 1920)}{{\\p0}}")
        # 図解: 横棒グラフが伸びる [[ラベル, 値, 表示], ...]
        if ln.get("chart"):
            rows = ln["chart"]
            vmax = max(r[1] for r in rows)
            top = FG_TOP + 70
            ev.append(f"Dialogue: 7,{ass_time(s)},{ass_time(e)},Box,,0,0,0,,"
                      f"{{\\an7\\pos(0,0)\\1c{BLACK}\\1a&H40&\\fad(120,0)\\p1}}{rect(40, top - 30, 1040, top + 150 * len(rows) + 10)}{{\\p0}}")
            for k, (label, value, shown) in enumerate(rows):
                y = top + k * 150
                w = int(900 * value / vmax)
                color = YELLOW if k == 0 else WHITE
                ev.append(f"Dialogue: 8,{ass_time(s)},{ass_time(e)},Board,,0,0,0,,{{\\an7\\pos(90,{y})}}{label}")
                ev.append(f"Dialogue: 8,{ass_time(s + 0.15)},{ass_time(e)},Box,,0,0,0,,"
                          f"{{\\an7\\pos(0,0)\\1c{color}\\clip(90,{y + 70},90,{y + 125})\\t(0,500,\\clip(90,{y + 70},{90 + w},{y + 125}))\\p1}}"
                          f"{rect(90, y + 70, 90 + w, y + 125)}{{\\p0}}")
                ev.append(f"Dialogue: 9,{ass_time(s + 0.6)},{ass_time(e)},Board,,0,0,0,,"
                          f"{{\\an6\\pos({min(1020, 90 + w - 10)},{y + 98})\\1c{BLACK}\\bord0\\shad0{pop_in(120)}}}{shown}")
    # 進捗バー
    ms = int(total * 1000)
    ev.append(f"Dialogue: 7,{ass_time(0)},{ass_time(total)},Box,,0,0,0,,"
              f"{{\\an7\\pos(0,0)\\1c{YELLOW}\\clip(0,{FG_TOP - 14},0,{FG_TOP})\\t(0,{ms},\\clip(0,{FG_TOP - 14},1080,{FG_TOP}))\\p1}}"
              f"m 0 {FG_TOP - 14} l 1080 {FG_TOP - 14} 1080 {FG_TOP} 0 {FG_TOP}{{\\p0}}")
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 2

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Head,{HEAD_FONT},92,{WHITE},{WHITE},{BLACK},&H99000000&,0,0,0,0,100,100,2,0,1,12,5,8,20,20,40,1
Style: Cap,{CAP_FONT},84,{WHITE},{WHITE},{BLACK},&H96000000&,0,0,0,0,100,100,0,0,1,10,4,5,30,30,0,1
Style: Badge,{HEAD_FONT},200,{YELLOW},{YELLOW},{BLACK},&H99000000&,0,0,0,0,100,100,0,0,1,18,8,5,0,0,0,1
Style: Board,{CAP_FONT},66,{WHITE},{WHITE},{BLACK},&H99000000&,0,0,0,0,100,100,0,0,1,8,3,4,0,0,0,1
Style: Hook,{HEAD_FONT},128,{WHITE},{WHITE},{BLACK},&H99000000&,0,0,0,0,100,100,0,0,1,14,6,5,0,0,0,1
Style: Box,Arial,10,{WHITE},{WHITE},{BLACK},&H00000000&,0,0,0,0,100,100,0,0,1,0,0,7,0,0,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
""" + "\n".join(ev) + "\n")


def zoom_expr(kind):
    if kind == "punch":   # 強く寄ってから戻る
        return "if(lt(on,7),1.28-0.035*on,1.035+0.0007*on)"
    if kind == "push":    # ゆっくり寄る
        return "1+0.0022*on"
    return "1"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("script")
    ap.add_argument("source")
    ap.add_argument("--out", required=True)
    ap.add_argument("--storyboard")
    ap.add_argument("--bgm")
    ap.add_argument("--speed", type=float, default=1.2)
    a = ap.parse_args()
    sc = json.load(open(a.script, encoding="utf-8"))
    spk = sc.get("voice", 21)
    src_w, src_h = probe(a.source)
    fg_h = int(1080 * src_h / src_w) // 2 * 2
    fg_bottom = FG_TOP + fg_h

    # 1) 音声と尺
    voices, cuts, t = [], [], 0.0
    for ln in sc["lines"]:
        v = voice(ln["say"], spk, a.speed)
        dur = len(v) / SR + GAP
        voices.append((t, v))
        cuts.append((t, t + dur, ln))
        t += dur
    total = t

    # 2) 音声ミックス(ナレーション + SE [+ BGM])
    mix = np.zeros(int((total + 1.0) * SR), np.float32)
    def put(at, x, gain):
        i = max(0, int(at * SR)); x = x[: len(mix) - i]
        mix[i:i + len(x)] += x * gain
    for at, v in voices:
        put(at, v, 1.0)
    put(0.0, se.get("logo"), 0.5)  # 毎回同じサウンドロゴ
    for i, (s, e, ln) in enumerate(cuts):
        if i:
            put(s - 0.12, se.get("whoosh"), 0.45)
        put(s + 0.03, se.get("pop"), 0.35)
        if ln.get("badge"):
            put(s, se.get("impact"), 0.7)
        if ln.get("pre_se"):
            put(s - 0.9, se.get(ln["pre_se"]), 0.55)
        for name in ln.get("se", []):
            put(s + 0.25, se.get(name), 0.6)
    if a.bgm:
        b = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", a.bgm, "-ac", "1", "-ar", str(SR), "-f", "s16le", "-"],
                           check=True, capture_output=True).stdout
        bgm = np.frombuffer(b, np.int16).astype(np.float32) / 32768
        bgm = np.resize(bgm, len(mix)) * 0.12
        mix += bgm
    mix = mix[: int(total * SR)]
    mix = mix / max(1.0, np.max(np.abs(mix)) / 0.95)

    with tempfile.TemporaryDirectory() as td:
        wav = os.path.join(td, "mix.wav")
        se.write_wav(wav, mix)

        # 3) カットごとの映像(ズーム)
        parts = []
        for i, (s, e, ln) in enumerate(cuts):
            p = os.path.join(td, f"p{i:02d}.mp4")
            freeze = f"tpad=start_mode=clone:start_duration={FREEZE}," if ln.get("freeze") else ""
            vf = (f"fps=30,{freeze}scale=2160:-2:flags=lanczos,"
                  f"zoompan=z='{zoom_expr(ln.get('zoom', 'push'))}':d=1:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
                  f":s=1080x{fg_h}:fps=30,unsharp=5:5:0.5,trim=duration={e - s:.3f},format=yuv420p")
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", str(to_sec(ln["src"])), "-t", f"{e - s:.3f}",
                            "-i", a.source, "-an", "-vf", vf, "-c:v", "libx264", "-crf", "16", p], check=True)
            parts.append(p)
        lst = os.path.join(td, "list.txt")
        open(lst, "w").write("".join(f"file '{p}'\n" for p in parts))

        # 4) 合成
        ass = os.path.join(td, "fx.ass")
        build_ass(ass, sc.get("header", ""), cuts, total, fg_bottom, sc.get("hook"))
        vf = (f"[0:v]split[a][b];"
              f"[a]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=28:2,eq=brightness=-0.3:saturation=1.2[bg];"
              f"[bg][b]overlay=0:{FG_TOP},noise=alls=6:allf=t,vignette=PI/5,"
              f"ass='{ass}':fontsdir='{FONTS}',format=yuv420p[v]")
        os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst, "-i", wav,
                        "-filter_complex", vf, "-map", "[v]", "-map", "1:a", "-c:v", "libx264", "-crf", "19",
                        "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", a.out], check=True)

        if a.storyboard:
            storyboard(a.out, a.storyboard, cuts, total, os.path.basename(a.script), speaker_name(spk), sc.get("hook"))
    chars = sum(len(reading(ln["say"])) for ln in sc["lines"])
    print(f"{a.out} ({total:.1f}s, {chars / total:.1f}字/秒, voice={speaker_name(spk)})")


def storyboard(video, out, cuts, total, title, vname, hook=None):
    from PIL import Image, ImageDraw, ImageFont
    font = ImageFont.truetype(os.path.join(FONTS, "MPLUSRounded1c-Black.ttf"), 19)
    big = ImageFont.truetype(os.path.join(FONTS, "MPLUSRounded1c-Black.ttf"), 25)
    PW, PH, TH, COLS = 324, 576, 330, 4
    rows = (len(cuts) + COLS - 1) // COLS
    sheet = Image.new("RGB", (COLS * (PW + 20) + 20, 70 + rows * (PH + TH + 20)), "white")
    d = ImageDraw.Draw(sheet)
    d.text((20, 18), f"{title}  全{total:.1f}秒 / {len(cuts)}カット / 声: VOICEVOX:{vname}", font=big, fill="black")
    with tempfile.TemporaryDirectory() as td:
        for i, (s, e, ln) in enumerate(cuts):
            png = os.path.join(td, f"{i}.png")
            at = s + 0.45 if ln.get("badge") else min(e - 0.05, s + max(0.45, (e - s) * 0.5))
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{at:.2f}", "-i", video, "-frames:v", "1", png],
                           check=True)
            x = 20 + (i % COLS) * (PW + 20)
            y = 70 + (i // COLS) * (PH + TH + 20)
            sheet.paste(Image.open(png).resize((PW, PH)), (x, y))
            ty = y + PH + 8
            d.text((x, ty), f"#{i + 1}  {s:.1f}–{e:.1f}秒", font=big, fill="#c00000")
            d.text((x, ty + 32), f"素材 {ln['src']}〜 / ズーム {ln.get('zoom', 'push')}", font=font, fill="#555555")
            ty += 60
            fx = ["白フラッシュ+シュッ"] if i else ["見出しポップ"]
            fx += ["字幕ポップ+ポン"]
            if ln.get("badge"):
                fx.append(f"「{ln['badge']}」叩きつけ+ドン")
            if ln.get("pre_se"):
                fx.append(f"直前に{ln['pre_se']}")
            fx += ln.get("se", [])
            fx += [n for k, n in [("freeze", "映像を一瞬止める"), ("shine", "光のスイープ"), ("tint", "金色に転調"), ("chart", "図解(棒グラフ)")] if ln.get(k)]
            if i == 0:
                fx += ["サウンドロゴ"] + (["冒頭フック3段"] if hook else [])
            body = ["【声】" + ln["say"].replace("{", "").replace("}", ""), "【演出】" + "・".join(fx)]
            if ln.get("note"):
                body.append("【狙い】" + ln["note"])
            for para in body:
                for wl in textwrap.wrap(para, 16):
                    d.text((x, ty), wl, font=font, fill="black")
                    ty += 24
    sheet.save(out)


if __name__ == "__main__":
    main()
