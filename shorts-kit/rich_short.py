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
BAND = 250  # 字幕帯(すりガラス)の高さ
MAX_SHOT = 3.0  # 本人の声モードで、同じ画角を続ける最長(秒)
JET_MIN = 0.28  # これ以上の間はジェットカットで詰める(秒)
JET_PAD = 0.06  # 声の前後に残す余白(秒)
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


def source_audio(path, start, end):
    """元動画の音声を切り出して整える(低域カット・ノイズ低減・コンプ・端のフェード)。"""
    d = end - start
    af = (f"highpass=f=90,afftdn=nf=-25,acompressor=threshold=-20dB:ratio=3:attack=5:release=80,"
          f"afade=t=in:d=0.015,afade=t=out:st={max(0, d - 0.03):.3f}:d=0.03")
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-ss", f"{start:.3f}", "-t", f"{d:.3f}", "-i", path,
                          "-af", af, "-ac", "1", "-ar", str(SR), "-f", "s16le", "-"], check=True, capture_output=True).stdout
    return np.frombuffer(raw, np.int16).astype(np.float32) / 32768


def speech_spans(path, start, end):
    """区間内の「間」(JET_MIN 秒以上の無音)を除いた、声のある小区間を返す。"""
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-ss", f"{start:.3f}", "-t", f"{end - start:.3f}", "-i", path,
                          "-ac", "1", "-ar", "16000", "-f", "s16le", "-"], check=True, capture_output=True).stdout
    x = np.frombuffer(raw, np.int16).astype(np.float32)
    win = 320  # 20ms
    n = len(x) // win
    if n == 0:
        return [(start, end)]
    db = 20 * np.log10(np.sqrt((x[: n * win].reshape(n, win) ** 2).mean(1)) + 1)
    thr = np.percentile(db, 10) + 5  # 小さな声も残す(間だけを詰める)
    voiced = db > thr
    spans, i = [], 0
    while i < n:
        if voiced[i]:
            j = i
            while j < n and (voiced[j] or (j + int(JET_MIN / 0.02) < n and voiced[j:j + int(JET_MIN / 0.02)].any())):
                j += 1
            spans.append((max(0, i * 0.02 - JET_PAD), min(end - start, j * 0.02 + JET_PAD)))
            i = j
        else:
            i += 1
    spans = [(a, b) for a, b in spans if b - a >= 0.15] or [(0, end - start)]
    return [(start + a, start + b) for a, b in spans]


def speaker_name(speaker):
    if speaker == "source":
        return "本人の声(元動画)"
    for s in json.load(urllib.request.urlopen(f"{VV}/speakers", timeout=30)):
        if any(st["id"] == speaker for st in s["styles"]):
            return s["name"]
    return str(speaker)


def colorize(text, base, accent):
    """{...} をアクセント色に。| は改行。"""
    text = text.replace("|", "\\N")
    return re.sub(r"\{(.+?)\}", lambda m: f"{{\\c{accent}}}{m.group(1)}{{\\c{base}}}", text)


def pop_in(ms_in=160):
    """見出し・バッジ用: 強く入って行き過ぎてから止まる。"""
    return f"\\fscx45\\fscy45\\t(0,{ms_in},\\fscx112\\fscy112)\\t({ms_in},{ms_in + 90},\\fscx100\\fscy100)"


def snap_in(ms_in=110):
    """字幕・表など小さな要素用: 素早く入り、行き過ぎはほぼなし。"""
    return f"\\fscx85\\fscy85\\alpha&HFF&\\t(0,{ms_in},\\fscx100\\fscy100\\alpha&H00&)"


