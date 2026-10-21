# CLAUDE.md

このファイルは、このリポジトリで作業する Claude Code 向けのガイドです。人向けの説明は `README.md` にある。

## プロジェクト概要

基本情報技術者試験（FE）の学習サイト **「FE用語ドリル」** と、その運用の仕組み。運営者は Yuki-fe（個人・副業）。

- **サイト**: https://fe.yogo-drill.com/ （独自ドメイン。旧 https://yuki-fe.github.io/fe-drill/ は GitHub Pages が自動で転送。GitHub Pages。リポジトリ `yuki-fe/fe-drill` の `main` ブランチの `/docs`）
  - 科目A: 用語 345語の単語帳（カード・4択・書いて答える・意味から答える、間違えた用語の復習）と、用語ごとの解説ページ
  - 科目B: 擬似言語のプログラムを **1行ずつ再生して変数の変化を見せる** のが売り。トレース練習・穴埋め・アルゴリズム図鑑・セキュリティ事例・記法クイズ・シミュレータ
- **LINE 運用ボット**（`line-bot/`、Google Apps Script）: 運営者だけが使う。毎朝のレポート、ニュース、お問い合わせ、Instagram の投稿
- **SNS**: Instagram（情報系の学生向けに、IT の知識とニュースを発信）と YouTube ショート
- お問い合わせ: Google フォーム https://forms.gle/s4yB1xMbcoRqZps2A （回答のスプレッドシートにボットがつながっている）
- アクセス解析: GA4（測定ID `G-4FY1CNV38B`）、Google Search Console
- 姉妹サイト **「ITパスポート用語ドリル」** は別のリポジトリ（デスクトップの `ip-drill`、`yuki-fe/ip-drill`、https://ip.yogo-drill.com/ で公開中。GA4 は別プロパティ）。この build.py をもとに作った。くわしくはそちらの CLAUDE.md
- 3つ目のサイト **「クラウド用語ドリル」**（AWS 認定クラウドプラクティショナー CLF-C02）はデスクトップの `cloud-drill`（`yuki-fe/cloud-drill`、未公開）。ip-drill の build.py をもとに作った。サイト名に「AWS」を入れない（AWS の商標の決まり）
- 4つ目のサイト **「国内旅行業務用語ドリル」**（国内旅行業務取扱管理者試験）はデスクトップの `travel-drill`（`yuki-fe/travel-drill`、未公開。**公開しない予定**（2026-10-21 に運営者が決めた））。cloud-drill の build.py をもとに作った。数字は元の文書で確かめたものだけを書く
- 5つ目のサイト **「生成AI用語ドリル」**（生成AIパスポート試験、2027年2月試験からの新シラバス）はデスクトップの `genai-drill`（`yuki-fe/genai-drill`、未公開、genai.yogo-drill.com の予定）。cloud-drill の build.py をもとに作った
- 6つ目のサイト **「ディープラーニング用語ドリル」**（JDLA の G検定、シラバス 2024）はデスクトップの `dl-drill`（`yuki-fe/dl-drill`、未公開、dl.yogo-drill.com の予定）。genai-drill の build.py をもとに作った。サイト名に「G検定」を入れない
- 7つ目のサイト **「簿記用語ドリル」**（簿記検定3級、2027年4月施行の出題区分表）はデスクトップの `boki-drill`（`yuki-fe/boki-drill`、未公開、boki.yogo-drill.com の予定）。dl-drill の build.py をもとに作った。略語クイズの代わりに勘定科目の分類クイズ（`kamoku.html`）。サイト名に「日商」を入れない
- 7つ目のサイトの「簿記用語ドリル」は、2026-10-19 に **2級（商業簿記・工業簿記）** も足した（3級・2級で300語）
- 8つ目のサイト **「医療事務用語ドリル」** はデスクトップの `iryo-drill`（`yuki-fe/iryo-drill`、未公開、iryo.yogo-drill.com の予定）。dl-drill の build.py をもとに作った。特定の試験に合わせていない（診療報酬請求事務能力認定試験は2025年12月で終了・実施団体は2026年3月に解散）。診療報酬の点数は書かない
- **IPA の試験制度が2027年度から変わる**（2026-10-19 に確認）: 今の制度は2026年度の試験で終わり。応用情報と高度試験は「プロフェッショナルデジタルスキル試験（仮称）」などに再編される案。ITパスポート・基本情報もシラバスが見直される（新シラバス案 Ver.0.1、2026年8〜9月公表）。FE・ITパスポートのサイトは、新シラバスが決まったら見直す
- 入り口のサイト **「用語ドリル」**（https://yogo-drill.com/ の予定、デスクトップの `yogo-drill`、未公開）が各サイトを紹介する（旅行のサイトは載せない）。サイトを公開したら、そちらの `sites.json` の `"public"` を true にしてビルドする

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
| `make_b_media.py` | 科目Bのリール動画（1080×1920、60fps、H.264 CRF 16、音なし）とトレースクイズの画像を作る。上にコード（今の行の帯がすべって動く）、下に **「動きの図」**（`b_visual.py`。`VISUAL = True`）。1行は0.5秒以上。Edge（動かないときは Chrome）と FFmpeg を使う |
| `b_visual.py` | リールの「動きの図」: 配列は箱、番号に使う変数（`[ ]` の中や、それを計算する式の変数）は箱の下の矢印（すべって動く）、代入は値のチップが飛ぶ（「s ← 0 + 3」の式も出す）、if・while で比べる箱はオレンジ、ふつうの変数はカード、再帰は呼び出しの深さ。大域変数は、コードに「大域:」とあるものだけ図に入れる。部品が多いと自動で小さくして収める |
| `make_figs.py` | 用語の **「動く図」**（ステップに分かれた SVG、`static/figs/<用語id>.svg`。利用者が「前へ」「次へ」・図のタップ・左右のスワイプで切り替える。切り替えは `static/assets/fig.js`）と、図のタイトル・手順の文（`data/figs.json`）を作る。用語ページの「図で見る」と、4択・書いて答える問題の答えのあとの「図で見る」に出る。図を足したら `python make_figs.py` → `python build.py`。今は20語（2026-10-20）。「前へ」「次へ」は小さな丸いボタン（‹ ›）と、ステップの点 |
| `make_mv.py`・`make_mv_strategy.py`・`mv_common.py` | 運営者が Suno で作った曲の MV（縦長・60fps・曲の音入り）。歌詞のまとまりごとに場面が変わり、1行ごとに図が1つ進む。歌詞は下にカラオケのように出す。曲・歌詞・行ごとの時間（`*_時間.json`）・できた動画は `notes/曲の動画/<曲名>/`、背景の映像は `notes/曲の動画/背景素材/`、背景の動画など作業用のファイルは `notes/曲の動画/作業用/`（どれも公開しない）。時間は音声認識（faster-whisper、サイトの .venv とは別に入れる）と歌詞の突き合わせで作り、合わない行は手で直す。`make_mv_strategy.py`・`make_mv_critical.py`・`make_mv_commit.py` は共通の部品 `mv_common.py` を使う（`make_mv.py` はまだ使っていない）。`--jobs 4` で4つに分けて同時に書き出す（できている部分は飛ばす。同時に2曲を動かすとメモリが足りなくなるので1曲ずつ）、`--youtube` で横長。リール版は `make_reel_cut.py`（小節の区切りで切ってつなぎ、宣伝の画面とフェードアウト）、YouTube のサムネイルと説明文は `make_youtube.py --meta 曲名`。Suno の曲を宣伝に使うときは、商用で使えるプランで作ったか確かめる |
| `upload_youtube.py` | 曲の YouTube 横長版を、YouTube に**非公開**で上げる（タイトル・説明文・チャプター・サムネイル・「改変・合成されたコンテンツ」の申告つき）。公開は運営者が YouTube Studio で押す（2026-10-21 に決めた）。OAuth クライアントは `notes/曲の動画/youtube_client_secret.json`、許可の記録は `notes/曲の動画/youtube_token.json`（どちらも合言葉と同じ扱い。リポジトリに入れない）。上げた動画の ID は `notes/曲の動画/<曲名>/youtube.json`（ショートは `youtube_short.json`）。ショート版は `make_reel_cut.py --shorts` で作って `upload_youtube.py --short` で上げる。Instagram のリールは自動で投稿しない（今のまま、運営者がアプリで投稿） |
| `song_tools/` | 曲の動画づくりの道具: `asr_run.py`・`asr_intro.py`（音声認識。`.venv-asr` で動かす。av==19.0.1 に固定）、`align.py`（歌詞と時間の突き合わせ）、`mixkit_list.py`・`mixkit_get.py`（Mixkit の Free の映像だけをダウンロード）、`cmp_audio.py`（2つの音源を比べる）。手順はスキル `/song-mv`（`.claude/skills/song-mv/SKILL.md`） |
| `make_intro_media.py` | Instagram の最初の投稿（サイト紹介のフィード5枚・リール・ストーリー2枚と投稿文）を `static/ig/intro/` に作る。一度きり |
| `make_app_icons.py` | スマホのホーム画面に置くアプリのアイコン（PWA 用。`static/icon-192.png`・`icon-512.png`・`icon-maskable-512.png`）を作る。アイコンの形を変えたときだけ |
| `make_ip_launch_media.py` | ITパスポート用語ドリルの公開を知らせるリール（約34秒・60fps・音なし）・表紙・投稿文を `static/ig/ip-launch/` に作る。一度きり。用語は `../ip-drill/data/terms.json` から読む |
| `media_fx.py` | 動画の飾りの仕組み。**リール動画は音なし（BGM も効果音もなし）**（2026-10-16 に運営者が決めた。`SFX_ON = False`・`BGM_STYLE = None`。動画には無音の音声トラックだけ入る）。効果音・BGM（`chip` 8ビット・`band` 楽器・`healing` ヒーリング風）・キャラクターのドット絵（`POSES`・`POSES_B`）を作る仕組みは残っているが、今は使っていない |
| `make_news_image.py` | 「今週のITニュース」の画像（見出し・用語の解説）を `static/ig/news/` に作る。ふだんは GitHub の自動実行が動かす。`--cover` で合言葉なしのとき用の表紙 |
| `.github/workflows/news-image.yml` | ボットの合図（repository_dispatch: news-image）で `make_news_image.py` を動かし、画像を commit して公開する |
| `line-bot/` | LINE ボットのプログラム。役割ごとの .gs（`config` 設定・setup / `talk` 話し方 / `report` 毎朝のレポート / `news` / `instagram` / `youtube` 数字とコメント / `inquiry` お問い合わせ / `line` Webhook と送信）と `appsscript.json`。合言葉（トークン）は入れない |
| `line-bot/test/run_test.py` | ボットの動作テスト（モックで動かす。Google や LINE には接続しない） |
| `notes/` | **公開しない**（`.gitignore` 済み）。`pdf/` 手順書の PDF、`src/` その元の HTML、`brand/` アイコン画像 |

