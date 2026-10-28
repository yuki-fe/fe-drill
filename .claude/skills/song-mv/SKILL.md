---
name: song-mv
description: 運営者が Suno で作った新しい曲から、Lemo-Opuscar の画風（曲ごとに選ぶ）で歌詞に合わせて IT 用語を図で解説する MV（縦長）・3分以内のリール版・YouTube 横長版・サムネイル・説明文を作り、YouTube に非公開で上げる。曲（mp3）と歌詞が届いたとき、または「曲の動画を作って」と頼まれたときに使う
---

# 曲の動画づくり（/song-mv）

運営者が Suno で作った曲（2026-10-20 以降の曲は、すべて Pro プランで商用利用できる）から、次を作る。
回答は日本語で、運営者は初心者なので、画面のボタン名まで具体的に書く。

## できあがるもの（`notes/曲の動画/<曲名>/`、公開しないフォルダ）
- `<曲名>_MV.mp4` 縦長 1080×1920・24fps・曲の音入り（Lemo-Opuscar の画風で、コードで描く）
- `<曲名>_リール.mp4` 3分以内・宣伝の画面つき・最後はフェードアウト（Instagram 用。投稿は運営者がアプリで。自動投稿はしない）
- `<曲名>_YouTube.mp4` 横長 1920×1080
- `<曲名>_YouTube_サムネイル.jpg`・`<曲名>_YouTube_説明文.txt`
- `<曲名>_ショート.mp4` YouTube ショート用（リール版の「プロフィールのリンクから」を「チャンネルのリンクから」にしたもの）
- YouTube に**非公開**で上げる（`upload_youtube.py`）。横長のフルバージョンとショートの両方。公開は運営者が YouTube Studio で押す

## 手順
1. **曲と歌詞を受け取る**: 曲は `notes/動画のサンプル/` か `~/Downloads` にあることが多い。`notes/曲の動画/<曲名>/<曲名>.mp3` に置く。同じ中身のファイルでないか md5 で確かめる（音の比べ方は `song_tools/cmp_audio.py`）（前に、ちがう曲名で同じ音が届いたことがある）。歌詞は `<曲名>_歌詞.txt` に、`[見出し]` でまとまりを分けて保存し、`(Piano …)` のような演奏の説明の行は外す
2. **長さと音量を測る**（ファイルの大きさから推測しない。ffmpeg の Duration を見る）。音量は `-af ebur128=peak=true` で測り、YouTube の目安 -14 LUFS との差を `mc.AUDIO_GAIN_DB` に入れる（いちばん大きい音が -1 dB を超えないように）
3. **音声認識**: 結果の JSON は、`mc.configure(..., words=結果.json)` に渡すと、カラオケの色が言葉ごとに進む（行を一定の速さで塗るより、歌とずれない）。曲を 16kHz・モノラルの raw（s16le）に変えてから、`.venv-asr\Scripts\python -I -X utf8 song_tools/asr_run.py 曲.raw 結果.json 歌詞.txt` で言葉ごとの時間を取る（faster-whisper・large-v3-turbo。`.venv-asr` は av==19.0.1 に固定。新しい版の av は Windows のアプリ制御に止められる）。最初の語りなどが取れないときは `song_tools/asr_intro.py`
4. **歌詞と時間の突き合わせ**: `song_tools/align.py` で自動で合わせる。**サビがくり返す曲は自動だとまざる**ので、認識の区切り（segments）を見て1行ずつ手で割り当てる。取れなかった行は、前後の区切りから推測し、運営者に伝える。`<曲名>_時間.json` に保存
5. **絵は Lemo-Opuscar で作る**（2026-10-28 に運営者が決めた。見本は `notes/曲の動画/ビットバイト・ダンス/ビットバイト・ダンス_CRT_30秒.mp4`、そのソースは `notes/曲の動画/作業用/bitbyte-crt/`）
   - ライブラリは `~/lemo-opuscar`（github.com/lemomo-ai/lemo-opuscar、MIT。部品は入れてある）。先に `git -C ~/lemo-opuscar pull` で新しくする。付属の `setup.sh` は Windows ではそのまま動かない（`.venv/bin` 前提）。部品を入れ直すときは、`~/lemo-opuscar` で `npm install`・`node node_modules/playwright-core/cli.js install chromium-headless-shell`・`.venv/Scripts/python -m pip install -r requirements.txt` を実行する（パッケージを入れる操作は、運営者に許可をもらう）
   - ライブラリの `AGENTS.md`・`DIRECTOR.md`・`TECHNIQUE.md`・`core/README.md` を読み、その手順に従う（Python は `.venv/Scripts/python`）
   - **画風は曲ごとに選ぶ**: 曲の雰囲気に合う画風を `styles/README.md` の59種類から2〜3出し、ギャラリー https://lemomo-ai.github.io/lemo-opuscar/ を添えて運営者に聞く。選んだ `styles/<画風>/STYLE.md` の決まりは全部守る
   - 作業フォルダは `~/lemo-opuscar/films/<英数字の名前>/`（日本語のパスは避ける）。`TREATMENT.md` を**先に**書き、デモ（`styles/<画風>/demo/`）はそのあとで技法だけ読む。デモの話・場面はまねしない
   - **曲が音楽の主役**: 作曲・ナレーションはしない。曲（ffmpeg で切り出した wav）に、画面の動きに合わせた効果音を小さく足すだけ（`mix.py`）。テンポは曲から測る（拍の位置も）。場面の切り替え・大事な動きは、小節の頭と歌の言葉の時間に合わせる
   - **歌詞は画風の字幕の形で出す**（例: ASCII/CRT は下の LOG 欄に言葉ごとに打つ）。時間は手順3の音声認識の言葉の時間から。日本語の字体は `notes/曲の動画/フォント/` の OFL のもの（作業フォルダの `fonts/` にコピー）
   - 図は用語の意味が正しく伝わるように（数字や式は確かめる）。キャラクターは入れない
   - 縦長は Instagram・ショートの表示に文字が隠れない配置で作る（上 約270px・下 約350px・右のボタンの列をよける）。最初の3秒で目を引く
   - ページは `innerWidth`×`innerHeight` から配置を決め、縦長（1080×1920）と横長（1920×1080）の両方を同じソースから出せるようにする
