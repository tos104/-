#!/bin/bash
# 既定ブランチ claude/shorts-kit の最新(PLAYBOOK・ツール・数値)を、いまのブランチに取り込む。
# SessionStart と UserPromptSubmit で動く。何も変わらなければ何も出力しない。
# 衝突したら取り込みをやめて元に戻し、その旨だけを Claude に伝える(作業中のファイルは壊さない)。
set -uo pipefail
DEFAULT=claude/shorts-kit
cd "${CLAUDE_PROJECT_DIR:-.}" 2>/dev/null || exit 0
git rev-parse --git-dir >/dev/null 2>&1 || exit 0
[ -e "$(git rev-parse --git-dir)/MERGE_HEAD" ] && exit 0   # 手動のマージ中は触らない
timeout 20 git fetch -q origin "$DEFAULT" 2>/dev/null || exit 0
git merge-base --is-ancestor "origin/$DEFAULT" HEAD 2>/dev/null && exit 0   # 取り込み済み
n=$(git rev-list --count "HEAD..origin/$DEFAULT")
if git merge -q --no-edit "origin/$DEFAULT" >/dev/null 2>&1; then
  echo "[自動同期] 既定ブランチ $DEFAULT から ${n} 件の更新を取り込みました(PLAYBOOK.md などが最新になっています)。"
else
  git merge --abort >/dev/null 2>&1
  echo "[自動同期] $DEFAULT の取り込みが衝突または未コミットの変更で止まりました。作業を区切ってコミットしたあと、git merge origin/$DEFAULT で取り込み、衝突は両方の追記を残す形で直してください。"
fi
exit 0