## よく使うコマンド

```powershell
python build.py                         # docs/ を作り直す（エラー・注意が出たら直す）
python make_figs.py                     # 用語の動く図を作り直す（そのあと build.py）
python -m http.server 8000 -d docs      # http://localhost:8000 で確認
python make_ig_images.py 120            # 用語クイズのストックを 120 投稿分まで作る
python make_b_media.py 16               # リール動画を 16 本まで作る（先に build.py を実行）
python line-bot/test/run_test.py        # ボットのテスト。最後に ALL OK
python notes/src/make_pdf.py 名前        # notes/src/名前.html から notes/pdf/名前.pdf を作る
.venv\Scripts\python notes/src/make_book.py   # 手順書を表紙・目次つきの1冊（notes/pdf/FE用語ドリル 機能と手順のまとめ.pdf）に。入れる手順書は PARTS で決める（pypdf が必要）
```

- PDF 作り・ボットのテストは Edge の見えないモードを使う。Edge が動かないとき（自動更新の途中など）は、自動で Chrome に切り替わる
- Windows のコンソールは cp932 なので、日本語を出力するスクリプトは `PYTHONIOENCODING=utf-8` を付けて動かす
- Python のパッケージは `requirements.txt`（Pillow・imageio-ffmpeg）。サイト専用の `.venv` に入れて、`.venv\Scripts\python` で動かす。FFmpeg は `imageio-ffmpeg` に入っているもの（環境変数 `FFMPEG` で別のものも指定できる）
- Bash の長いヒアドキュメントは失敗しやすい。長い内容は Write でファイルに書いてから実行する