# 0フレーム目から見えたまま、わずかに縮んで落ち着く(スワイプ前の一瞬で読める)
SETTLE = "\\fscx112\\fscy112\\t(0,140,\\fscx100\\fscy100)"
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
            if k == 0:  # 0フレーム目から見えている(スワイプ前の一瞬で何の動画かわかる)
                anim = "\\fscx118\\fscy118\\t(0,120,\\fscx100\\fscy100)"
            else:       # #005 マスクリビール、0.25秒ずつ(#002 スタガー)
                anim = f"\\clip(0,{y - 75},1080,{y + 75})\\move(540,{y + 150},540,{y},0,180)"
            pos = "" if "move" in anim else f"\\pos(540,{y})"
            ev.append(f"Dialogue: 8,{ass_time(k * 0.25)},{ass_time(end0)},Hook,,0,0,0,,"
                      f"{{\\an5{pos}{anim}\\frz3\\fad(0,150)}}{colorize(word, WHITE, YELLOW)}")
        ev.append(f"Dialogue: 7,{ass_time(0)},{ass_time(end0)},Box,,0,0,0,,"
                  f"{{\\an7\\pos(0,0)\\1c{BLACK}\\1a&H60&\\fad(0,150)\\p1}}{rect(0, FG_TOP, 1080, fg_bottom - 250)}{{\\p0}}")
    band_top = fg_bottom - BAND
    cap_y = band_top + 125
    # 見出し(太い黒フチ1層。二重フチは極太書体だと字が潰れる)
    ev.append(f"Dialogue: 1,{ass_time(0)},{ass_time(total)},Head,,0,0,0,,"
              f"{{\\an8\\pos(540,46){SETTLE}}}{colorize(header, WHITE, YELLOW)}")
    # 字幕の帯はすりガラス(映像側でぼかし済み)。上端に細い区切り線だけ引く
    ev.append(f"Dialogue: 2,{ass_time(0)},{ass_time(total)},Box,,0,0,0,,"
              f"{{\\an7\\pos(0,0)\\1c{YELLOW}\\1a&H60&\\p1}}{rect(0, band_top, 1080, band_top + 4)}{{\\p0}}")
    # ランキング表: 冒頭から「？？？」で並べ、順位の発表時に埋める
    board = sorted([(int(re.sub(r"\D", "", ln["badge"])), s, ln) for s, e, ln in cuts if ln.get("badge")])
    for row, (rank, s, ln) in enumerate(board):
        y = fg_bottom + 60 + row * 118
        label = f"第{rank}位"
        ev.append(f"Dialogue: 3,{ass_time(0)},{ass_time(s)},Board,,0,0,0,,{{\\an4\\pos(70,{y})\\1c&H00A0A0A0&}}{label}  ？？？")
        ev.append(f"Dialogue: 3,{ass_time(s)},{ass_time(total)},Board,,0,0,0,,"
                  f"{{\\an4\\pos(70,{y}){snap_in()}}}{{\\c{YELLOW}}}{label}{{\\c{WHITE}}}  {ln.get('board', ln['badge'])}")
        if rank == 1:  # 1位には王冠アイコン
            ev.append(f"Dialogue: 3,{ass_time(s)},{ass_time(total)},Box,,0,0,0,,"
                      f"{{\\an7\\pos(8,{y - 78})\\1c{YELLOW}\\3c{BLACK}\\bord4\\fscx60\\fscy60{pop_in(140)}\\p1}}{CROWN}{{\\p0}}")
    for i, (s, e, ln) in enumerate(cuts):
        # カット頭の白フラッシュ(同じ行の中のジャンプカットには入れない)
        if i and not ln.get("sub"):
            ev.append(f"Dialogue: 5,{ass_time(s)},{ass_time(s + 0.12)},Box,,0,0,0,,"
                      f"{{\\an7\\pos(0,0)\\1c{WHITE}\\1a&H30&\\fad(0,110)\\p1}}m 0 0 l 1080 0 1080 1920 0 1920{{\\p0}}")
        # 字幕(ポップイン)
        cap = colorize(ln.get("cap", ln["say"]), WHITE, YELLOW if not ln.get("badge") else RED)
        anim = SETTLE if i == 0 else ("" if ln.get("cont") else snap_in())
        c0 = 0 if i == 0 else (s if ln.get("cont") else s + 0.03)  # 先頭の字幕だけ0フレーム目から
        ev.append(f"Dialogue: 4,{ass_time(c0)},{ass_time(e)},Cap,,0,0,0,,{{\\an5\\pos(540,{cap_y}){anim}}}{cap}")
        # 順位バッジ(画面中央に叩きつけ→フェード)
        if ln.get("badge"):
            ev.append(f"Dialogue: 6,{ass_time(s + 0.02)},{ass_time(min(e, s + 1.3))},Badge,,0,0,0,,"
                      f"{{\\an5\\pos(540,{FG_TOP + 260})\\frz6\\fad(0,180)"
                      f"\\fscx260\\fscy260\\t(0,140,\\fscx92\\fscy92)\\t(140,220,\\fscx100\\fscy100)}}{ln['badge']}")
        if ln.get("badge"):
            cx, cy = 540, FG_TOP + 260
            for k in range(10):
                ang = k * 36
                ev.append(f"Dialogue: 5,{ass_time(s + 0.05)},{ass_time(s + 0.45)},Box,,0,0,0,,"
                          f"{{\\an7\\pos({cx},{cy})\\org({cx},{cy})\\frz{ang}\\1c{YELLOW}\\bord0\\fad(0,200)"
                          f"\\fscx60\\fscy100\\t(0,300,\\fscx160\\fscy60)\\p1}}{rect(170, -6, 330, 6)}{{\\p0}}")
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
                      f"{{\\an7\\pos(0,0)\\1c{BLACK}\\1a&H06&\\fad(120,0)\\p1}}{rect(0, FG_TOP, 1080, fg_bottom - 250)}{{\\p0}}")
            for k, (label, value, shown) in enumerate(rows):
                y = top + k * 150
                w = int(900 * value / vmax)
                color = YELLOW if k == 0 else WHITE
                ev.append(f"Dialogue: 8,{ass_time(s)},{ass_time(e)},Board,,0,0,0,,{{\\an7\\pos(90,{y})}}{label}")
                ev.append(f"Dialogue: 8,{ass_time(s + 0.15)},{ass_time(e)},Box,,0,0,0,,"
                          f"{{\\an7\\pos(0,0)\\1c{color}\\clip(90,{y + 70},90,{y + 125})\\t(0,500,\\clip(90,{y + 70},{90 + w},{y + 125}))\\p1}}"
                          f"{rect(90, y + 70, 90 + w, y + 125)}{{\\p0}}")
                steps = 12
                for j in range(steps + 1):
                    t0 = s + 0.15 + 0.5 * j / steps
                    t1 = e if j == steps else s + 0.15 + 0.5 * (j + 1) / steps
                    txt_ = shown if j == steps else f"{round(value * j / steps)}万円"
                    ev.append(f"Dialogue: 9,{ass_time(t0)},{ass_time(t1)},Board,,0,0,0,,"
                              f"{{\\an6\\pos({min(1020, 90 + w - 10)},{y + 98})\\1c{WHITE}\\3c{BLACK}\\bord7}}{txt_}")
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


