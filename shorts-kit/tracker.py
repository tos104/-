#!/usr/bin/env python3
"""公開数値のスナップショットを取り、前回との差分レポートを出す。

  python3 tracker.py snapshot   # data/snapshots.jsonl に1行追記
  python3 tracker.py report     # 最新と前回(既定)の差分を表示 / --hours 24 で約24時間前と比較
取れるのは誰でも見られる数値(登録者・再生・高評価)だけ。視聴維持率などは YouTube Studio 側。
"""
import argparse, datetime as dt, json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from yti import call, walk, txt, shorts, views

CHANNELS = {
    "tt": "UC3oXfarxiGrU2TigmMBWhfg",      # ティーティーチャンネル(委託元)
    "mii": "UCCPmaRgms9FjAci2QnQR-SA",     # Miiのポケカタイム(参考)
    "taihei": "UCdBU4qCDToP-H_ImP1kqkKg",  # タイヘイ@サウスTV(参考)
}
OWN = "tt"
OWN_DETAIL = 15  # 委託元の最新N本は高評価数と投稿日も取る
DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "snapshots.jsonl")


def subs(bid):
    hdr = json.dumps(call("browse", {"browseId": bid}).get("header", {}), ensure_ascii=False)
    m = re.search(r"チャンネル登録者数 ([\d.]+)(万)?人", hdr)
    return None if not m else float(m.group(1)) * (1e4 if m.group(2) else 1)


def detail(vid):
    d = call("next", {"videoId": vid})
    s = json.dumps(d, ensure_ascii=False)
    likes = re.search(r'"likeCountIfIndifferentNumber": "(\d+)"', s)
    p = next(walk(d, "videoPrimaryInfoRenderer"), {})
    return {"likes": int(likes.group(1)) if likes else None, "date": txt(p.get("dateText"))}


def snapshot():
    snap = {"ts": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "channels": {}}
    for name, bid in CHANNELS.items():
        items = []
        for i, (vid, title, vc) in enumerate(shorts(bid, pages=4)):
            it = {"id": vid, "title": re.split(r"\s#|＃", title or "")[0].strip(), "views": int(views(vc))}
            if name == OWN and i < OWN_DETAIL:
                it.update(detail(vid))
            items.append(it)
        snap["channels"][name] = {"subs": subs(bid), "shorts": items}
    os.makedirs(os.path.dirname(DATA), exist_ok=True)
    with open(DATA, "a", encoding="utf-8") as f:
        f.write(json.dumps(snap, ensure_ascii=False) + "\n")
    print(f"snapshot {snap['ts']} -> {DATA}")


def report(hours):
    snaps = [json.loads(l) for l in open(DATA, encoding="utf-8")]
    cur = snaps[-1]
    t = lambda s: dt.datetime.fromisoformat(s["ts"])
    prev = snaps[-2] if len(snaps) > 1 else None
    if hours and len(snaps) > 1:
        target = t(cur) - dt.timedelta(hours=hours)
        prev = min(snaps[:-1], key=lambda s: abs(t(s) - target))
    span = (t(cur) - t(prev)).total_seconds() / 3600 if prev else 0
    print(f"# {cur['ts']}  (比較: {prev['ts'] if prev else 'なし'} / {span:.1f}時間)")
    for name, ch in cur["channels"].items():
        pch = prev["channels"].get(name, {}) if prev else {}
        before = {x["id"]: x for x in pch.get("shorts", [])}
        ds = (ch["subs"] or 0) - (pch.get("subs") or 0) if prev else 0
        print(f"\n## {name}  登録者 {ch['subs']:.0f} ({ds:+.0f})")
        rows = []
        for x in ch["shorts"]:
            b = before.get(x["id"])
            rows.append((x["views"] - b["views"] if b else (None if prev else 0), x))
        new = [x for d, x in rows if d is None and prev]
        for x in new:
            print(f"  NEW  {x['views']:>8,}  {x['title'][:40]}")
        grow = sorted([r for r in rows if r[0] is not None], key=lambda r: -r[0])
        for d, x in grow[:5 if name != OWN else OWN_DETAIL]:
            extra = ""
            if "likes" in x and x["likes"] is not None and x["views"]:
                extra = f"  高評価率 {x['likes'] / x['views'] * 100:.1f}%  {x.get('date', '')}"
            print(f"  {d:+8,}  計{x['views']:>8,}  {x['title'][:40]}{extra}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["snapshot", "report"])
    ap.add_argument("--hours", type=float)
    a = ap.parse_args()
    snapshot() if a.cmd == "snapshot" else report(a.hours)