## アプリとして使う（PWA）

- サイトはスマホのホーム画面に追加して、アプリのように全画面で使える（PWA）。build.py の `build_pwa_files` が `manifest.webmanifest`（名前・アイコン・色 `THEME`）と `sw.js`（サービスワーカー）を作り、全ページで登録する。手順のページは `app.html`（フッターの「アプリとして使う」）
- サービスワーカー: ページはネット優先・取れないときは保存したもの（なければ `offline.html`）、CSS・JS・画像は保存したものをすぐ出して裏で新しくする。`ig/`（動画など）は保存しない。中身が変わると版の名前（ハッシュ）が変わり、古い保存は自動で消える
- iPhone では、Safari とホーム画面のアプリで進み具合（localStorage）が別々になる（`app.html` に書いてある）
- Google Play に出すときは、この PWA を包む（TWA。登録料 25ドル）。App Store は、サイトを包んだだけのアプリは審査で断られやすい

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
- スクリプト プロパティ: `LINE_TOKEN` `WEBHOOK_KEY` `SETUP_CODE` `OWNER_USER_ID` `NEWS_GENRES` `GA_PROPERTY_ID` `IG_TOKEN` `IG_USER_ID` `GITHUB_TOKEN`（ニュースの画像を頼む。fe-drill の Contents 読み書きだけ）`YT_CHANNEL_ID`（setup が自動で入れる）`YT_API_KEY`（YouTube のコメントを読む API キー。YouTube Data API v3 だけに制限）ほか、`IG_`・`YT_` で始まる状態の記録
- トリガー: `onFormSubmit`、`dailyReport`（毎朝8時）、`igWorker`（10分ごと）、`refreshInstagramToken`（毎週）。関数名を変えるとトリガーが切れる
- **サイトの点検**（`report.gs` の `checkSection`・`checkDetailText`）: 入り口の yogo-drill のリポジトリで GitHub の自動実行が毎週月曜 4:00 に全サイトを点検し、結果を `check-results` のブランチの `result.json` に置く（`CONFIG.checkUrl`）。新しい結果が出た朝のレポートに【サイトの点検】の欄（既読は `CHECK_SEEN`）、月曜は結果が取れない・`checkStaleDays` 日より古いときも知らせる。LINE の「点検」でサイトごとの問題・注意。点検の中身は yogo-drill の `check/`
- 毎朝のレポートの閲覧者は【閲覧者：基本情報（FE用語ドリル）】と【閲覧者：ITパスポート】の2つの欄（同じ形）。ITパスポートは姉妹サイトの閲覧者（GA4 のプロパティ ID は `CONFIG.ipGaPropertyId`、空にすると出さない）
- GCP は標準プロジェクト「fe-drill-line」（Search Console API・Analytics Data API・YouTube Data API v3 を有効化）
- YouTube（`youtube.gs`）は **読むだけ**: 毎朝のレポートの【YouTube】の欄（最新の動画の数字・登録者の増減・新しいコメント）と、LINE の「ユーチューブ 反応」「ユーチューブ コメント」。スクリプトの持ち主の権限（`youtube.readonly`、`ScriptApp.getOAuthToken()`）で読む。コメント（commentThreads）は youtube.readonly では 403 になるので API キーで読む（`youtube.force-ssl` は管理の権限まで付くので使わない）。エディタで `testYouTube` を実行すると問い合わせごとの結果が出る。手順は「YouTubeの数字とコメントの設定.pdf」

