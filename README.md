# FE用語ドリル

基本情報技術者試験の用語を覚える静的サイトです。`python build.py` を実行すると `docs/` に全ページが書き出され、そのまま GitHub Pages で公開できます。サーバもデータベースも要りません。

## フォルダの中身

| パス | 内容 | 編集するか |
|---|---|---|
| `config.json` | サイト名・公開URL・運営者・広告やアフィリエイトの設定 | する |
| `data/terms.json` | 用語データ（345語） | する |
| `build.py` | ページを生成するスクリプト。運営者情報・プライバシーポリシーの文面もここにある | 文面を変えるとき |
| `static/assets/` | CSS と JavaScript（学習機能・確認問題） | 見た目や機能を変えるとき |
| `docs/` | 生成されたサイト。**直接編集しない**（ビルドのたびに作り直される） | しない |
| `make_ig_images.py` | Instagram 投稿用の画像と投稿文（`static/ig/`）を作る。`python make_ig_images.py 120` で投稿のストックを増やす | ストックを増やすとき |
| `line-bot/` | LINE 運用ボット（Google Apps Script）のプログラム。合言葉は入っていない | 話し方やジャンルを変えるとき |

## 普段の作業

```powershell
cd "C:\Users\admin\Desktop\claude FE対策サイト"
python build.py                       # docs/ を作り直す
python -m http.server 8000 -d docs    # http://localhost:8000 で確認（Ctrl+C で終了）
```

`build.py` は、用語の重複や設定の入れ忘れがあると「エラー」「注意」を表示します。

### 用語を追加・修正する

`data/terms.json` に次の形で追記します。

```json
{"id": "0346", "field": "T", "sub": "ネットワーク", "term": "用語名", "desc": "説明文"}
```

- `field` は `T`（テクノロジ系）/ `M`（マネジメント系）/ `S`（ストラテジ系）
- `id` は今ある最大の番号の次にする。**公開後に既存の id を変えたり使い回したりしない**（ページのURLが `terms/0001.html` のように id で決まるため、検索結果やリンクが切れる）
- 用語名に `（）` を付けると、括弧の中も「書いて答える」で正解になる（例: `排他的論理和（XOR）`）

## 科目B（`data/b/`）

| ファイル | 中身 | ページ |
|---|---|---|
| `algorithms.json` | アルゴリズム図鑑（コード・解説・確認用の正解 `expect`） | `b/algorithms/〇〇.html` |
| `trace.json` | トレース練習（`line` 行目を実行した直後の `vars` を答える。正解の表は自動で作られる） | `b/trace.html` |
| `fill.json` | 穴埋め問題（コードの `{{a}}` が空欄。`tests` で正解だけが通ることを確かめる） | `b/fill.html` |
| `security.json` | セキュリティ事例 | `b/security.html` |
| `notation.json` | 擬似言語の書き方クイズ | `b/notation.html` |
| `kakomon.json`（任意） | IPA 公開問題の解説。ファイルがあるときだけページができる | `b/kakomon/` |

- `terms` に用語名を書くと、その用語ページに「科目Bで練習する」のリンクが付く（用語名は `data/terms.json` と完全に同じにする）
- プログラムは `static/assets/pseudo.js`（擬似言語のインタプリタ）で実際に動かしている
- **問題を追加・修正したら、`python build.py` の後に `checks/b-check.html` をブラウザで開き、「ALL OK」になることを確かめる**。図鑑の結果、穴埋めの正解・不正解、記法クイズの答えを全部動かして確かめる
- IPA の過去問を使う場合は、IPA の最新の利用条件を確認してから入れる

## 公開する（GitHub Pages・無料）

1. [GitHub](https://github.com/) のアカウントを作る
2. [GitHub Desktop](https://desktop.github.com/) を入れてログインする
3. GitHub Desktop で「File → Add local repository」からこのフォルダを選び、「create a repository」で登録する
   - Name は `fe-drill` など。「Keep this code private」は**外す**（無料プランの Pages は公開リポジトリが前提）
4. 「Publish repository」を押す
5. GitHub のリポジトリのページで **Settings → Pages** を開き、「Deploy from a branch」・ブランチ `main`・フォルダ `/docs` を選んで Save
6. 数分後に `https://ユーザー名.github.io/fe-drill/` で見られるようになる
7. `config.json` の `base_url` をそのURLに変え、`python build.py` → GitHub Desktop で Commit → Push

以降は「編集 → `python build.py` → Commit → Push」で更新されます。

### 公開前に `config.json` で埋めるもの

- `base_url`: 公開するURL（末尾の `/` は不要）
- `operator`: 運営者名（ハンドルネームでよい）
- `contact`: お問い合わせ先。メールアドレスか、Google フォームのURL（`https://` から始まるものはリンクになる）

## 検索に載せる

1. [Google Search Console](https://search.google.com/search-console) にサイトを登録する
2. 「サイトマップ」に `sitemap.xml` を送信する

用語ページが検索結果に出るまでには、数週間〜数か月かかります。

## 収益化

### アフィリエイト（最初に始めやすい）

- [Amazonアソシエイト](https://affiliate.amazon.co.jp/): 参考書を紹介する。審査は、サイトを公開して中身がそろってから申し込む
- [A8.net](https://www.a8.net/) などの ASP: 資格の通信講座の広告がある

もらった広告コード（HTML）を `config.json` の `affiliate_html` に貼ると、用語ページと用語一覧に「PR」の表示付きで出ます。Amazon を使うなら `amazon_associate` を `true` にすると、プライバシーポリシーに必要な文言が入ります。

> 2023年10月から、広告であることを隠した宣伝はステルスマーケティングとして景品表示法で禁止されています。広告の枠に自動で付く「PR」の表示は消さないでください。

### Google AdSense

- **`github.io` のアドレスのままでは申し込めません**。独自ドメイン（年1,500円前後）を取って、GitHub Pages に設定してから申請します
  - ドメインを取得 → GitHub の Settings → Pages → Custom domain に入力 → ドメイン会社の DNS 設定で GitHub を指す（手順は GitHub のヘルプ「Managing a custom domain」）
- 審査では、運営者情報・お問い合わせ先・プライバシーポリシーと、中身が十分にあることが見られます。用語ページに「試験での問われ方」「覚え方」などの独自の解説を足していくと、通りやすくなります
- 承認されたら、`config.json` の `adsense_client` に `ca-pub-...` を入れてビルドします。広告のコード、`ads.txt`、プライバシーポリシーの広告の説明が自動で入ります

### アクセス解析

Google アナリティクスの測定ID（`G-...`）を `google_analytics_id` に入れると、全ページに計測タグとプライバシーポリシーの説明が入ります。

## 公開前のチェックリスト

- [ ] 用語の説明に誤りがないか確認した（AIの支援で作った文章なので、特に数値や法律の内容）
- [ ] `config.json` の `base_url` / `operator` / `contact` を埋めた
- [ ] 運営者情報の「用語の説明について」の文面が実態と合っている（`build.py` の `build_about`）
- [ ] IPA の過去問を載せる場合は、IPA のサイトで最新の利用条件を確認した
- [ ] 副業の収入が年20万円を超えたら確定申告が必要になる（会社員の場合）