6. **静止画で確かめる**: `node core/render/still.mjs <作業フォルダ> 秒 秒 … --size 1080x1920` → `core/render/sheet.py` で一覧にして見る。文字の重なり・はみ出し・暗すぎる場面を直す
7. **書き出し**（作業フォルダの `build.sh` にまとめる。見本の `build.sh` を参考に。1曲ずつ順番に）
   - 縦長: `video.mjs --fps 24 --size 1080x1920` → `mux.sh`（−14 LUFS）→ `notes/曲の動画/<曲名>/<曲名>_MV.mp4`。リール用の配置で作っているので、同じものを `<曲名>_MV_リール用.mp4` としても置く
   - 横長: `--size 1920x1080` で書き出して `<曲名>_YouTube.mp4`
   - 30秒で約5分かかる（4分の曲なら40分ほど）。長い作業は裏で動かし、終わったら知らせる。書き出し中は、パソコンをスリープさせない（運営者に伝える）
8. **リール版・サムネイル・説明文**（今までの道具をそのまま使う）
   - リール版: `make_reel_cut.py` の `CUTS` に、**小節の区切り**で切る場所を足して `python make_reel_cut.py <曲名>`。3分以内
   - サムネイル・説明文・字幕: `make_youtube.py` の `SONGS` と `THUMBS` を足して `python make_youtube.py --meta <曲名>`。字幕ファイル `<曲名>_字幕.srt` と `<曲名>_ショート_字幕.srt` もできる（運営者が YouTube Studio の「字幕」から上げる）。チャプターは1つ10秒以上
   - 作業フォルダの `CREDITS`（曲・字体・ライブラリのライセンス）を `notes/曲の動画/<曲名>/` にもコピーする
   - 古いやり方（`make_mv_<曲>.py`・`mv_common.py` の Pillow の MV、Mixkit・Pexels の背景の映像）は、運営者が頼んだときだけ使う
9. **できたものを確かめる**: 長さ・画面の大きさ・音、つなぎ目、いくつかの場面の画像を見る
10. **YouTube に非公開で上げる**: `python upload_youtube.py <曲名>`（タイトル・説明文・チャプター・サムネイル・「改変・合成されたコンテンツ」の申告つき）。続けてショート版を `python make_reel_cut.py --shorts <曲名>` で作り、`python upload_youtube.py --short <曲名>` で上げる（説明文にフルバージョンの URL が入る。ショートのサムネイルは API で設定できない）。許可が切れていたら、ブラウザで許可が要る（OAuth の同意画面は「FE用語ドリル LINE」の名前で出る）。運営者が自分で上げた曲は二重に上げない（先に運営者に確かめる）
11. **運営者に伝える**: できたもの・確かめたこと・推測した行・YouTube の URL と「YouTube Studio で公開を押す」手順、ショートの「関連動画」にフルバージョンをつなぐ手順。必要ならリールの投稿文も作る

## 決まりごと
- 「公式」「IPA」「必ず合格」「ここだけ」などの言葉は使わない。投稿文・説明文にも
- 投稿文・説明文には、サイト（fe.yogo-drill.com・ip.yogo-drill.com）への案内を入れる
- 作業用のファイル（背景の動画など）は `notes/曲の動画/作業用/`。大きいので、完成したら消してよいか運営者に聞く
- 2026-10-20 より前の曲（データ構造の心など）は、商用で使えるか運営者に確かめる