### Instagram

- **ボットからの自動投稿（API で投稿）は 2026-10-16 から止めている**（`CONFIG.igAutoPost: false`）。下書きには「素材を受け取る」だけを出し、運営者がアプリから投稿して「投稿した」を押す。「投稿」と送っても投稿しない。止める前の予約は投稿せずに取り消す。また使うときは `igAutoPost: true` にする（テストは両方を確かめている）
- Facebook ログイン方式。API は `https://graph.facebook.com/v23.0`、トークンは Facebook ページのトークン（期限なし）。Facebook ページ「Fe用語ドリル」と連携
- 投稿の種類は `IG_KINDS`: 用語クイズ（term）・トレースクイズ（trace）・リール動画（reel）・今週のITニュース（news）。曜日ごとの種類は `CONFIG.rotation`（日〜土: reel, term, term, trace, term, reel, news）
- ストックはサイトに置いた `ig/posts.json`・`ig/trace-posts.json`・`ig/reels.json`。投稿すると次へ進む。**リールは減りが早い**（16本・週2本で約2か月分）
- 毎朝の下書きの「素材を受け取る」（LINE で「素材」でも同じ）で、画像・動画・投稿文・紹介コメントが届く。運営者がアプリで投稿（BGM を付けたいとき）し、「投稿した」を押すとストックが進む
- 投稿の直後に、サイトの紹介コメント（`PIN_COMMENTS`）を自動で付ける。**コメントの固定は API でできないので、運営者がアプリで固定する**
- YouTube ショートは自動投稿しない（未審査のアプリから API で上げた動画は非公開に固定されるため）。リール投稿後にタイトルと説明を LINE に送り、運営者が手で上げる
- 最初のサイト紹介リールは、LINE の「紹介リール」で動画・表紙・投稿文・紹介コメントを受け取り、運営者がアプリで手動投稿する（BGM を Instagram の音楽で付けるため。API では付けられない）。`ig/intro/intro.json` を読む
- 今週のITニュース（土曜、`news.gs`）: ボットが1週間の候補を LINE に出し、運営者が「ニュース投稿 1 4 6」か「おまかせ」で選ぶ → ボットが GitHub の自動実行に画像を頼む → 画像がサイトに出たら igWorker が下書きを送る。状態は `IG_NEWS`、投稿済みは `IG_NEWS_DONE`。`GITHUB_TOKEN` がなければ決まった表紙（`ig/news/cover.jpg`）で作る
- Google ニュースの RSS は「個人で読むため」の条件付き。自動で選んでそのまま Instagram に載せない（運営者が選ぶ形を守る）
- GitHub の自動実行が main に commit するので、運営者は push の前に GitHub Desktop の「Pull origin」が要ることがある

