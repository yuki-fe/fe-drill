---
name: block-edit-docs
enabled: true
event: file
action: block
conditions:
  - field: file_path
    operator: regex_match
    pattern: (^|[\\/])docs[\\/]
---

**docs/ は生成物なので直接編集しない。**

`docs/` は `python build.py` のたびに作り直される。元を直すこと:

- ページの中身・文面 → `build.py`、`data/*.json`
- CSS・JS・画像 → `static/`（`docs/` にそのままコピーされる）

直したら `python build.py` を実行する。
