"""曲の YouTube 横長版を、YouTube に「非公開」で上げる（タイトル・説明文・チャプター・サムネイルつき）。

公開は、運営者が YouTube Studio で内容を確かめてから「公開」を押す。
（Google の審査を受けていないアプリから上げた動画は、非公開に固定されるため。自動で公開はしない）

    python upload_youtube.py コミットしないで     # 1曲を上げる
    python upload_youtube.py --check              # ログインと、上げた記録だけ確かめる
    python upload_youtube.py --short コミットしないで   # 縦長のショート版（make_reel_cut.py --shorts で作る）を上げる

使うファイル（どれも notes/ の中で、公開しない）
- notes/曲の動画/youtube_client_secret.json   Google Cloud で作った OAuth クライアント（デスクトップ アプリ）
- notes/曲の動画/youtube_token.json           初回にブラウザで許可すると作られる。合言葉と同じ扱い
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


def service():
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    creds = None
    if TOKEN.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN), SCOPES)
    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
        except Exception:
            creds = None   # 許可の期限切れ（テスト中のアプリは7日ほど）→ もう一度ブラウザで許可
    if not creds or not creds.valid:
        if not CLIENT.exists():
            sys.exit(f"OAuth クライアントのファイルがありません: {CLIENT}")
        flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT), SCOPES)
        print("ブラウザが開きます。YouTube に動画を上げる許可をしてください。", flush=True)
        creds = flow.run_local_server(port=0, prompt="consent")
        TOKEN.write_text(creds.to_json(), encoding="utf-8")
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


if __name__ == "__main__":
    args = sys.argv[1:]
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