## 決まりごと

- ユーザーへの回答は **日本語**。運営者は初心者寄りなので、手順は画面のボタン名まで具体的に書く
- 手順書・計画などの資料は **PDF** で作る: `notes/src/〇〇.html` を書く → `python notes/src/make_pdf.py 〇〇` → PDF を開いて崩れを確認。PDF のファイル名は日本語のタイトル。機能や運用の手順書を作ったら `make_book.py` の PARTS に足して、まとめの1冊も作り直す。古くなった手順書は `notes/pdf/古い/`・`notes/src/古い/` へ
- 「公式」「IPA」など試験の主催者と関係があるように見える言葉、「必ず合格」「ここだけ」など確かめられない言い切りは、サイト・投稿・資料のどれにも使わない
- ニュースは見出し・媒体名・自分の言葉のひとことまで。記事の本文や画像は載せない
- 広告は「PR」の表示を消さない（ステルスマーケティング規制）
- トークン・合言葉・個人情報はリポジトリに入れない。リポジトリは **公開** なので、`notes/` や画像の置き場所に注意する
- 用語の説明は AI の支援で作ったもの。数値や法律の内容を足すときは特に確かめる
- 動画にキャラクター（アイコンのドット絵）は **入れない**（2026-10-16 に運営者が決めた。ふきだしでセリフを言わせる形も試したが、やめた）。`make_ip_launch_media.py` の `Scene.chara`・`Scene.say`（ふきだしの形 talk/think/shout）・`Scene.walk` は残してあるので、また使うときはそれを呼ぶ

## 未決定・これからの候補

- 独自ドメイン **yogo-drill.com** を Xserverドメインで取得済み（2026年10月、ドメインのみ・自動更新）。サブドメインで fe. / ip. / cloud. / travel. に移す途中。手順は「独自ドメインに移す手順.pdf」
- AdSense（独自ドメインに移したあと）、サブスク
