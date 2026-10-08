# CLAUDE.md

このファイルは、このリポジトリで作業する Claude Code 向けのガイドです。人向けの説明は `README.md` にある。

## プロジェクト概要

基本情報技術者試験（FE）の学習サイト **「FE用語ドリル」** と、その運用の仕組み。運営者は Yuki-fe（個人・副業）。

- **サイト**: https://yuki-fe.github.io/fe-drill/ （GitHub Pages。リポジトリ `yuki-fe/fe-drill` の `main` ブランチの `/docs`）
  - 科目A: 用語 345語の単語帳（カード・4択・書いて答える・意味から答える、間違えた用語の復習）と、用語ごとの解説ページ
  - 科目B: 擬似言語のプログラムを **1行ずつ再生して変数の変化を見せる** のが売り。トレース練習・穴埋め・アルゴリズム図鑑・セキュリティ事例・記法クイズ・シミュレータ
- **LINE 運用ボット**（`line-bot/`、Google Apps Script）: 運営者だけが使う。毎朝のレポート、ニュース、お問い合わせ、Instagram の投稿
- **SNS**: Instagram（情報系の学生向けに、IT の知識とニュースを発信）と YouTube ショート
- お問い合わせ: Google フォーム https://forms.gle/s4yB1xMbcoRqZps2A （回答のスプレッドシートにボットがつながっている）
- アクセス解析: GA4（測定ID `G-4FY1CNV38B`）、Google Search Console

## フォルダ構成

| パス | 内容 |
|---|---|
| `config.json` | サイト名・公開 URL・運営者・GA・広告の設定 |
| `build.py` | サイトを生成する（`docs/` に書き出す）。運営者情報・プライバシーポリシーの文面もここ |
| `data/terms.json` | 用語データ。`id` は URL（`terms/0001.html`）になるので、**公開後に変えたり使い回したりしない** |
| `data/b/*.json` | 科目Bの問題（algorithms / trace / fill / security / notation） |
| `static/` | `docs/` にそのままコピーされる。`assets/`（CSS・JS）、`ig/`（Instagram の画像・動画と投稿文の JSON） |
| `static/assets/pseudo.js` | 擬似言語のインタプリタ。ビューア・答え合わせ・リール動画すべてがこれで動く |
| `docs/` | **生成物。直接編集しない**（ビルドのたびに作り直される）。ただし GitHub Pages が使うので commit はする |
| `checks/` | ビルドで作られる確認ページ（`b-check.html`）。commit しない |
| `make_ig_images.py` | 用語クイズの投稿画像（1080×1350 の2枚組）と投稿文を作る |
| `make_b_media.py` | 科目Bのリール動画（1080×1920、H.264）とトレースクイズの画像を作る。Edge と FFmpeg を使う |
| `make_intro_media.py` | Instagram の最初の投稿（サイト紹介のフィード5枚・リール・ストーリー2枚と投稿文）を `static/ig/intro/` に作る。一度きり |
| `line-bot/` | LINE ボットのプログラム。役割ごとの .gs（`config` 設定・setup / `talk` 話し方 / `report` 毎朝のレポート / `news` / `instagram` / `inquiry` お問い合わせ / `line` Webhook と送信）と `appsscript.json`。合言葉（トークン）は入れない |
| `line-bot/test/run_test.py` | ボットの動作テスト（モックで動かす。Google や LINE には接続しない） |
| `notes/` | **公開しない**（`.gitignore` 済み）。`pdf/` 手順書の PDF、`src/` その元の HTML、`brand/` アイコン画像 |

## よく使うコマンド

```powershell
python build.py                         # docs/ を作り直す（エラー・注意が出たら直す）
python -m http.server 8000 -d docs      # http://localhost:8000 で確認
python make_ig_images.py 120            # 用語クイズのストックを 120 投稿分まで作る
python make_b_media.py 16               # リール動画を 16 本まで作る（先に build.py を実行）
python line-bot/test/run_test.py        # ボットのテスト。最後に ALL OK
python notes/src/make_pdf.py 名前        # notes/src/名前.html から notes/pdf/名前.pdf を作る
```

- Windows のコンソールは cp932 なので、日本語を出力するスクリプトは `PYTHONIOENCODING=utf-8` を付けて動かす
- Python のパッケージは `requirements.txt`（Pillow・imageio-ffmpeg）。サイト専用の `.venv` に入れて、`.venv\Scripts\python` で動かす。FFmpeg は `imageio-ffmpeg` に入っているもの（環境変数 `FFMPEG` で別のものも指定できる）
- Bash の長いヒアドキュメントは失敗しやすい。長い内容は Write でファイルに書いてから実行する

