"""曲の YouTube 横長版を、YouTube に「非公開」で上げる（タイトル・説明文・チャプター・サムネイルつき）。

公開は、運営者が YouTube Studio で内容を確かめてから「公開」を押す。
（Google の審査を受けていないアプリから上げた動画は、非公開に固定されるため。自動で公開はしない）

    python upload_youtube.py コミットしないで     # 1曲を上げる
    python upload_youtube.py --check              # ログインと、上げた記録だけ確かめる
    python upload_youtube.py --short コミットしないで   # 縦長のショート版（make_reel_cut.py --shorts で作る）を上げる
    python upload_youtube.py --lesson 二分探索    # 科目Bの解説動画（notes/科目B解説動画/二分探索/）の本編と宣伝のショート
    python upload_youtube.py --ip ネットワーク②_IPアドレス・DNS   # ITパスポートの解説動画（notes/ITパスポート解説動画/<名前>/）。再生リストにも足す
    python upload_youtube.py --playlist           # 科目Bの解説動画の再生リストを作る・まだ入っていない回を足す（LESSON_ORDER の順）
    python upload_youtube.py --whatif もしも基本情報に合格したら   # もしも動画（notes/もしも動画/<名前>/）をショートで上げる

使うファイル（どれも notes/ の中で、公開しない）
- notes/曲の動画/youtube_client_secret.json   Google Cloud で作った OAuth クライアント（デスクトップ アプリ）
- notes/曲の動画/youtube_token.json           初回にブラウザで許可すると作られる。合言葉と同じ扱い
- notes/曲の動画/youtube_token_manage.json    再生リスト用の許可（YouTube アカウントの管理）。合言葉と同じ扱い
- notes/曲の動画/<曲名>/<曲名>_YouTube.mp4・_YouTube_説明文.txt・_YouTube_サムネイル.jpg
- notes/曲の動画/<曲名>/youtube.json          上げた動画の ID の記録（同じ曲を二重に上げない）
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).parent
SONGS_DIR = ROOT / "notes" / "曲の動画"
CLIENT = SONGS_DIR / "youtube_client_secret.json"
TOKEN = SONGS_DIR / "youtube_token.json"
SCOPES = ["https://www.googleapis.com/auth/youtube.upload", "https://www.googleapis.com/auth/youtube.readonly"]
CATEGORY = "27"   # 教育
TAGS = ["ITパスポート", "基本情報技術者試験", "勉強ソング", "資格勉強", "IT用語"]
# AI で作った歌声なので、YouTube の「改変・合成されたコンテンツ」の申告をする
SYNTHETIC = True


def service(token=TOKEN, scopes=SCOPES):
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    creds = None
    if token.exists():
        creds = Credentials.from_authorized_user_file(str(token), scopes)
    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
        except Exception:
            creds = None   # 許可の期限切れ（テスト中のアプリは7日ほど）→ もう一度ブラウザで許可
    if not creds or not creds.valid:
        if not CLIENT.exists():
            sys.exit(f"OAuth クライアントのファイルがありません: {CLIENT}")
        flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT), scopes)
        print("ブラウザが開きます。YouTube の許可をしてください。", flush=True)
        creds = flow.run_local_server(port=0, prompt="consent")
        token.write_text(creds.to_json(), encoding="utf-8")
    return build("youtube", "v3", credentials=creds)


def read_description(path):
    """説明文のファイル: 1行目がタイトル、そのあとが説明文。"""
    lines = path.read_text(encoding="utf-8").splitlines()
    title = lines[0].strip()
    body = "\n".join(lines[1:]).strip()
    return title[:100], body[:5000]


def upload(yt, name):
    from googleapiclient.http import MediaFileUpload
    d = SONGS_DIR / name
    video = d / f"{name}_YouTube.mp4"
    thumb = d / f"{name}_YouTube_サムネイル.jpg"
    desc = d / f"{name}_YouTube_説明文.txt"
    record = d / "youtube.json"
    for p in (video, thumb, desc):
        if not p.exists():
            sys.exit(f"ファイルがありません: {p}")
    if record.exists():
        r = json.loads(record.read_text(encoding="utf-8"))
        sys.exit(f"もう上げてあります: https://youtu.be/{r['id']}（上げ直すときは {record.name} を消してから）")
    title, body = read_description(desc)
    meta = {
        "snippet": {"title": title, "description": body, "tags": TAGS, "categoryId": CATEGORY,
                    "defaultLanguage": "ja", "defaultAudioLanguage": "ja"},
        "status": {"privacyStatus": "private", "selfDeclaredMadeForKids": False, "containsSyntheticMedia": SYNTHETIC},
    }
    media = MediaFileUpload(str(video), mimetype="video/mp4", chunksize=8 * 1024 * 1024, resumable=True)
    req = yt.videos().insert(part="snippet,status", body=meta, media_body=media)
    print(f"上げています: {video.name}", flush=True)
    res = None
    while res is None:
        status, res = req.next_chunk()
        if status:
            print(f"  {int(status.progress() * 100)}%", flush=True)
    vid = res["id"]
    record.write_text(json.dumps({"id": vid, "title": title, "privacy": "private"}, ensure_ascii=False, indent=1), encoding="utf-8")
    try:
        yt.thumbnails().set(videoId=vid, media_body=MediaFileUpload(str(thumb), mimetype="image/jpeg")).execute()
        print("サムネイルを設定しました", flush=True)
    except Exception as e:
        # サムネイルの設定は、チャンネルの電話番号の確認がすんでいないとできない
        print(f"サムネイルを設定できませんでした（YouTube Studio で設定してください）: {e}", flush=True)
    print(f"非公開で上げました: https://youtu.be/{vid}")
    print("YouTube Studio で内容を確かめて、「公開」にしてください。")


# フルバージョンの URL を説明文に入れない曲（運営者が自分で上げていて、URL がわからないもの）
NO_FULL_URL = {"クリティカルパス"}


def upload_short(yt, name):
    """縦長のショート版（<曲名>_ショート.mp4、3分以内）を非公開で上げる。サムネイルはショートでは設定できない。"""
    from googleapiclient.http import MediaFileUpload
    import make_youtube
    d = SONGS_DIR / name
    video = d / f"{name}_ショート.mp4"
    record = d / "youtube_short.json"
    if not video.exists():
        sys.exit(f"ファイルがありません: {video}")
    if record.exists():
        r = json.loads(record.read_text(encoding="utf-8"))
        sys.exit(f"もう上げてあります: https://youtu.be/{r['id']}（上げ直すときは {record.name} を消してから）")
    info = make_youtube.SONGS[name]
    lead = "".join(info["lead"])
    title = f"{name}｜{lead} #Shorts"[:100]
    full = d / "youtube.json"
    if full.exists() and name not in NO_FULL_URL:
        full_line = f"▼ フルバージョン\nhttps://youtu.be/{json.loads(full.read_text(encoding='utf-8'))['id']}"
    else:
        full_line = "▼ フルバージョンは、チャンネルの動画から"
    sites = "\n".join(f"・{n}：{u}" for n, u, _ in make_youtube.SITES)
    body = (f"{info['desc']}\n歌詞に合わせて、用語の意味を図で解説しています。\n\n{full_line}\n\n"
            f"▼ 用語の復習は、無料の単語帳サイトで（登録なし・スマホで使えます）\n{sites}\n\n"
            f"曲：Suno で作成\n映像素材：Mixkit\n\n#Shorts {info['tags']}")
    meta = {
        "snippet": {"title": title, "description": body[:5000], "tags": TAGS, "categoryId": CATEGORY,
                    "defaultLanguage": "ja", "defaultAudioLanguage": "ja"},
        "status": {"privacyStatus": "private", "selfDeclaredMadeForKids": False, "containsSyntheticMedia": SYNTHETIC},
    }
    media = MediaFileUpload(str(video), mimetype="video/mp4", chunksize=8 * 1024 * 1024, resumable=True)
    req = yt.videos().insert(part="snippet,status", body=meta, media_body=media)
    print(f"上げています: {video.name}", flush=True)
    res = None
    while res is None:
        _, res = req.next_chunk()
    vid = res["id"]
    record.write_text(json.dumps({"id": vid, "title": title, "privacy": "private"}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"非公開で上げました（ショート）: https://youtu.be/{vid}")


# ───────── 科目Bの解説動画（notes/科目B解説動画/<名前>/）
LESSON_DIR = ROOT / "notes" / "科目B解説動画"
LESSON_TAGS = ["基本情報技術者試験", "科目B", "アルゴリズム", "擬似言語", "資格勉強"]


def upload_lesson(yt, name, root=LESSON_DIR, tags=LESSON_TAGS):
    """本編（<名前>_本編_YouTube.mp4）を非公開で上げる。宣伝のショート（<名前>_宣伝_リール・ショート.mp4）があれば、それも上げる（今は作らない）。
    タイトルは YouTubeのタイトル.txt、説明文は YouTubeの説明文.txt。ショートの説明文には本編の URL を入れる。
    上げた記録は youtube.json・youtube_short.json（同じものを二重に上げない）。"""
    from googleapiclient.http import MediaFileUpload
    d = root / name
    video, short = d / f"{name}_本編_YouTube.mp4", d / f"{name}_宣伝_リール・ショート.mp4"
    thumb, tfile, dfile = d / f"{name}_サムネイル.jpg", d / "YouTubeのタイトル.txt", d / "YouTubeの説明文.txt"
    for p in (video, thumb, tfile, dfile):
        if not p.exists():
            sys.exit(f"ファイルがありません: {p}")
    title = tfile.read_text(encoding="utf-8").strip()[:100]
    body = dfile.read_text(encoding="utf-8").strip()[:5000]

    def send(path, meta):
        media = MediaFileUpload(str(path), mimetype="video/mp4", chunksize=8 * 1024 * 1024, resumable=True)
        req = yt.videos().insert(part="snippet,status", body=meta, media_body=media)
        print(f"上げています: {path.name}", flush=True)
        res = None
        while res is None:
            status, res = req.next_chunk()
            if status:
                print(f"  {int(status.progress() * 100)}%", flush=True)
        return res["id"]

    def meta(t, b):
        return {"snippet": {"title": t, "description": b, "tags": tags, "categoryId": CATEGORY,
                            "defaultLanguage": "ja", "defaultAudioLanguage": "ja"},
                # ナレーションが合成音声なので、「改変・合成されたコンテンツ」の申告をする
                "status": {"privacyStatus": "private", "selfDeclaredMadeForKids": False, "containsSyntheticMedia": True}}

    rec = d / "youtube.json"
    if rec.exists():
        vid = json.loads(rec.read_text(encoding="utf-8"))["id"]
        print(f"本編はもう上げてあります: https://youtu.be/{vid}")
    else:
        vid = send(video, meta(title, body))
        rec.write_text(json.dumps({"id": vid, "title": title, "privacy": "private"}, ensure_ascii=False, indent=1), encoding="utf-8")
        try:
            yt.thumbnails().set(videoId=vid, media_body=MediaFileUpload(str(thumb), mimetype="image/jpeg")).execute()
            print("サムネイルを設定しました", flush=True)
        except Exception as e:
            print(f"サムネイルを設定できませんでした（YouTube Studio で設定してください）: {e}", flush=True)
        print(f"非公開で上げました（本編）: https://youtu.be/{vid}")

    # 2026-10-30 からショート（縦長の宣伝）は作らない。ファイルがない回は本編だけ上げて終わる
    if not short.exists():
        return
    srec = d / "youtube_short.json"
    if srec.exists():
        print(f"ショートはもう上げてあります: https://youtu.be/{json.loads(srec.read_text(encoding='utf-8'))['id']}")
        return
    # ショートの題名は回ごとに YouTubeのショートのタイトル.txt に書く（ないときは止める。題名を使い回さないため）
    sfile = d / "YouTubeのショートのタイトル.txt"
    if not sfile.exists():
        sys.exit(f"ショートの題名のファイルがありません: {sfile}")
    stitle = sfile.read_text(encoding="utf-8").strip()[:100]
    sbody = (f"基本情報技術者試験の科目B「{name.replace('_', ' ')}」を、ホワイトボードで1行ずつ。\n"
             f"本番と同じ形の穴埋め問題の答えと解説は、本編で。\n\n▼ 本編\nhttps://youtu.be/{vid}\n\n"
             f"▼ 練習はこちら（FE用語ドリル 科目B）\nhttps://fe.yogo-drill.com/\n\n"
             f"※ ナレーションは合成音声です。\n#Shorts #基本情報技術者試験 #科目B #擬似言語")
    sid = send(short, meta(stitle, sbody))
    srec.write_text(json.dumps({"id": sid, "title": stitle, "privacy": "private"}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"非公開で上げました（ショート）: https://youtu.be/{sid}")


# ───────── 科目Bの解説動画の再生リスト（2026-11-04）
# 再生リストを作る・足すには「YouTube アカウントの管理」の許可が要る。上げる許可（TOKEN）とは別のファイルに分ける
MANAGE_TOKEN = SONGS_DIR / "youtube_token_manage.json"
MANAGE_SCOPES = ["https://www.googleapis.com/auth/youtube"]
PLAYLIST_REC = LESSON_DIR / "playlist.json"
# 再生リストに並べる順（作る順。メモ fe-b-video-series と同じ）。新しい回を作ったら、ここに足す
LESSON_ORDER = ["基礎回1_変数・if・配列", "基礎回2_for・while・トレース表", "基礎回3_関数・大域変数",
                "最大値を求める", "線形探索", "二分探索", "10進数を2進数に変換する",
                "ユークリッドの互除法", "バブルソート", "選択ソート", "挿入ソート",
                "階乗（再帰）", "フィボナッチ数列", "スタック", "キュー",
                "リスト", "2分木", "ハッシュ", "クイックソート",
                "マージソート", "文字列探索", "素数", "2次元配列"]
PLAYLIST_TITLE = "基本情報技術者試験 科目B アルゴリズム解説（擬似言語を1行ずつ）"
PLAYLIST_DESC = ("基本情報技術者試験の科目Bで出る擬似言語とアルゴリズムを、ホワイトボードで1行ずつ説明するシリーズです。\n"
                 "擬似言語の読み方（基礎回）から始めて、探索・整列などのアルゴリズムへ進みます。どの回にも本番と同じ形の穴埋め問題があります。\n\n"
                 "▼ 練習はこちら（FE用語ドリル 科目B）\nhttps://fe.yogo-drill.com/\n\n※ ナレーションは合成音声です。")


def _sync(rec_path, title, desc, items):
    """再生リストがなければ公開で作り、items（[(名前, 動画 ID か None)] の並べたい順）のうち、まだ入っていないものを足す。
    記録は rec_path（再生リストの ID と、入れた動画の ID）。"""
    yt = service(MANAGE_TOKEN, MANAGE_SCOPES)
    rec = json.loads(rec_path.read_text(encoding="utf-8")) if rec_path.exists() else {}
    if not rec.get("id"):
        res = yt.playlists().insert(part="snippet,status", body={
            "snippet": {"title": title, "description": desc, "defaultLanguage": "ja"},
            "status": {"privacyStatus": "public"}}).execute()
        rec = {"id": res["id"], "title": title, "videos": []}
        rec_path.write_text(json.dumps(rec, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"再生リストを作りました: https://www.youtube.com/playlist?list={res['id']}", flush=True)
    order = [vid for _, vid in items if vid]
    for name, vid in items:
        if not vid:
            print(f"  まだ上げていない: {name}")
            continue
        if vid in rec["videos"]:
            continue
        # 先のものより後に上がっても、並べたい順の位置に入れる
        pos = sum(1 for v in rec["videos"] if v in order and order.index(v) < order.index(vid))
        yt.playlistItems().insert(part="snippet", body={"snippet": {
            "playlistId": rec["id"], "position": pos, "resourceId": {"kind": "youtube#video", "videoId": vid}}}).execute()
        rec["videos"].insert(pos, vid)
        rec_path.write_text(json.dumps(rec, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"  足しました: {name}", flush=True)
    print(f"再生リスト: https://www.youtube.com/playlist?list={rec['id']}（{len(rec['videos'])} 本）")


def _vid(p):
    return json.loads(p.read_text(encoding="utf-8"))["id"] if p.exists() else None


def sync_playlist():
    """科目Bの解説動画の再生リスト（LESSON_ORDER の順）。記録は notes/科目B解説動画/playlist.json。"""
    _sync(PLAYLIST_REC, PLAYLIST_TITLE, PLAYLIST_DESC, [(n, _vid(LESSON_DIR / n / "youtube.json")) for n in LESSON_ORDER])


# ───────── ITパスポートの解説動画（2026-11-04〜。notes/ITパスポート解説動画/<名前>/）
# 名前（フォルダ名）は 一覧.json の題名から ip_folder() で作る。再生リストは 一覧.json の順（no の順）に並べる
IP_DIR = ROOT / "notes" / "ITパスポート解説動画"
IP_TAGS = ["ITパスポート", "iパス", "IT用語", "資格勉強", "わかりやすい"]
IP_PLAYLIST_REC = IP_DIR / "playlist.json"
IP_PLAYLIST_TITLE = "ITパスポート たとえでわかる解説（全範囲）"
IP_PLAYLIST_DESC = ("ITパスポート試験の範囲を、身近なたとえ（住所・電話帳など）で、はじめての人にもわかるように説明するシリーズです。\n"
                    "どの回にも、本番と同じ4択の練習問題があります。\n\n"
                    "▼ 用語の練習はこちら（ITパスポート用語ドリル）\nhttps://ip.yogo-drill.com/\n\n※ ナレーションは合成音声です。")


def ip_folder(title):
    """一覧.json の題名 → フォルダ名（例: ネットワーク②（IPアドレス・DNS） → ネットワーク②_IPアドレス・DNS）。"""
    return title.replace("（", "_").replace("）", "").replace("？", "").replace(" ", "_")


def sync_ip_playlist():
    order = [ip_folder(v["title"]) for v in json.loads((IP_DIR / "一覧.json").read_text(encoding="utf-8"))]
    items = [(n, _vid(IP_DIR / n / "youtube.json")) for n in order]
    _sync(IP_PLAYLIST_REC, IP_PLAYLIST_TITLE, IP_PLAYLIST_DESC, [x for x in items if x[1]])


# 勉強ソングの再生リスト（2026-11-04）。曲の横長の本編だけ（ショート・前の版は入れない）を、上げた順に並べる
SONG_PLAYLIST_REC = SONGS_DIR / "playlist.json"
SONG_PLAYLIST_TITLE = "IT用語の勉強ソング（ITパスポート・基本情報）"
SONG_PLAYLIST_DESC = ("ITパスポート・基本情報技術者試験の用語を、歌と図で覚える勉強ソングです。\n"
                      "歌詞に出てくる用語を、1行ずつ図で説明します。\n\n"
                      "▼ 用語の練習はこちら（FE用語ドリル）\nhttps://fe.yogo-drill.com/\n\n※ 曲・歌声は AI で作成しています。")


def sync_song_playlist():
    recs = sorted(SONGS_DIR.glob("*/youtube.json"), key=lambda p: p.stat().st_mtime)
    _sync(SONG_PLAYLIST_REC, SONG_PLAYLIST_TITLE, SONG_PLAYLIST_DESC, [(p.parent.name, _vid(p)) for p in recs])


# ───────── もしも動画（2026-11-05〜。Higgsfield の /content-factory で作った縦長の動画。notes/もしも動画/<名前>/）
WHATIF_DIR = ROOT / "notes" / "もしも動画"
WHATIF_TAGS = ["基本情報技術者試験", "基本情報", "IT資格", "資格勉強", "もしも"]


def upload_whatif(yt, name):
    """<名前>.mp4 をショートとして非公開で上げる。題名は YouTubeのタイトル.txt、説明文は YouTubeの説明文.txt。
    絵はコードで描いたアニメで声もないので、「改変・合成されたコンテンツ」の申告はしない。記録は youtube_short.json。"""
    from googleapiclient.http import MediaFileUpload
    d = WHATIF_DIR / name
    video, tfile, dfile = d / f"{name}.mp4", d / "YouTubeのタイトル.txt", d / "YouTubeの説明文.txt"
    for p in (video, tfile, dfile):
        if not p.exists():
            sys.exit(f"ファイルがありません: {p}")
    rec = d / "youtube_short.json"
    if rec.exists():
        sys.exit(f"もう上げてあります: https://youtu.be/{_vid(rec)}（上げ直すときは {rec.name} を消してから）")
    title = tfile.read_text(encoding="utf-8").strip()[:100]
    body = dfile.read_text(encoding="utf-8").strip()[:5000]
    meta = {"snippet": {"title": title, "description": body, "tags": WHATIF_TAGS, "categoryId": CATEGORY,
                        "defaultLanguage": "ja", "defaultAudioLanguage": "ja"},
            "status": {"privacyStatus": "private", "selfDeclaredMadeForKids": False, "containsSyntheticMedia": False}}
    media = MediaFileUpload(str(video), mimetype="video/mp4", chunksize=8 * 1024 * 1024, resumable=True)
    req = yt.videos().insert(part="snippet,status", body=meta, media_body=media)
    print(f"上げています: {video.name}", flush=True)
    res = None
    while res is None:
        _, res = req.next_chunk()
    rec.write_text(json.dumps({"id": res["id"], "title": title, "privacy": "private"}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"非公開で上げました（ショート）: https://youtu.be/{res['id']}")


if __name__ == "__main__":
    args = sys.argv[1:]
    if args and args[0] == "--lesson":     # python upload_youtube.py --lesson 二分探索
        yt = service()
        for n in args[1:]:
            upload_lesson(yt, n)
        if MANAGE_TOKEN.exists():      # 再生リストの許可があれば、上げた回を再生リストにも足す
            sync_playlist()
        sys.exit()
    if args and args[0] == "--ip":         # python upload_youtube.py --ip ネットワーク②_IPアドレス・DNS
        yt = service()
        for n in args[1:]:
            upload_lesson(yt, n, IP_DIR, IP_TAGS)
        if MANAGE_TOKEN.exists():
            sync_ip_playlist()
        sys.exit()
    if args and args[0] == "--ip-playlist":
        sync_ip_playlist()
        sys.exit()
    if args and args[0] == "--whatif":     # python upload_youtube.py --whatif もしも基本情報に合格したら
        yt = service()
        for n in args[1:]:
            upload_whatif(yt, n)
        sys.exit()
    if args and args[0] == "--playlist":   # python upload_youtube.py --playlist
        sync_playlist()
        sys.exit()
    if args and args[0] == "--song-playlist":   # python upload_youtube.py --song-playlist
        sync_song_playlist()
        sys.exit()
    shorts = "--short" in args
    args = [a for a in args if a != "--short"]
    yt = service()
    if shorts:
        for n in args:
            upload_short(yt, n)
        sys.exit()
    if "--check" in args or not args:
        ch = yt.channels().list(part="snippet", mine=True).execute()
        names = [c["snippet"]["title"] for c in ch.get("items", [])]
        print("ログインしたチャンネル:", "・".join(names) or "（なし）")
        for r in sorted(SONGS_DIR.glob("*/youtube.json")):
            x = json.loads(r.read_text(encoding="utf-8"))
            print(f"  {r.parent.name}: https://youtu.be/{x['id']}")
    else:
        for n in args:
            upload(yt, n)
        if MANAGE_TOKEN.exists():      # 再生リストの許可があれば、上げた曲を勉強ソングの再生リストにも足す
            sync_song_playlist()
