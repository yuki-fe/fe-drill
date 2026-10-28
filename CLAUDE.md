# CLAUDE.md

このファイルは、このリポジトリで作業する Claude Code 向けのガイドです。人向けの説明は `README.md` にある。

## プロジェクト概要

基本情報技術者試験（FE）の学習サイト **「FE用語ドリル」** と、その運用の仕組み。運営者は Yuki-fe（個人・副業）。

- **サイト**: https://fe.yogo-drill.com/ （独自ドメイン。旧 https://yuki-fe.github.io/fe-drill/ は GitHub Pages が自動で転送。GitHub Pages。リポジトリ `yuki-fe/fe-drill` の `main` ブランチの `/docs`）
  - 科目A: 用語 345語の単語帳（カード・4択・書いて答える・意味から答える、間違えた用語の復習）と、用語ごとの解説ページ
  - 科目B: 擬似言語のプログラムを **1行ずつ再生して変数の変化を見せる** のが売り。トレース練習・穴埋め・アルゴリズム図鑑・セキュリティ事例・記法クイズ・シミュレータ
- **LINE 運用ボット**（`line-bot/`、Google Apps Script）: 運営者だけが使う。毎朝のレポート（公開中の用語サイトごとの様子）、ニュース、お問い合わせ、Instagram の下書きと素材
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
| `data/yomi.json` | 用語の読み（用語 id → ひらがな・半角英数字）。**用語タイピング**（`typing.html`、`static/assets/typing.js`）で打つ文字。用語を足したら読みも足す（ないと build.py が注意を出し、その用語はタイピングに出ない）。英語の略語は英字のまま、かっこの中は打たない |
| `data/imi.json` | 用語の **意味の要点**（用語 id → [画面に出す短い文, 打つ読み]）。タイピングの「意味も打つ」（初めは「する」）で、用語のあとに打つ。10〜20文字ほどで、説明文（desc）の要点だけ。読みの文字の決まりは yomi.json と同じ（「・」などの記号は読みに入れない）。用語を足したらここにも足す（ないと build.py が注意を出し、その用語は意味を飛ばす）。制限時間は 1分・2分・3分（60・120・180秒）から選べ、自己ベストは時間・意味も打つかごとに分かれる（`typing.js` の `TIMES`・`bestKey`） |
| `data/b/*.json` | 科目Bの問題（algorithms / trace / fill / security / notation） |
| `static/` | `docs/` にそのままコピーされる。`assets/`（CSS・JS）、`ig/`（Instagram の画像・動画と投稿文の JSON） |
| `static/assets/pseudo.js` | 擬似言語のインタプリタ。ビューア・答え合わせ・リール動画すべてがこれで動く |
| `docs/` | **生成物。直接編集しない**（ビルドのたびに作り直される）。ただし GitHub Pages が使うので commit はする |
| `checks/` | ビルドで作られる確認ページ（`b-check.html`）。commit しない |
| `make_ig_images.py` | 用語クイズの投稿画像（1080×1350 の2枚組）と投稿文を作る |
| `make_b_media.py` | 科目Bのリール動画（1080×1920、60fps、H.264 CRF 16、音なし）とトレースクイズの画像を作る。上にコード（今の行の帯がすべって動く）、下に **「動きの図」**（`b_visual.py`。`VISUAL = True`）。1行は0.5秒以上。Edge（動かないときは Chrome）と FFmpeg を使う |
| `b_visual.py` | リールの「動きの図」: 配列は箱、番号に使う変数（`[ ]` の中や、それを計算する式の変数）は箱の下の矢印（すべって動く）、代入は値のチップが飛ぶ（「s ← 0 + 3」の式も出す）、if・while で比べる箱はオレンジ、ふつうの変数はカード、再帰は呼び出しの深さ。大域変数は、コードに「大域:」とあるものだけ図に入れる。部品が多いと自動で小さくして収める |
| `make_figs.py` | 用語の **「動く図」**（ステップに分かれた SVG、`static/figs/<用語id>.svg`。利用者が「前へ」「次へ」・図のタップ・左右のスワイプで切り替える。切り替えは `static/assets/fig.js`）と、図のタイトル・手順の文（`data/figs.json`）を作る。用語ページの「図で見る」と、4択・書いて答える問題の答えのあとの「図で見る」に出る。図を足したら `python make_figs.py` → `python build.py`。今は20語（2026-10-20）。「前へ」「次へ」は小さな丸いボタン（‹ ›）と、ステップの点 |
| `make_mv.py`・`make_mv_strategy.py`・`mv_common.py` | 運営者が Suno で作った曲の MV（縦長・60fps・曲の音入り）。歌詞のまとまりごとに場面が変わり、1行ごとに図が1つ進む。歌詞は下にカラオケのように出す。曲・歌詞・行ごとの時間（`*_時間.json`）・できた動画は `notes/曲の動画/<曲名>/`、背景の映像は `notes/曲の動画/背景素材/`、背景の動画など作業用のファイルは `notes/曲の動画/作業用/`（どれも公開しない）。時間は音声認識（faster-whisper、サイトの .venv とは別に入れる）と歌詞の突き合わせで作り、合わない行は手で直す。`make_mv_strategy.py`・`make_mv_critical.py`・`make_mv_commit.py`・`make_mv_recursive.py`（リカーシブルキング）・`make_mv_bitbyte.py`（ビットバイト・ダンス。ドット文字 DotGothic16・0＝シアン／1＝ローズ）・`make_mv_hwrave.py`（ハードウェア・レイヴ。RocknRoll One と Orbitron・アシッドグリーン／マゼンタ／シアン）・`make_mv_duplex.py`（デュプレックス・ハート。Rampart One と Audiowide・主系＝ホットピンク／待機系＝エレクトリックブルー）は共通の部品 `mv_common.py` を使う（`make_mv.py` はまだ使っていない）。曲ごとに色（`mc.BG1` など）と見出しの字体（`mc.HEAD_FONT`、`notes/曲の動画/フォント/` の TTF）を入れかえられる（リカーシブルキングは ui-ux-pro-max で決めたネオン・金色・Dela Gothic One）。`--safe` でリール・ショート用の配置（`_MV_リール用.mp4`。Instagram の表示に文字が隠れない。make_reel_cut.py が優先して使う）、`configure(words=音声認識の JSON)` で言葉ごとのカラオケ、`mc.AUDIO_GAIN_DB` で音量（YouTube の目安 -14 LUFS）。`make_youtube.py --meta` は字幕ファイル（SRT）も作る。`--jobs 4` で4つに分けて同時に書き出す（できている部分は飛ばす。同時に2曲を動かすとメモリが足りなくなるので1曲ずつ）、`--youtube` で横長。リール版は `make_reel_cut.py`（小節の区切りで切ってつなぎ、宣伝の画面とフェードアウト）、YouTube のサムネイルと説明文は `make_youtube.py --meta 曲名`。Suno の曲を宣伝に使うときは、商用で使えるプランで作ったか確かめる |
| `upload_youtube.py` | 曲の YouTube 横長版を、YouTube に**非公開**で上げる（タイトル・説明文・チャプター・サムネイル・「改変・合成されたコンテンツ」の申告つき）。公開は運営者が YouTube Studio で押す（2026-10-21 に決めた）。OAuth クライアントは `notes/曲の動画/youtube_client_secret.json`、許可の記録は `notes/曲の動画/youtube_token.json`（どちらも合言葉と同じ扱い。リポジトリに入れない）。上げた動画の ID は `notes/曲の動画/<曲名>/youtube.json`（ショートは `youtube_short.json`）。ショート版は `make_reel_cut.py --shorts` で作って `upload_youtube.py --short` で上げる。Instagram のリールは自動で投稿しない（今のまま、運営者がアプリで投稿） |
| `song_tools/` | 曲の動画づくりの道具: `asr_run.py`・`asr_intro.py`（音声認識。`.venv-asr` で動かす。av==19.0.1 に固定）、`align.py`（歌詞と時間の突き合わせ）、`mixkit_list.py`・`mixkit_get.py`（Mixkit の Free の映像だけをダウンロード）、`pexels_list.py`・`pexels_get.py`（Pexels の映像を探して `背景素材/p番号.mp4` に保存。API キーは `notes/曲の動画/pexels_api_key.txt`、合言葉と同じ扱い。作った人は `背景素材/pexels_credits.json`）、`cmp_audio.py`（2つの音源を比べる）。手順はスキル `/song-mv`（`.claude/skills/song-mv/SKILL.md`） |
| `research_tools/` | Claude が YouTube・Instagram の動画を見て情報を集める道具: `video_research.py`（yt-dlp で検索・一覧・情報・字幕・コメント、静止画の一覧。`.venv` で動かす）、`transcribe.py`（字幕がないときの文字起こし。`.venv-asr`）。できたものは `notes/動画の調査/`。手順はスキル `/video-research` |
| `make_intro_media.py` | Instagram の最初の投稿（サイト紹介のフィード5枚・リール・ストーリー2枚と投稿文）を `static/ig/intro/` に作る。一度きり |
| `make_og_images.py` | LINE・SNS に URL を貼ったときの画像（og:image、1200×630）を、FE・ITパスポート・入り口（yogo-drill）の `static/og.png` に作る（2026-10-26）。語数は `../yogo-drill/sites.json` から読むので、語数やサイトが変わったら作り直して各サイトで build.py |
| `make_app_icons.py` | スマホのホーム画面に置くアプリのアイコン（PWA 用。`static/icon-192.png`・`icon-512.png`・`icon-maskable-512.png`）を作る。アイコンの形を変えたときだけ |
| `make_ip_launch_media.py` | ITパスポート用語ドリルの公開を知らせるリール（約34秒・60fps・音なし）・表紙・投稿文を `static/ig/ip-launch/` に作る。一度きり。用語は `../ip-drill/data/terms.json` から読む |
| `make_series_promo.py`・`make_promo_shots.py` | **用語ドリル全体**（yogo-drill.com と公開中の7サイト）の宣伝リール（約36秒・60fps・音なし）・表紙・投稿文を `static/ig/series-promo/` に作る。デザインはサイトのレイアウトと同じ「ミニマル・スイス」（ui-ux-pro-max）、文字は Noto Sans JP、上のふちに7サイトの色の帯。サイトの一覧は `../yogo-drill/sites.json`（`public` のもの。旅行は入らない）。先に `..\yogo-drill\.venv\Scripts\python make_promo_shots.py` で各サイトのスマホの画面を `notes/宣伝動画/画面/` に撮る（playwright が要る）。`--stills` で場面ごとの静止画、`--captions` で投稿文だけ作り直す。FE だけの宣伝リール（クレイ風・紫）は `make_promo_media.py`（`static/ig/promo/`） |
| `media_fx.py` | 動画の飾りの仕組み。**リール動画は音なし（BGM も効果音もなし）**（2026-10-16 に運営者が決めた。`SFX_ON = False`・`BGM_STYLE = None`。動画には無音の音声トラックだけ入る）。効果音・BGM（`chip` 8ビット・`band` 楽器・`healing` ヒーリング風）・キャラクターのドット絵（`POSES`・`POSES_B`）を作る仕組みは残っているが、今は使っていない |
| `line-bot/` | LINE ボットのプログラム。役割ごとの .gs（`config` 設定・setup / `talk` 話し方 / `report` 毎朝のレポート / `news` / `instagram` / `youtube` 数字とコメント / `inquiry` お問い合わせ / `line` Webhook と送信）と `appsscript.json`。合言葉（トークン）は入れない |
| `ranking/` | 用語タイピングの **ランキング**（2026-10-27）。`ranking.gs` は LINE ボットとは別の GAS（スプレッドシート「タイピングランキング」に付ける。ウェブアプリ・全員）。ランキングは「練習・意味も打つ・2分・分野すべて」（`practice-120-imi`）の1つだけで、**全用語サイト共通**（2026-10-27・28 に運営者が決めた。公開中の7サイトすべてで送れる。`RANK.sites` にサイトの名前）。順位は **点数 = 文字数 × 正確さ³ × 10**（`typing.js` の `points` と `ranking.gs` の `points` は同じ式。点数は GAS 側で計算する）、結果のランク S〜D は1分あたりの点数（`GRADES`）。自己ベストも点数（`typing-pt-`）。`doGet` で上位20人（今週＝月曜0時 JST 区切り・全期間）、`doPost` で文字数・打鍵・ミスを受ける（ありえない値・NG語の名前ははじく。シート「記録」の「非表示」列で運営者が消せる）。サイトは `config.json` の `typing_rank_url`（空ならランキングを出さない）と `site_key`（`typing.js` の `BOARD`）。テストは `python ranking/test/run_test.py`（最後に ALL OK）。手順は「タイピングランキングの設定.pdf」。サイトを足すときは `RANK.sites` に足して GAS を新バージョンでデプロイし、そのサイトの config.json に `site_key`・`typing_rank_url` を入れる |
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
- スクリプト プロパティ: `LINE_TOKEN` `WEBHOOK_KEY` `SETUP_CODE` `OWNER_USER_ID` `NEWS_GENRES` `GA_PROPERTY_ID` `IG_TOKEN` `IG_USER_ID` `YT_CHANNEL_ID`（setup が自動で入れる）`YT_API_KEY`（YouTube のコメントを読む API キー。YouTube Data API v3 だけに制限）ほか、`IG_`・`YT_` で始まる状態の記録
- トリガー: `onFormSubmit`、`dailyReport`（毎朝8時）、`refreshInstagramToken`（毎週）。関数名を変えるとトリガーが切れる（`igWorker` は 2026-10-25 になくした。残っていたら setup をもう一度実行して消す）
- **サイトの点検**（`report.gs` の `checkSection`・`checkDetailText`）: 入り口の yogo-drill のリポジトリで GitHub の自動実行が毎週月曜 4:00 に全サイトを点検し、結果を `check-results` のブランチの `result.json` に置く（`CONFIG.checkUrl`）。新しい結果が出た朝のレポートに【サイトの点検】の欄（既読は `CHECK_SEEN`）、月曜は結果が取れない・`checkStaleDays` 日より古いときも知らせる。LINE の「点検」でサイトごとの問題・注意。点検の中身は yogo-drill の `check/`
- 毎朝のレポートは、**公開中の用語サイトごとの欄**（`config.gs` の `SITES`。閲覧者・検索・開けるか・最後の更新）→【インスタ】【YouTube】【サイトの点検】【お問い合わせ】。サイトを公開したら `SITES` に足す。`ga` は GA4 のプロパティ ID（2026-10-25 に全サイトに付けた。空なら「アナリティクスはまだ」。FE は `main: true` でスクリプト プロパティの `GA_PROPERTY_ID`）、`search: true` は Search Console に URL プレフィックスで登録したサイト（今は FE・ITパスポートだけ）
- LINE の「グラフ」はサイトを選ぶボタン（アナリティクスのあるサイトだけ）、「グラフ 簿記」でそのサイトのグラフ（線はサイトの色 `color`）。月曜の朝は FE のグラフ。「人気」は FE だけ
- LINE のことばは「グラフ」「人気」「問い合わせ」「済 3」「コメント」「紹介コメント」「反応」「ユーチューブ（反応・コメント）」「リンク」「点検」「使い方」。「状況」「インスタ」「素材」「投稿」「紹介リール」「ニュース」「ジャンル」「ニュース投稿」は 2026-10-25 になくした（運営者が決めた）
- GCP は標準プロジェクト「fe-drill-line」（Search Console API・Analytics Data API・YouTube Data API v3 を有効化）
- YouTube（`youtube.gs`）は **読むだけ**: 毎朝のレポートの【YouTube】の欄（最新の動画の数字・登録者の増減・新しいコメント）と、LINE の「ユーチューブ 反応」「ユーチューブ コメント」。スクリプトの持ち主の権限（`youtube.readonly`、`ScriptApp.getOAuthToken()`）で読む。コメント（commentThreads）は youtube.readonly では 403 になるので API キーで読む（`youtube.force-ssl` は管理の権限まで付くので使わない）。エディタで `testYouTube` を実行すると問い合わせごとの結果が出る。手順は「YouTubeの数字とコメントの設定.pdf」

