#!/bin/bash
# このセッションでコミットした分を、既定ブランチ claude/shorts-kit にも反映する(Stop で動く)。
# 早送り(fast-forward)できるときだけ push する。できないときは何もしない(次の取り込みで解消される)。
set -uo pipefail
DEFAULT=claude/shorts-kit
cd "${CLAUDE_PROJECT_DIR:-.}" 2>/dev/null || exit 0
git rev-parse --git-dir >/dev/null 2>&1 || exit 0
[ -e "$(git rev-parse --git-dir)/MERGE_HEAD" ] && exit 0
timeout 20 git fetch -q origin "$DEFAULT" 2>/dev/null || exit 0
git merge-base --is-ancestor HEAD "origin/$DEFAULT" 2>/dev/null && exit 0          # 反映済み
git merge-base --is-ancestor "origin/$DEFAULT" HEAD 2>/dev/null || exit 0          # 早送りできない
timeout 30 git push -q origin "HEAD:$DEFAULT" >/dev/null 2>&1 || true
exit 0
