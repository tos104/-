#!/usr/bin/env python3
"""書き出したショートを検品する(CRITIC 層)。何が・どこで・なぜダメかを数字で出す。

  python3 critic.py video.mp4 [--sheet out/contact.png] [--poster out/poster.png]
基準は PLAYBOOK.md の仮説から。1つでも FAIL があれば終了コード 1。
"""
import argparse, re, subprocess, sys

# 基準は参考動画の実測値に合わせる(2026-10-20 計測)
#   タイヘイ録画: 変化の平均間隔 1.72秒 / 最長の静止 6.1秒 / -13.8 LUFS
#   ユーザー制作の目利きショート: 2.18秒 / 4.4秒 / -13.1 LUFS
RULES = {
    "max_duration": 60.0,     # ショートの尺(秒)
    "first_sound": 0.5,       # 最初の音が出るまで(秒)
    "max_silence": 0.6,       # 無音が続いてよい長さ(秒)
    "max_static": 6.5,        # 画面に大きな変化がない最長(秒)
    "mean_change": 1.8,       # 意味のある変化の平均間隔(秒)
    "loudness": (-15.5, -12.5),  # 統合ラウドネス(LUFS)
}


def ff(args):
    return subprocess.run(["ffmpeg", "-hide_banner", "-nostats"] + args + ["-f", "null", "-"],
                          capture_output=True, text=True).stderr


def duration(path):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
                                capture_output=True, text=True).stdout)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("--sheet")
    ap.add_argument("--poster")
    a = ap.parse_args()
    d = duration(a.video)
    res = []

    def check(name, ok, detail):
        res.append(("PASS" if ok else "FAIL", name, detail))

    check("尺", d <= RULES["max_duration"], f"{d:.1f}秒 (上限 {RULES['max_duration']:.0f})")

    sil = ff(["-i", a.video, "-af", "silencedetect=n=-38dB:d=0.25"])
    starts = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", sil)]
    ends = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", sil)]
    first = ends[0] if starts and starts[0] < 0.05 and ends else 0.0
    check("最初の音", first <= RULES["first_sound"], f"{first:.2f}秒後")
    gaps = [(s, e - s) for s, e in zip(starts, ends) if s > 0.05]
    long_gaps = [(s, g) for s, g in gaps if g > RULES["max_silence"]]
    check("無音の間", not long_gaps, ", ".join(f"{s:.1f}秒から{g:.1f}秒" for s, g in long_gaps) or "なし")

    sc = ff(["-i", a.video, "-vf", "select='gt(scene,0.12)',showinfo"])
    times = [0.0] + [float(x) for x in re.findall(r"pts_time:([\d.]+)", sc)] + [d]
    holds = [(times[i], times[i + 1] - times[i]) for i in range(len(times) - 1)]
    static = [(t, h) for t, h in holds if h > RULES["max_static"]]
    mean = d / max(1, len(times) - 1)
    check("画面変化の平均間隔", mean <= RULES["mean_change"], f"{mean:.2f}秒 ({len(times) - 2}回)")
    check("止まって見える区間", not static, ", ".join(f"{t:.1f}秒から{h:.1f}秒" for t, h in static) or "なし")

    lo = re.search(r"I:\s+(-?[\d.]+) LUFS", ff(["-i", a.video, "-af", "ebur128=framelog=quiet"]))
    lufs = float(lo.group(1)) if lo else float("nan")
    check("ラウドネス", RULES["loudness"][0] <= lufs <= RULES["loudness"][1], f"{lufs:.1f} LUFS")

    for st, name, detail in res:
        print(f"[{st}] {name}: {detail}")

    if a.sheet:  # 1秒ごとのコンタクトシート
        cols = 8
        rows = int(d) // cols + 1
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", a.video, "-vf",
                        f"fps=1,scale=180:-1,drawtext=text='%{{pts\\:hms}}':x=4:y=4:fontsize=16:fontcolor=yellow:box=1:boxcolor=black,"
                        f"tile={cols}x{rows}", "-frames:v", "1", a.sheet], check=True)
    if a.poster:  # 冒頭フックが揃うコマ(0.9秒)をサムネイル候補に
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", "0.9", "-i", a.video, "-frames:v", "1", a.poster], check=True)
    sys.exit(1 if any(r[0] == "FAIL" for r in res) else 0)


if __name__ == "__main__":
    main()