### Instagram

- **ボットは Instagram に投稿しない**（2026-10-16 に止め、2026-10-25 に自動投稿・予約のコードを消した）。下書きのボタンは「素材を受け取る」「別のにする」「種類を変える」「今日はやめる」。運営者がアプリから投稿して「投稿した」を押す。また自動で投稿したくなったら、git の履歴（2026-10-25 より前の `instagram.gs` の `igPublish`・`igWorker`）から戻す
- Facebook ログイン方式。API は `https://graph.facebook.com/v23.0`、トークンは Facebook ページのトークン（期限なし）。Facebook ページ「Fe用語ドリル」と連携
- 投稿の種類は `IG_KINDS`: 用語クイズ（term）・トレースクイズ（trace）・リール動画（reel）。曜日ごとの種類は `CONFIG.rotation`（日〜土: reel, term, term, trace, term, reel, term）
- ストックはサイトに置いた `ig/posts.json`・`ig/trace-posts.json`・`ig/reels.json`。投稿すると次へ進む。**リールは減りが早い**（16本・週2本で約2か月分）
- 毎朝の下書きの「素材を受け取る」で、画像・動画・投稿文・紹介コメントが届く。運営者がアプリで投稿（BGM を付けたいとき）し、「投稿した」を押すとストックが進む
- サイトの紹介コメント（`PIN_COMMENTS`）は素材の最後の吹き出しで届く。LINE の「紹介コメント」で、いちばん新しい投稿に API で付けることもできる。**コメントの固定は API でできないので、運営者がアプリで固定する**
- YouTube ショートは自動投稿しない（未審査のアプリから API で上げた動画は非公開に固定されるため）。リールで「投稿した」を押すとタイトルと説明を LINE に送り、運営者が手で上げる
- 土曜の「今週のITニュース」の投稿は 2026-10-25 にやめた（ボットのコード・`make_news_image.py`・GitHub の自動実行を消した）。ニュースは毎朝のレポートで読むだけ（ジャンルはスクリプト プロパティ `NEWS_GENRES`）
- Google ニュースの RSS は「個人で読むため」の条件付き。自動で選んでそのまま Instagram に載せない