SIMPLE_CROP = "330:184:109:62"  # 548x360 の元動画から、上のテロップ/ロゴと下のテロップを除いた中央部分(4:2:0 のため偶数)
_cw, _ch = map(int, SIMPLE_CROP.split(":")[:2])
SIMPLE_H = int(1080 * _ch / _cw) // 2 * 2  # 1080 幅にしたときの高さ(切り取り範囲から計算)
SIMPLE_TOP = 470


def build_ass_simple(path, header, cuts, total):
    """見出し(固定)と字幕(切り替えのみ)だけ。動きは字幕の 0.08 秒のフェードだけ。"""
    ev = [f"Dialogue: 1,{ass_time(0)},{ass_time(total)},Head,,0,0,0,,{{\\an5\\pos(540,290)}}{colorize(header, WHITE, YELLOW)}"]
    cap_y = SIMPLE_TOP + SIMPLE_H + 150
    for i, (s, e, ln) in enumerate(cuts):
        cap = colorize(ln.get("cap", ""), WHITE, YELLOW)
        if ln.get("badge"):
            cap = f"{{\\c{YELLOW}}}{ln['badge']}{{\\c{WHITE}}}\\N" + cap
        fade = "" if (i == 0 or ln.get("cont")) else "\\fad(80,0)"
        ev.append(f"Dialogue: 2,{ass_time(s)},{ass_time(e)},Cap,,0,0,0,,{{\\an5\\pos(540,{cap_y}){fade}}}{cap}")
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 2

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Head,{HEAD_FONT},96,{WHITE},{WHITE},{BLACK},&H00000000&,0,0,0,0,100,100,2,0,1,6,0,5,40,40,0,1
Style: Cap,{CAP_FONT},84,{WHITE},{WHITE},{BLACK},&H00000000&,0,0,0,0,100,100,0,0,1,6,0,5,50,50,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
""" + "\n".join(ev) + "\n")


def zoom_expr(kind):
    if kind == "punch":   # 強く寄ってから戻る
        return "if(lt(on,7),1.28-0.035*on,1.035+0.0007*on)"
    if kind == "jump":    # ジャンプカット: 少し寄った画角で切り替わりを見せる
        return "1.1+0.0012*on"
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
    ap.add_argument("--simple", action="store_true", help="演出なし: 黒背景・見出し・映像・字幕だけ。効果音なし")
    a = ap.parse_args()
    sc = json.load(open(a.script, encoding="utf-8"))
    spk = sc.get("voice", 21)
    src_w, src_h = probe(a.source)
    fg_h = int(1080 * src_h / src_w) // 2 * 2
    fg_bottom = FG_TOP + fg_h

    # 1) 音声と尺
    voices, cuts, t = [], [], 0.0
    for ln in sc["lines"]:
        if spk == "source":
            # ranges の各区間をつなぐ。2区間目以降はジャンプカット(演出は先頭区間だけ)
            caps = ln.get("caps", [ln.get("cap", "")])
            for k, rg in enumerate(ln["ranges"]):
                r0, r1 = rg[0], rg[1]
                st, en = to_sec(r0), to_sec(r1)
                vshift = to_sec(rg[2]) - st if len(rg) > 2 else 0.0  # 映像の取り出し位置のずれ
                cap = caps[min(k, len(caps) - 1)]
                first_in_range = True
                spans = speech_spans(a.source, st, en) if ln.get("jet", True) else [(st, en)]
                for si, (a0, a1) in enumerate(spans):
                    voices.append((t, source_audio(a.source, a0, a1)))
                    # 長い区間は MAX_SHOT 秒ごとに画角を変えて切る(同じ字幕のまま続ける)
                    m = max(1, int(np.ceil((a1 - a0) / MAX_SHOT)))
                    for j in range(m):
                        c0, c1 = a0 + (a1 - a0) * j / m, a0 + (a1 - a0) * (j + 1) / m
                        if k == 0 and first_in_range:
                            sub = dict(ln)
                        else:
                            sub = {"sub": True, "zoom": "jump" if (len(cuts) % 2) else "push", "cont": not first_in_range,
                                   "jet": si > 0 and j == 0}
                        sub.update(src=f"{c0 + vshift:.2f}", cap=cap, say=sub.get("say", cap) if first_in_range else "")
                        cuts.append((t, t + c1 - c0, sub))
                        t += c1 - c0
                        first_in_range = False
            continue
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
    if not a.simple:
        put(max(0.0, total - 1.0), se.get("logo"), 0.55)  # 毎回同じサウンドロゴ(最後。ループの継ぎ目)
    for i, (s, e, ln) in enumerate([] if a.simple else cuts):
        if i and not ln.get("sub"):
            put(s - 0.12, se.get("whoosh"), 0.45)
        if not ln.get("cont"):
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
            if a.simple:
                # 元動画の上下のテロップとロゴを切り落とし、カードの部分だけを大きく。動きは付けない
                z = 1.15 if i % 2 else 1.0  # ジャンプカットの継ぎ目が目立たないよう画角だけ交互に
                vf = (f"fps=30,crop={SIMPLE_CROP},scale={int(1080 * z) // 2 * 2}:-2:flags=lanczos,"
                      f"crop=1080:{SIMPLE_H},unsharp=5:5:0.4,format=yuv420p")
                subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", str(to_sec(ln["src"])), "-t", f"{e - s:.3f}",
                                "-i", a.source, "-an", "-vf", vf, "-c:v", "libx264", "-crf", "16", p], check=True)
                parts.append(p)
                continue
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
        if a.simple:
            build_ass_simple(ass, sc.get("header", ""), cuts, total)
            vf = (f"color=c=black:s=1080x1920:r=30[bg];[bg][0:v]overlay=0:{SIMPLE_TOP}:shortest=1,"
                  f"ass='{ass}':fontsdir='{FONTS}',format=yuv420p[v]")
        hits = [s_ for s_, _, ln in cuts if ln.get("badge")]
        shake = "+".join(f"if(between(t,{h:.2f},{h + 0.28:.2f}),14*sin(t*95)*(1-(t-{h:.2f})/0.28),0)" for h in hits) or "0"
        if not a.simple:
          vf = (f"[0:v]split[a][b];"
              f"[a]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=28:2,eq=brightness=-0.3:saturation=1.2[bg];"
              f"[b]split[f1][f2];[f2]crop=1080:{BAND}:0:{fg_h - BAND},boxblur=22:3,eq=brightness=-0.28:saturation=0.35[glass];"
              f"[f1][glass]overlay=0:{fg_h - BAND}[fgx];"
              f"[bg][fgx]overlay=x='{shake}':y='{FG_TOP}+({shake})*0.6',noise=alls=6:allf=t:all_seed=7,vignette=PI/5,"
              f"ass='{ass}':fontsdir='{FONTS}',format=yuv420p[v]")
        os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst, "-i", wav,
                        "-filter_complex", vf, "-map", "[v]", "-map", "1:a", "-c:v", "libx264", "-crf", "19",
                        "-af", "loudnorm=I=-11.5:TP=-1.0:LRA=11", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", a.out], check=True)

        if a.storyboard:
            storyboard(a.out, a.storyboard, cuts, total, os.path.basename(a.script), speaker_name(spk), sc.get("hook"))
    chars = sum(len(reading(ln.get("say", ""))) for _, _, ln in cuts)
    print(f"{a.out} ({total:.1f}s, {chars / total:.1f}字/秒, voice={speaker_name(spk)})")


def storyboard(video, out, cuts, total, title, vname, hook=None):
    from PIL import Image, ImageDraw, ImageFont
    font = ImageFont.truetype(os.path.join(FONTS, "MPLUSRounded1c-Black.ttf"), 19)
    big = ImageFont.truetype(os.path.join(FONTS, "MPLUSRounded1c-Black.ttf"), 25)
    cuts = [c for c in cuts if not c[2].get("sub")]  # 台本の行ごとの代表コマだけ
    PW, PH, TH, COLS = 324, 576, 330, 4
    rows = (len(cuts) + COLS - 1) // COLS
    sheet = Image.new("RGB", (COLS * (PW + 20) + 20, 70 + rows * (PH + TH + 20)), "white")
    d = ImageDraw.Draw(sheet)
    d.text((20, 18), f"{title}  全{total:.1f}秒 / {len(cuts)}カット / 声: {vname if '本人' in vname else 'VOICEVOX:' + vname}", font=big, fill="black")
    with tempfile.TemporaryDirectory() as td:
        for i, (s, e, ln) in enumerate(cuts):
            png = os.path.join(td, f"{i}.png")
            at = s + 0.45 if ln.get("badge") else s + max(0.45, (e - s) * 0.5)
            at = max(0.0, min(at, e - 0.05, total - 0.1))
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{at:.2f}", "-i", video, "-frames:v", "1", png],
                           check=True)
            x = 20 + (i % COLS) * (PW + 20)
            y = 70 + (i // COLS) * (PH + TH + 20)
            sheet.paste(Image.open(png).resize((PW, PH)), (x, y))
            ty = y + PH + 8
            d.text((x, ty), f"#{i + 1}  {s:.1f}–{e:.1f}秒", font=big, fill="#c00000")
            d.text((x, ty + 32), f"素材 {ln['src']}〜 / ズーム {ln.get('zoom', 'push')}", font=font, fill="#555555")
            ty += 60
            fx = (["白フラッシュ+シュッ"] if not ln.get("sub") else ["#041ジャンプカット"]) if i else ["#001ポップイン(見出し)"]
            fx += ["#001ポップイン(字幕)+ポン"]
            if ln.get("badge"):
                fx.append(f"「{ln['badge']}」#036傾き+#010オーバーシュート+#003バースト+#024インパクトシェイク+ドン")
            if ln.get("pre_se"):
                fx.append(f"直前に{ln['pre_se']}")
            fx += ln.get("se", [])
            fx += [n for k, n in [("freeze", "#040フリーズフレーム"), ("shine", "#022ライトスイープ"), ("tint", "金色に転調"), ("chart", "図解(棒グラフ)+#007カウントアップ")] if ln.get(k)]
            if i == 0:
                fx += ["サウンドロゴ"] + (["冒頭フック3段(#005マスクリビール+#002スタガー)"] if hook else [])
            body = ["【声】" + re.sub(r"[{}|]", "", ln["say"]), "【演出】" + "・".join(fx)]
            if ln.get("note"):
                body.append("【狙い】" + ln["note"])
            for para in body:
                for wl in textwrap.wrap(para, 16):
                    d.text((x, ty), wl, font=font, fill="black")
                    ty += 24
    sheet.save(out)


if __name__ == "__main__":
    main()