## 公開までの流れ

1. 編集する
2. `python build.py`
3. 科目Bを触ったら `checks/b-check.html` をブラウザで開き、**ALL OK** を確認する
4. 運営者が **GitHub Desktop** で commit → push する（運営者はコマンドの git に慣れていない。手順を説明するときは GitHub Desktop の画面で説明する）
5. 数分で公開サイトに反映される

## LINE ボット（`line-bot/`）

- Apps Script は回答のスプレッドシートに付いている。**ファイルを直したら、運営者が Apps Script のエディタに貼り付けて「デプロイ → デプロイを管理 → 新バージョン」で公開する**（これをしないと反映されない）
- 直したら必ず `python line-bot/test/run_test.py` を動かす。新しい機能にはテストのシナリオも足す
- キャラクターは **先輩エンジニア**。返事は AI ではなく `TALK` の決まった文（費用をかけないため）。口調をそろえる
- 運営者だけが使う（`登録 合言葉` で `OWNER_USER_ID` を登録）。返信（reply）は無料、プッシュは月 200 通まで（吹き出し5個で1通）なので、プッシュは増やしすぎない
- スクリプト プロパティ: `LINE_TOKEN` `WEBHOOK_KEY` `SETUP_CODE` `OWNER_USER_ID` `NEWS_GENRES` `GA_PROPERTY_ID` `IG_TOKEN` `IG_USER_ID` ほか、`IG_` で始まる状態の記録
- トリガー: `onFormSubmit`、`dailyReport`（毎朝8時）、`igWorker`（10分ごと）、`refreshInstagramToken`（毎週）。関数名を変えるとトリガーが切れる
- GCP は標準プロジェクト「fe-drill-line」（Search Console API・Analytics Data API を有効化済み）

### Instagram

- Facebook ログイン方式。API は `https://graph.facebook.com/v23.0`、トークンは Facebook ページのトークン（期限なし）。Facebook ページ「Fe用語ドリル」と連携
- 投稿の種類は `IG_KINDS`: 用語クイズ（term）・トレースクイズ（trace）・リール動画（reel）。曜日ごとの種類は `CONFIG.rotation`（日〜土: reel, term, term, trace, term, reel, term）
- ストックはサイトに置いた `ig/posts.json`・`ig/trace-posts.json`・`ig/reels.json`。投稿すると次へ進む。**リールは減りが早い**（16本・週2本で約2か月分）
- 投稿の直後に、サイトの紹介コメント（`PIN_COMMENTS`）を自動で付ける。**コメントの固定は API でできないので、運営者がアプリで固定する**
- YouTube ショートは自動投稿しない（未審査のアプリから API で上げた動画は非公開に固定されるため）。リール投稿後にタイトルと説明を LINE に送り、運営者が手で上げる
- 最初のサイト紹介リールは、LINE の「紹介リール」で投稿する（`ig/intro/intro.json` を読む。一度だけ。投稿済みは `IG_INTRO_DONE`。リールのストックは進めない）
- ニュースは今は LINE に届くだけ。Instagram の「今週のITニュース」の投稿は未実装

## 決まりごと

- ユーザーへの回答は **日本語**。運営者は初心者寄りなので、手順は画面のボタン名まで具体的に書く
- 手順書・計画などの資料は **PDF** で作る: `notes/src/〇〇.html` を書く → `python notes/src/make_pdf.py 〇〇` → PDF を開いて崩れを確認。PDF のファイル名は日本語のタイトル
- 「公式」「IPA」など試験の主催者と関係があるように見える言葉、「必ず合格」「ここだけ」など確かめられない言い切りは、サイト・投稿・資料のどれにも使わない
- ニュースは見出し・媒体名・自分の言葉のひとことまで。記事の本文や画像は載せない
- 広告は「PR」の表示を消さない（ステルスマーケティング規制）
- トークン・合言葉・個人情報はリポジトリに入れない。リポジトリは **公開** なので、`notes/` や画像の置き場所に注意する
- 用語の説明は AI の支援で作ったもの。数値や法律の内容を足すときは特に確かめる

## 未決定・これからの候補

- Instagram の「今週のITニュース」投稿（ボットがニュースを選ぶボタンと表紙を出す）
- AdSense（独自ドメインが必要）、サブスク