## 決まりごと

- **レイアウト**（2026-10-23 に入れた）: 見た目の土台は `static/assets/style.css`、その上に全サイト共通の `static/assets/layout.css`（FE用語ドリルのものと同じファイル。直すときは FE で直して、各サイトにコピーする）。トップは「見出し・説明・数字・あなたの進み具合」→「学習する」（学び方はタブ）→「できること」のカード→説明。用語ページは本文と右の「この用語を練習する」「同じ分野の用語」の2列（スマホは1列）。学習の画面（app.js）が使う `#modes`・`#fields`・`#toolbar`・`#panel`・`#reset` は消さない
- **用語タイピング**は、公開中の全サイト（ip・cloud・genai・dl・boki・iryo）にも 2026-10-25 に入れた。`static/assets/typing.js` と style.css の「用語タイピング」の部分は全サイト共通なので、FE で直して各サイトにコピーする。各サイトの読みと意味は、それぞれの `data/yomi.json`・`data/imi.json`。始める前に 3・2・1 のカウントダウン、Esc（スマホは「やめる」）ですぐメニューへ（記録は残さない）、腕だめしのパスは Tab・ヒントは Enter。日本語入力（全角）のままでも打てる（key が "Process" のときは `e.code` から半角の文字にし、日本語入力が作った文字は捨てる。2026-10-28）
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
