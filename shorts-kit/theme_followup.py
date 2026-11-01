#!/usr/bin/env python3
"""「伸びたテーマを深掘りする」は効くのかを、競合のショート一覧(タイトル・再生数)で確かめる。

  python3 theme_followup.py [research/competitors_2026-10-25.json] [--window 10] [--hit 2.0]

方法(各チャンネルの中で比べる。規模の差を消すため 再生÷中央値 の倍率で見る):
- テーマ語 = タイトルに2回以上出るが、全体の10%以下にしか出ない語(ポケカ・PSA のような毎回の語は除く)
- 当たり = 倍率 hit 以上。その後に出た window 本のうち、当たりとテーマ語を共有するものを「深掘り」とする
- 比較1: 深掘り と 同じ期間の深掘りでない動画
- 比較2(対照): 普通の動画(倍率0.67〜1.5)の後に同じテーマを続けた動画。「テーマを続けること自体」の効果と分ける
限界: 相関であり因果ではない/タイトルの語でしかテーマを見ていない/話題そのものの流行と区別できない
"""
import argparse, json, re, statistics as st
from collections import Counter

TOK = re.compile(r"[ァ-ヴー]{2,}|[一-龥]{2,}|[A-Za-z0-9]{3,}")


def tokens(t):
    t = re.sub(r"#\S+", " ", t)  # ハッシュタグは除く
    return set(TOK.findall(t))


def channel(shorts, window, hit):
    sh = list(reversed(shorts))  # 一覧は新しい順 → 古い順に直す
    v = [s["views"] or 0 for s in sh]
    m = st.median(v) or 1
    r = [x / m for x in v]
    tk = [tokens(s["title"]) for s in sh]
    df = Counter(w for t in tk for w in t)
    sal = [{w for w in t if 2 <= df[w] <= max(2, 0.10 * len(sh))} for t in tk]
    out = {"hit_follow": [], "hit_other": [], "base_follow": [], "base_other": []}
    for i in range(len(sh)):
        kind = "hit" if r[i] >= hit else ("base" if 0.67 <= r[i] <= 1.5 else None)
        if not kind or not sal[i]:
            continue
        for j in range(i + 1, min(len(sh), i + 1 + window)):
            key = "follow" if sal[i] & sal[j] else "other"
            out[f"{kind}_{key}"].append(r[j])
    return out, len(sh)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("data", nargs="?", default="research/competitors_2026-10-25.json")
    ap.add_argument("--window", type=int, default=10)
    ap.add_argument("--hit", type=float, default=2.0)
    a = ap.parse_args()
    d = json.load(open(a.data))
    rows = []
    for name, c in d.items():
        if len(c.get("shorts", [])) < 30:
            continue
        o, n = channel(c["shorts"], a.window, a.hit)
        if len(o["hit_follow"]) >= 3 and len(o["hit_other"]) >= 3:
            hf, ho = st.median(o["hit_follow"]), st.median(o["hit_other"])
            bf = st.median(o["base_follow"]) if len(o["base_follow"]) >= 3 else None
            rows.append((name, n, len(o["hit_follow"]), hf, ho, bf))
    print(f"窓={a.window}本 当たり=中央値の{a.hit}倍以上  比較できたチャンネル {len(rows)}")
    print(f"{'チャンネル':<22}{'本数':>5}{'深掘り数':>7}{'深掘り':>8}{'その他':>8}{'対照':>8}")
    for name, n, k, hf, ho, bf in sorted(rows, key=lambda x: -(x[3] / x[4])):
        print(f"{name[:20]:<22}{n:>5}{k:>7}{hf:>8.2f}{ho:>8.2f}{(f'{bf:.2f}' if bf else '-'):>8}")
    lift = [hf / ho for _, _, _, hf, ho, _ in rows]
    up = sum(x > 1 for x in lift)
    print(f"\n深掘り÷その他 の中央値 ×{st.median(lift):.2f}  上がったチャンネル {up}/{len(rows)} ({up / len(rows):.0%})")
    pair = [(hf, bf) for _, _, _, hf, _, bf in rows if bf]
    upb = sum(h > b for h, b in pair)
    print(f"当たり後の深掘り vs 普通の動画の後の同テーマ: 前者が上 {upb}/{len(pair)}  "
          f"倍率の中央値 {st.median([h for h, _ in pair]):.2f} vs {st.median([b for _, b in pair]):.2f}")


if __name__ == "__main__":
    main()
