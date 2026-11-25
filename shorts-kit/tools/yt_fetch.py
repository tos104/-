#!/usr/bin/env python3
"""yt_fetch: YouTubeリンクから「見る」ための材料を一式そろえるラッパー(ポータブル版)。

使い方:
  python3 yt_fetch.py <YouTubeのURL> [--video] [--frames N] [--out DIR]

出力 (既定: リポジトリの shorts-kit/research_dl/<動画ID>/):
  meta.txt        タイトル・長さ・投稿者・投稿日・再生数の要約
  info.json       yt-dlp のメタデータ全量
  subtitles.srt   日本語字幕 (手動字幕優先、無ければ自動字幕)
  transcript.txt  字幕から時刻を外した本文テキスト
  thumbnail.jpg   サムネイル画像
  frames/         動画から等間隔で切り出した静止画 (既定5枚)
  video.mp4       --video を付けた時だけ動画本体を残す

前提: yt-dlp (PATH 上、または python -m yt_dlp) と ffmpeg (フレーム切り出し用)。
要点: --extractor-args youtube:player_client=android を必ず付けること。
終了コード: 0=成功 / 2=yt-dlp が無い / 3=取得不可(ボット判定・ログイン必須) / 1=その他の失敗
"""
import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path


def _find_ytdlp():
    exe = shutil.which("yt-dlp")
    if exe:
        return [exe]
    probe = subprocess.run([sys.executable, "-m", "yt_dlp", "--version"],
                           capture_output=True, text=True)
    if probe.returncode == 0:
        return [sys.executable, "-m", "yt_dlp"]
    return None


YTDLP_CMD = _find_ytdlp()
BASE_OUT = Path(__file__).resolve().parent.parent / "research_dl"
CLIENT_ARGS = ["--extractor-args", "youtube:player_client=android", "--retries", "5"]
BLOCK_HINTS = ("Sign in to confirm", "not a bot", "members-only", "Members-only",
               "Private video", "login required", "HTTP Error 403")


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def srt_to_text(srt_path: Path) -> str:
    lines, seen = [], set()
    for raw in srt_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        s = raw.strip()
        if not s or s.isdigit() or "-->" in s:
            continue
        if s not in seen:
            seen.add(s)
            lines.append(s)
    return "\n".join(lines)


