# 定期作業の手順

## A. 自動で動いている予約タスク(Claude の scheduled tasks。ユーザーのアカウント)
| 名前 | いつ(日本時間) | 何をする | 状態(11-09) |
|---|---|---|---|
| ショート数値チェック | 毎日 20:49 | `shorts-kit` で `python3 tracker.py snapshot` → `report --hours 24` と `--hours 48` → `data/snapshots.jsonl` をコミットして `claude/shorts-kit` に push。nori: 投稿から 7 日たった動画の「7日再生÷中央値 3,677・高評価率・コメント数」を PLAYBOOK 4.998 に記入、登録者の週ごとの増減を報告。変化なしなら 1 行「変化なし」 | 成功 |
| ブランチ同期(PLAYBOOK) | 毎日 20:17 | `origin/claude/*` の各ブランチを `claude/shorts-kit` に取り込む(追記同士の衝突は両方残す、書き換え同士の衝突は飛ばして報告)。force push しない | 成功 |
| やり直し分析 | 毎日 21:00 | 直近 24 時間の briefs の「ユーザー指示」節とコミットから、やり直しの原因 TOP3 と改善文案を出す。やり直しがあればプッシュ通知 | 成功 |
これらの予約タスクのプロンプトの全文は、Claude の scheduled tasks(list_triggers)で見られる。

## B. 動画 1 本を作る手順(毎回)
1. **素材を受け取る**: ユーザーが GigaFile の URL を渡す → `output/<案件>/` に保存。ページの cookie を付けて `download.php?file=<ID>`
2. **中身を確かめる**: `ffmpeg -i src.mp4 -ac 1 -ar 16000 audio.wav` → `python3 transcribe.py audio.wav --model-dir <ReazonSpeech> --vad <silero_vad.onnx> --out src.srt`。数秒おきのコマを並べて画面を見る。聞き取れない所は VAD なしで区切って聞き直す
3. **案を出す**: 入り口動画か信頼動画かを決める。PLAYBOOK 4.31(冒頭フック 4 分類)・4.9986(疑問の順)・4.9987(デザインの使い分け)・4.9989(型)を当てる。冒頭の型を絵コンテに書く
4. **絵コンテ**(関門 2・ユーザーの承認が要る): 各カットに秒・見ている人の疑問・元動画の時刻・効果音を書いた一覧画像を出す
   - 手法の動画: `chart_short.py --board`(1022 v15 の形)。素材は高画質のスクリーンショット(`pics`)
   - 入り口動画: `neon_short.py --frames`(図解ネオン白版・`fx_spread_learn.py` が舞台)
5. **台本**: `shorts-kit/scripts/<名前>_vN.json`。直したら版を上げる(上書きしない)。`briefs/<名前>.md` に「## vN: ユーザー指示」として変更点を追記
6. **書き出し**: `python3 chart_short.py scripts/X.json --out output/X.mp4`(または `neon_short.py`)。重い書き出しは 1 本ずつ
7. **検品**(関門 4): `python3 critic.py output/X.mp4 --sheet output/X_sheet.png` → コンタクトシートを目で見る。音量は `ffmpeg -af ebur128=peak=true` で -14 LUFS 前後か確認
8. **声**: VOICEVOX を起動 → 台本の各カットに `"say"` を入れる → 声の長さに合わせて `dur` を延ばす → `"voice"` `"say_speed": 1.2` `"loudness"` を入れて書き出す
9. **投稿文セット**: `copy/<名前>_vN.md`(タイトル 3 案・説明文 A/B・固定コメント・タグ・人が確認すること・出典)
10. **納品**: 動画・コンタクトシート・投稿文をユーザーに送る。コミットして作業ブランチに push。知見は PLAYBOOK に書いて `claude/shorts-kit` にも push
11. **投稿後**: 予約タスクの数値チェックが 7 日後の数字を PLAYBOOK に入れる → 型・仮説を更新

## C. ユーザーへの報告の形
- 日本語。結論(30〜80字)→ 根拠 → 具体的なアクション → 代替案 → リスク・注意点
- 完了報告には実行した検証(コマンド・結果)を書く。やっていない検証は理由を書く
- 長い作業は区切りごとに「完了したこと・次にやること・気になっていること」
