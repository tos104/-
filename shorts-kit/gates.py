#!/usr/bin/env python3
"""制作の関門(GATE 1〜6)の状態を確かめ、次にやること・足りない成果物を出す。

  python3 gates.py trade_top3            # 状態を表示
  python3 gates.py trade_top3 --approve 2 --note "絵コンテOK"   # 人の承認を記録

ファイルがある・コマンドが成功した、だけでは完成にしない。
人の承認が要る関門は gates/<name>.json に記録がない限り未通過。
"""
import argparse, datetime as dt, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

GATES = [
    (1, "参照と素材の承認", [("brief", "briefs/{n}.md")], True),
    (2, "スタイルガイドと台本(絵コンテ)の承認", [("style", "PLAYBOOK.md"), ("script", "scripts/{n}*.json"),
                                       ("storyboard", "../output/storyboard_{n}*.png")], True),
    (3, "代表コマの確認", [("storyboard", "../output/storyboard_{n}*.png")], False),
    (4, "仮書き出しとコンタクトシート", [("contact", "../output/contact_*.png")], False),
    (5, "欠陥上位3つの修正", [("review", "reviews/{n}*.md")], False),
    (6, "音・形式・納品物の確認", [("copy", "copy/{n}.md")], True),
]


def exists(pattern, n):
    import glob
    return bool(glob.glob(os.path.join(HERE, pattern.format(n=n))))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("name")
    ap.add_argument("--approve", type=int)
    ap.add_argument("--note", default="")
    a = ap.parse_args()
    path = os.path.join(HERE, "gates", f"{a.name}.json")
    state = json.load(open(path, encoding="utf-8")) if os.path.exists(path) else {}
    if a.approve:
        state[str(a.approve)] = {"at": dt.datetime.now().isoformat(timespec="minutes"), "note": a.note}
        json.dump(state, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    nxt = None
    for no, title, arts, human in GATES:
        missing = [k for k, p in arts if not exists(p, a.name)]
        approved = str(no) in state
        ok = not missing and (approved or not human)
        mark = "通過" if ok else "未通過"
        why = []
        if missing:
            why.append("足りない成果物: " + ", ".join(missing))
        if human and not approved:
            why.append("人の承認待ち")
        if approved:
            why.append(f"承認 {state[str(no)]['at']} {state[str(no)]['note']}")
        print(f"GATE {no} [{mark}] {title}" + (" — " + " / ".join(why) if why else ""))
        if not ok and nxt is None:
            nxt = no
    print(f"\n次: GATE {nxt}" if nxt else "\n全関門を通過")
    sys.exit(0 if nxt is None else 1)


if __name__ == "__main__":
    main()
