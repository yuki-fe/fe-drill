---
name: video-research
description: YouTube・Instagram の動画を Claude が見て情報を集める（字幕・文字起こし・静止画の一覧・再生回数・コメント）。「この動画を見て」「YouTube で〇〇を調べて」「伸びている動画を調べて」「このリールの中身をまとめて」と頼まれたときに使う
---

# 動画を見て情報を集める

Claude は動画をそのまま再生できない。`research_tools/video_research.py` で動画を **文字（字幕か文字起こし）** と **数秒ごとの静止画を 3×3 に並べた一覧の画像** にして、それを読む。

## 使い方（リポジトリの一番上で動かす）

```powershell
# キーワードで YouTube を検索（再生回数つきの一覧）。--new で新しい順
.venv\Scripts\python research_tools/video_research.py --search "基本情報 勉強" -n 15
# チャンネル・再生リストの動画の一覧
.venv\Scripts\python research_tools/video_research.py --list https://www.youtube.com/@チャンネル/videos -n 30
# 1本を調べる（YouTube・Instagram の公開リールの URL）
.venv\Scripts\python research_tools/video_research.py URL
# 手元の動画ファイル（運営者がスマホで保存したリールなど）
.venv\Scripts\python research_tools/video_research.py "C:\…\reel.mp4"
```

- できたものは `notes/動画の調査/<日付>_<id>/`（公開しない）: `info.md`（タイトル・再生回数・説明文・コメント）、`transcript.txt`（`[mm:ss] 文`）、`sheet_01.jpg`…（静止画の一覧、最大4枚）。一覧は `notes/動画の調査/<日付>_YouTube_検索「…」.md`
- 字幕（日本語）があれば字幕、なければ音声を `.venv-asr` の faster-whisper で文字起こし（長い動画は時間がかかる。`--model small` で速く、`--no-asr` で飛ばす）
- 映像がいらないときは `--no-frames`（動画を取らない）。コメントの数は `--comments 20`（0 で取らない）
- 長い動画は静止画の間隔が自動で広がる（全体で36枚まで）。細かく見たい場面は ffmpeg で切り出して読む
- 動画・音声のファイルは使ったあと自動で消える

## 調べたあと

1. `info.md` と `transcript.txt` を Read、静止画の一覧を Read（画像として見る）
2. 運営者には日本語で、要点・使えそうなネタ・数字（再生回数など）をまとめて答える。何本も調べたときは比べる表に
3. 残す価値があるまとめは `notes/動画の調査/` に md で書く

## 注意

- **Instagram はログインなしで取れる公開の投稿だけ**。取れないときは、運営者に保存した動画ファイルを渡してもらう。ブラウザのログイン情報（cookies）を使って取らない（アカウントが止められるおそれ）
- YouTube の 429（取りすぎ）が出たら、少し時間をおく。何十本も続けて取らない
- 集めたものは **調べるため・参考にするためだけ**。他人の動画の文字起こし・画像・言い回しを、サイト・投稿・動画にそのまま使わない（ニュースと同じく、自分の言葉で）
- yt-dlp はサイトの `.venv` に入っている。YouTube の変更で動かなくなったら `.venv\Scripts\python -m pip install -U yt-dlp`
