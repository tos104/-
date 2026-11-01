---
name: kinetic-film
description: 言葉を拍に置くキネティック・タイポ動画(編集ソフトなし・コードだけ)を作るとき。「Kinetic Film」「文字が拍で動く映像」「モーショングラフィックの冒頭」「言葉を0.3秒ごとに積む」と言われたら使う。
---

# キネティック・フィルム(言葉を拍に置く映像)

道具: `shorts-kit/kinetic/`
- `kinetic.html` … 時刻 t を渡すとその瞬間を描くページ(CSSアニメ・乱数なし=同じ台本から毎回同じ映像。MD5一致を確認済み)
- `render_kinetic.py` … 台本JSON → 1080x1920 mp4(効果音は同じ拍の時刻から合成)+ コンタクトシート
- `sample.json` … 台本の例

```
cd shorts-kit && python3 kinetic/render_kinetic.py kinetic/sample.json --out kinetic/out/x.mp4 --sheet kinetic/out/x.png [--bgm bgm.wav]
# 曲に合わせる(音ハメ): 曲の BPM と1拍目を自動検出し、言葉をその拍に置く
python3 kinetic/render_kinetic.py kinetic/sample.json --music song.mp3 --out kinetic/out/x.mp4 --sheet kinetic/out/x.png
```
- `beat_detect.py` … 曲の BPM と1拍目の位置を検出(numpyのみ)。合成テスト曲 92/112/128/150BPM で、BPM誤差0.25以内・拍位置25ms以内(1コマ未満)を確認済み
- 実際の曲(ボーカル入り・テンポ変化あり)では未検証。検出値は書き出し時に表示されるので、ずれたら台本に `bpm` / `offset` を書いて `--bgm` で渡す

## 手順
1. 言葉を拍に置く: 1拍に1〜2語。`bpm` で拍の長さが決まる(128bpm = 0.47秒/拍)。溜めたい語は `len: 2`
2. 各拍に `why`(なぜこの拍があるか)を書く。無いと書き出しが止まる。言えない拍は削る
3. 動き: `style` = slam(叩きつけ)/ pop / tilt3d(3D)/ slide / type(1文字ずつ)。`cam` = push / pull / roll / whip
4. 色: `palette` を2〜3色に絞り、`pal` で拍ごとに切り替える。`burst`(星形)は着地の拍だけ
5. 書き出し → コンタクトシートを目で見る → `CONTRACT.md` の関門4〜5へ

## 守ること(制作契約)
- 文言は承認済みのものだけ。金額・枚数・カード名を作らない
- 音楽は持っていない。曲は人が用意したもの(Suno で作って書き出した mp3 など)を `--music` / `--bgm` で渡す。この環境から suno.com・YouTube は通信できない(2026-10-31 時点・ネットワーク設定で拒否)。無ければ効果音だけ(偽の素材で埋めない)
- 参考映像を真似るときは、先に実測して `PLAYBOOK.md` のスタイルガイドに書く
