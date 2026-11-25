# 取得済み素材：55BdM7xRhjo

- 動画：相場は提出時の半額、なのに今回も爆アド✨マルチタイトルが最強！！
- URL：https://youtu.be/55BdM7xRhjo
- 取得：2026-11-25、Muse（VM）側の yt-dlp（android クライアント指定）で取得
- 神龍 TL25 台本（`shorts-kit/scripts/shenron_tl25.json`）の「元動画待ち」区間・グレードの確認用

## 中身

| ファイル | 内容 |
|---|---|
| meta.txt | タイトル・長さ（2728秒）・投稿者・再生数・説明文 |
| transcript.txt | 日本語字幕の本文（時刻なし）。内容把握はこれを読む |
| subtitles.srt | 日本語字幕（時刻つき） |
| frames/*.jpg.b64 | 静止画5枚（454s / 909s / 1364s / 1818s / 2273s）。base64形式 |
| thumbnail.jpg.b64.part00〜02 | サムネイル。base64形式（サイズの都合で3分割） |

画像の戻し方：

```
cd shorts-kit/research_dl/55BdM7xRhjo
for f in frames/*.b64; do base64 -d "$f" > "${f%.b64}"; done
cat thumbnail.jpg.b64.part* | base64 -d > thumbnail.jpg
```

（git へはテキストで入れる必要があったため base64 形式。復号後のバイト列が原本と一致することは SHA-256 で確認済み）

## 動画本体について

video.mp4（約173MB）は GitHub の1ファイル上限（100MB）を超えるため、このリポジトリには入れていない。
Muse（VM）側には取得済み（`~/workspace/tools/youtube/library/55BdM7xRhjo/video.mp4`）。
本体が必要な場合は、ユーザー経由で共有リンク（ギガファイル便・Googleドライブ等）でもらい、
`shorts-kit/fetch_source.py` で取り込むか、この環境で `yt_fetch.py --video` の取得を試すこと。