def report_blocked(stderr: str):
    print("=" * 60, file=sys.stderr)
    print("【取得不可】この環境からは、この動画を取得できませんでした。", file=sys.stderr)
    print("YouTube のボット判定、またはログイン必須(メンバー限定・非公開・年齢制限)のためです。", file=sys.stderr)
    print("動画なしで作業を進めず、必ず次のどれかをしてください:", file=sys.stderr)
    print("  1) research_dl/<動画ID>/ に取得済み素材が既に入っていないか確認する", file=sys.stderr)
    print("  2) 無ければ、ユーザーに「Muse(VM)側で取得して素材をこのリポジトリへ入れてもらう」よう伝える", file=sys.stderr)
    print("  3) 取得できない事実と理由を、そのまま正直に報告する(ごまかさない)", file=sys.stderr)
    print("=" * 60, file=sys.stderr)
    print(stderr[-800:], file=sys.stderr)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("url")
    ap.add_argument("--video", action="store_true", help="動画本体も残す")
    ap.add_argument("--frames", type=int, default=5, help="切り出す静止画の枚数")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    if YTDLP_CMD is None:
        print("ERROR: yt-dlp が見つかりません。次のコマンドで入れてから再実行してください:", file=sys.stderr)
        print("  pip install -U yt-dlp   (または: python3 -m pip install -U yt-dlp)", file=sys.stderr)
        sys.exit(2)

    # 1) メタデータ
    r = run([*YTDLP_CMD, *CLIENT_ARGS, "-j", args.url])
    if r.returncode != 0:
        if any(h in r.stderr for h in BLOCK_HINTS):
            report_blocked(r.stderr)
            sys.exit(3)
        print("ERROR: メタデータ取得に失敗しました", file=sys.stderr)
        print(r.stderr[-800:], file=sys.stderr)
        sys.exit(1)
    info = json.loads(r.stdout)
    vid = info["id"]
    out = Path(args.out) if args.out else BASE_OUT / vid
    out.mkdir(parents=True, exist_ok=True)
    (out / "info.json").write_text(json.dumps(info, ensure_ascii=False, indent=1), encoding="utf-8")
    meta = (
        f"title: {info.get('title')}\n"
        f"uploader: {info.get('uploader')}\n"
        f"duration: {info.get('duration')} sec\n"
        f"upload_date: {info.get('upload_date')}\n"
        f"view_count: {info.get('view_count')}\n"
        f"url: {info.get('webpage_url')}\n"
        f"description:\n{info.get('description') or ''}\n"
    )
    (out / "meta.txt").write_text(meta, encoding="utf-8")
    print(f"[ok] メタデータ: {info.get('title')} ({info.get('duration')} sec)")

    # 2) 日本語字幕 (手動優先・無ければ自動)
    run([*YTDLP_CMD, *CLIENT_ARGS, "--skip-download", "--write-subs", "--write-auto-subs",
         "--sub-langs", "ja.*", "--sub-format", "vtt/srt/best", "--convert-subs", "srt",
         "-o", str(out / "subs.%(ext)s"), args.url])
    srt = out / "subs.ja.srt"
    if not srt.exists():
        cands = sorted(out.glob("subs.ja*.srt"))
        if cands:
            srt = cands[0]
    if srt.exists():
        srt.rename(out / "subtitles.srt")
        for leftover in out.glob("subs.*.srt"):
            leftover.unlink()
        (out / "transcript.txt").write_text(srt_to_text(out / "subtitles.srt"), encoding="utf-8")
        print("[ok] 日本語字幕 -> subtitles.srt / transcript.txt")
    else:
        print("[--] 日本語字幕なし (手動・自動とも無し)")

    # 3) サムネイル
    run([*YTDLP_CMD, *CLIENT_ARGS, "--skip-download", "--write-thumbnail",
         "--convert-thumbnails", "jpg", "-o", str(out / "thumb.%(ext)s"), args.url])
    th = out / "thumb.jpg"
    if th.exists():
        th.rename(out / "thumbnail.jpg")
        print("[ok] サムネイル -> thumbnail.jpg")

    # 4) フレーム切り出し用に低画質で一時ダウンロード
    if shutil.which("ffmpeg") is None:
        print("[--] ffmpeg が無いためフレーム切り出しと動画保存は省略しました")
        print(f"完了: {out}")
        return
    tmp_video = out / "_tmp_video.mp4"
    r = run([*YTDLP_CMD, *CLIENT_ARGS, "-f", "worst[ext=mp4]/worst",
             "-o", str(out / "_tmp_video.%(ext)s"), args.url])
    got = tmp_video if tmp_video.exists() else next(iter(out.glob("_tmp_video.*")), None)
    if got and args.frames > 0:
        fdir = out / "frames"
        fdir.mkdir(exist_ok=True)
        dur = info.get("duration") or 0
        made = 0
        for i in range(args.frames):
            t = max(1, int(dur * (i + 1) / (args.frames + 1)))
            rr = run(["ffmpeg", "-loglevel", "error", "-ss", str(t), "-i", str(got),
                      "-frames:v", "1", str(fdir / f"frame_{i+1:02d}_{t}s.jpg")])
            if rr.returncode == 0:
                made += 1
        print(f"[ok] フレーム {made} 枚 -> frames/")
    if got:
        if args.video:
            got.rename(out / "video.mp4")
            print("[ok] 動画本体 -> video.mp4")
        else:
            got.unlink()

    print(f"完了: {out}")


if __name__ == "__main__":
    main()
