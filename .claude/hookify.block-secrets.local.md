---
name: block-secrets
enabled: true
event: file
action: block
conditions:
  - field: file_path
    operator: regex_match
    pattern: ^(?!.*[\\/]notes[\\/])
  - field: new_text
    operator: regex_match
    pattern: AIza[0-9A-Za-z_\-]{35}|EAA[0-9A-Za-z]{60,}|gh[pousr]_[0-9A-Za-z]{30,}|sk-[0-9A-Za-z_\-]{30,}|(TOKEN|SECRET|API_KEY|SETUP_CODE|WEBHOOK_KEY)['"]?\s*[:=]\s*['"][0-9A-Za-z+/=_\-]{20,}['"]
---

**トークン・API キー・合言葉らしい文字列をリポジトリに書こうとしている。**

このリポジトリは公開なので、合言葉は入れない。

- LINE ボット → スクリプト プロパティ
- 手元のキー → `notes/` の下（`.gitignore` 済み。例: `notes/曲の動画/pexels_api_key.txt`）

コードではキーをファイルやプロパティから読むようにする。
