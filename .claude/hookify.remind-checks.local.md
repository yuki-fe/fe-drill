---
name: remind-checks
enabled: true
event: file
action: warn
conditions:
  - field: file_path
    operator: regex_match
    pattern: (^|[\\/])(data[\\/]b[\\/]|static[\\/]assets[\\/](pseudo|b)\.js|line-bot[\\/]|ranking[\\/])
---

**この変更のあとに確かめること:**

- 科目B（`data/b/`・`pseudo.js`・`b.js`）→ `python build.py` のあと `checks/b-check.html` で **ALL OK**
- LINE ボット（`line-bot/`）→ `python line-bot/test/run_test.py` で **ALL OK**。運営者に「Apps Script に貼って新バージョンでデプロイ」と伝える
- ランキング（`ranking/`）→ `python ranking/test/run_test.py` で **ALL OK**
