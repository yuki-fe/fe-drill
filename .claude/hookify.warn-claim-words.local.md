---
name: warn-claim-words
enabled: true
event: file
action: warn
conditions:
  - field: file_path
    operator: regex_match
    pattern: (^|[\\/])(build\.py|config\.json|data[\\/]|static[\\/]|line-bot[\\/]|make_[^\\/]*\.py|notes[\\/]src[\\/])
  - field: new_text
    operator: regex_match
    pattern: 公式サイト|公式の|IPA公認|IPA 公認|必ず合格|絶対合格|ここだけ|確実に受か
---

**試験の主催者と関係があるように見える言葉や、確かめられない言い切りが入っていないか確認する。**

「公式」「IPA 公認」「必ず合格」「ここだけ」などは、サイト・投稿・資料のどれにも使わない（CLAUDE.md の決まりごと）。
数学の「公式」や、他社サービスの「公式マーケット」のような意味なら問題ない。
