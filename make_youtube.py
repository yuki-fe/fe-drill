"""縦長の MV から、YouTube 用の横長の動画（1920×1080）・サムネイル・説明文を作る。

- まん中に縦長の MV（図と歌詞）を置き、左右は文字のない背景の映像をぼかして広げる
- 左に曲名と説明、右に用語サイトの宣伝を出す
- サムネイル（1280×720）と、チャプター（場面ごとの時間）つきの説明文も作る

    python make_youtube.py
"""
import json
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

import imageio_ffmpeg
from mv_common import BG1, BLUE, CELL, CREAM, GOLD, GREEN, MUTED, font, mix

ROOT = Path(__file__).parent
SONGS_DIR = ROOT / "notes" / "曲の動画"
WORK = SONGS_DIR / "作業用"                 # 背景の動画・宣伝の画像など
FOLDER = {"ストラテジ・アイランド": "ストラテジ・アイランド（商用不可）"}   # 曲名とフォルダ名がちがうもの


def song_dir(name):
    return SONGS_DIR / FOLDER.get(name, name)
YW, YH = 1920, 1080
MVW = 608            # まん中の縦長の MV の幅（高さ 1080）
SIDE = (YW - MVW) // 2

SONGS = {
    "ストラテジ・アイランド": {
        "title": "Strategy Riddim", "sub": "〜ストラテジ・アイランド〜",
        "lead": ["ITパスポート・基本情報の", "ストラテジ系の用語を、", "歌と図で覚える"],
        "terms": ["SWOT分析・3C分析", "4P・4C・PPM", "損益分岐点・ROE", "KGI・KPI・BSC", "ERP・SCM・CRM・BPR", "パレート図・ABC分析", "著作権・特許・PL法", "CSR・コンプライアンス"],
        "thumb_at": 97.0,
        "thumb_big": ["ストラテジ系", "用語を歌で覚える"],
        "thumb_small": "SWOT・PPM・損益分岐点・ROE…",
        "chapters": [(0, "タイトル・イントロ"), (39, "SWOT分析"), (53, "3C分析"), (66, "4Pと4C"), (81, "PPM"),
                     (108, "損益分岐点"), (122, "ROEと流動比率"), (130, "KGI・KPI・バランススコアカード"),
                     (144, "ERP・SCM・CRM・BPR"), (171, "パレート図・ABC分析・特性要因図"),
                     (186, "著作権・特許・PL法・不正アクセス禁止法"), (207, "CSR・コンプライアンス"), (236, "アウトロ")],
        "yt_title": "【勉強ソング】ストラテジ系の用語を歌で覚える｜Strategy Riddim 〜ストラテジ・アイランド〜（ITパスポート・基本情報）",
        "tags": "#ITパスポート #基本情報技術者試験 #ストラテジ系 #勉強ソング #資格勉強",
        "desc": "ITパスポート試験・基本情報技術者試験のストラテジ系に出てくる用語を、歌にしました。",
    },
    "クリティカルパス": {
        "title": "クリティカルパス", "sub": "〜完了しなかったプロジェクト〜",
        "lead": ["プロジェクトマネジメントの", "用語で歌う、", "冬の歌"],
        "terms": ["ガントチャート・WBS", "スラック・クリティカルパス", "クラッシング・ファストトラッキング", "リスク対応の4つ",
                  "SLA・インシデント・問題管理", "EVM（PV・EV・AC）", "BCP・変更管理", "ベースライン・監査証跡"],
        "thumb_at": 100.0,
        "thumb_big": ["クリティカルパス", "PM用語で歌う冬の歌"],
        "thumb_small": "WBS・EVM・リスク対応・変更管理…",
        "chapters": [(0, "イントロ"), (13, "ガントチャート"), (42, "WBS"), (62, "スラック"), (72, "クリティカルパス（サビ）"),
                     (108, "リスク対応（回避・転嫁・軽減・受容）"), (122, "SLA・インシデント"), (138, "問題管理"),
                     (149, "クリティカルパス（サビ2）"), (178, "EVM・BCP"), (208, "変更管理・ベースライン"),
                     (240, "監査証跡"), (254, "エンディング")],
        "yt_title": "【勉強ソング】プロジェクトマネジメントの用語で歌う冬の歌｜クリティカルパス 〜完了しなかったプロジェクト〜（ITパスポート・基本情報）",
        "tags": "#ITパスポート #基本情報技術者試験 #プロジェクトマネジメント #勉強ソング #資格勉強",
        "desc": "ITパスポート試験・基本情報技術者試験のマネジメント系に出てくる、プロジェクトマネジメントやサービスマネジメントの用語を、冬の歌にしました。",
    },
}
# 新しい音源（ワン・ラブ・ストラテジ）: 用語は同じで、曲名・時間・チャプターがちがう
# （2026-10-22: 前の曲名のまま写していたので、曲名・タイトル・用語を分けた）
SONGS["ワン・ラブ・ストラテジ"] = dict(
    SONGS["ストラテジ・アイランド"], thumb_at=84.0,
    title="ワン・ラブ・ストラテジ", sub="〜One Love Strategy〜",
    yt_title="【勉強ソング】ストラテジ系の用語を歌で覚える｜ワン・ラブ・ストラテジ（ITパスポート・基本情報）",
    desc="ITパスポート試験・基本情報技術者試験のストラテジ系に出てくる用語を、レゲエの歌にしました。",
    terms=["SWOT分析・3C分析", "4P・4C・PPM", "損益分岐点・ROE・流動比率", "KGI・KPI・BSC",
           "ERP・SCM・CRM・コアコンピタンス・BPR", "パレート図・ABC分析・特性要因図",
           "著作権・特許・PL法・不正アクセス禁止法", "CSR・コンプライアンス"],
    chapters=[
    (0, "イントロ"), (29, "SWOT分析"), (44, "3C分析"), (55, "4Pと4C"), (69, "PPM"), (94, "損益分岐点"),
    (108, "ROEと流動比率"), (121, "KGI・KPI・バランススコアカード"), (136, "ERP・SCM・CRM・BPR"),
    (160, "パレート図・ABC分析・特性要因図"), (178, "著作権・特許・PL法・不正アクセス禁止法"),
    (192, "CSR・コンプライアンス"), (217, "エンディング")])
SONGS["コミットしないで"] = {
    "title": "コミットしないで", "sub": "〜夏の恋とコンピュータ〜",
    "lead": ["コンピュータの", "用語で歌う、", "夏の恋の歌"],
    "terms": ["2進数", "割り込み・優先度", "3ウェイハンドシェイク", "コミット・ロールバック・ACID",
              "キャッシュ・デッドロック", "排他制御", "二分探索・ping・バックアップ", "暗号化・秘密鍵"],
    "thumb_at": 80.0,
    "thumb_big": ["コミットしないで", "IT用語で歌う夏の恋"],
    "thumb_small": "ACID・デッドロック・暗号化…",
    "chapters": [(0, "イントロ"), (14, "2進数"), (41, "割り込みと優先度"), (57, "3ウェイハンドシェイク"),
                 (69, "コミットとロールバック（サビ）"), (102, "キャッシュ"), (130, "デッドロック"), (145, "排他制御"),
                 (158, "コミットとロールバック（サビ2）"), (186, "二分探索・ping・フルバックアップ"),
                 (216, "暗号化と秘密鍵"), (245, "アウトロ")],
    "yt_title": "【勉強ソング】コンピュータの用語で歌う夏の恋の歌｜コミットしないで（ITパスポート・基本情報）",
    "tags": "#ITパスポート #基本情報技術者試験 #テクノロジ系 #勉強ソング #資格勉強",
    "desc": "ITパスポート試験・基本情報技術者試験のテクノロジ系に出てくる、2進数・ネットワーク・データベース・セキュリティの用語を、夏の恋の歌にしました。",
}
SONGS["リカーシブルキング"] = {
    "title": "リカーシブルキング", "sub": "Recursive King",
    "lead": ["アルゴリズムと", "開発の用語で刻む、", "IT のラップ"],
    "terms": ["再帰・スタック・ベースケース", "バブルソート・マージソート・ヒープ・計算量", "逆ポーランド記法",
              "外部キー・インデックス・ビュー・射影", "スタブ・ドライバ・テスト駆動開発・リファクタリング",
              "ブルートフォース攻撃・辞書攻撃・DDoS", "ペアプログラミング・スクラム"],
    "thumb_at": 24.0,
    "thumb_big": ["リカーシブルキング", "IT用語で刻むラップ"],
    "thumb_small": "再帰・ソート・DB・テスト…",
    "chapters": [(0, "イントロ・再帰とスタック（サビ）"), (27, "ソートと計算量"), (49, "再帰とスタック（サビ2）"),
                 (69, "逆ポーランド記法・データベース"), (95, "テスト・TDD・リファクタリング"),
                 (116, "攻撃・パスワード・ペアプロ・スクラム"), (136, "最後のサビ"), (157, "アウトロ（return）")],
    "yt_title": "【勉強ソング】再帰・ソート・DB・テストの用語で刻むラップ｜リカーシブルキング（基本情報・ITパスポート）",
    "tags": "#基本情報技術者試験 #ITパスポート #アルゴリズム #勉強ソング #資格勉強",
    "desc": "基本情報技術者試験・ITパスポート試験に出てくる、アルゴリズム（再帰・ソート・逆ポーランド記法）・データベース・テスト・セキュリティ・アジャイルの用語を、ラップにしました。",
}
SONGS["ビットバイト・ダンス"] = {
    "title": "ビットバイト・ダンス", "sub": "Bit Byte Dance",
    "lead": ["0 と 1 の", "基礎理論で踊る、", "エレクトロの歌"],
    "terms": ["ビット・バイト・2のn乗", "2進数・10進数・16進数", "AND・OR・NOT・XOR・シフト", "2の補数",
              "パリティチェック・CRC・ハミング符号", "情報量", "期待値・正規分布", "オートマトン・BNF"],
    "thumb_at": 70.0,
    "thumb_big": ["ビットバイト・ダンス", "0と1の基礎理論"],
    "thumb_small": "16進数・論理演算・2の補数…",
    "chapters": [(0, "イントロ"), (28, "ビットとバイト"), (43, "16進数・2のn乗"), (64, "基数とビット演算（サビ）"),
                 (93, "論理演算（NOT・AND・OR）"), (107, "パリティ・CRC・ハミング符号"), (121, "情報量"),
                 (135, "基数とビット演算（サビ2）"), (164, "期待値・正規分布・オートマトン・BNF"),
                 (195, "2の補数（最後のサビ）"), (229, "アウトロ")],
    "yt_title": "【勉強ソング】2進数・16進数・論理演算の用語で踊る｜ビットバイト・ダンス（基本情報・ITパスポート）",
    "tags": "#基本情報技術者試験 #ITパスポート #基礎理論 #勉強ソング #資格勉強",
    "desc": "基本情報技術者試験・ITパスポート試験の基礎理論に出てくる、ビットとバイト・基数の変換・論理演算・誤り検出・情報量・確率・オートマトンの用語を、エレクトロの歌にしました。",
}
SONGS["ハードウェア・レイヴ"] = {
    "title": "ハードウェア・レイヴ", "sub": "Hardware Rave",
    "lead": ["CPU・メモリ・入出力の", "ハードウェアの用語で", "上がる EDM"],
    "terms": ["マルチコア・GPU", "DRAM・SRAM・キャッシュ", "揮発性・フラッシュメモリ", "SSD・HDD",
              "USB・ホットプラグ・バスパワー", "Bluetooth・NFC・HDMI", "RGB・CMYK・解像度・dpi", "センサ・有機EL・液晶"],
    "thumb_at": 78.0,
    "thumb_big": ["ハードウェア・レイヴ", "CPU・メモリ・入出力"],
    "thumb_small": "SSD・HDD・DRAM・SRAM・USB…",
    "chapters": [(0, "イントロ（電源オン）"), (32, "マルチコアと GPU"), (46, "DRAM と SRAM"), (61, "揮発性とフラッシュメモリ"),
                 (75, "SSD と HDD（ドロップ）"), (109, "USB・ホットプラグ・バスパワー"), (117, "Bluetooth・NFC・HDMI"),
                 (128, "RGB と CMYK"), (146, "画素・解像度・dpi（ドロップ2）"), (161, "センサ・タッチパネル・有機EL・液晶"),
                 (183, "クロック〜最後のドロップ"), (233, "アウトロ")],
    "yt_title": "【勉強ソング】SSD・DRAM・USBのハードウェア用語で上がる｜ハードウェア・レイヴ（基本情報・ITパスポート）",
    "tags": "#基本情報技術者試験 #ITパスポート #ハードウェア #勉強ソング #資格勉強",
    "desc": "基本情報技術者試験・ITパスポート試験のハードウェアの分野に出てくる、CPU（マルチコア・GPU）・メモリ（DRAM・SRAM・フラッシュメモリ）・記憶装置（SSD・HDD）・入出力インタフェース（USB・Bluetooth・NFC・HDMI）・色と解像度・入出力装置の用語を、EDM（レイヴ）の歌にしました。",
}
SONGS["デュプレックス・ハート"] = {
    "title": "デュプレックス・ハート", "sub": "Duplex Heart",
    "lead": ["システム構成と OS の", "用語で歌う、", "80年代ロック"],
    "terms": ["クライアントサーバ・シンクライアント", "P2P・集中処理・分散処理", "OS・カーネル・デバイスドライバ",
              "デュプレックス・デュアルシステム", "稼働率・フェイルオーバー", "スプーリング・絶対パス・相対パス",
              "レスポンス・ターンアラウンド・スループット", "ホット・コールドスタンバイ"],
    "thumb_at": 92.0,
    "thumb_big": ["デュプレックス・ハート", "システム構成と OS"],
    "thumb_small": "デュアル・ホットスタンバイ・P2P…",
    "chapters": [(0, "イントロ"), (35, "クライアントとサーバー"), (57, "ピアツーピア・集中と分散"), (71, "OS の仕事"),
                 (87, "デュプレックスとデュアル（サビ）"), (123, "スプーリング"), (138, "絶対パスと相対パス"),
                 (153, "レスポンスタイム・スループット"), (170, "稼働率（サビ2）"), (202, "ギターソロ（フェイルオーバー）"),
                 (229, "ホットスタンバイとコールドスタンバイ"), (255, "オープンソース（最後のサビ）"), (290, "アウトロ")],
    "yt_title": "【勉強ソング】デュプレックス・デュアル・ホットスタンバイの用語で歌う80年代ロック｜デュプレックス・ハート（基本情報・ITパスポート）",
    "tags": "#基本情報技術者試験 #ITパスポート #システム構成 #勉強ソング #資格勉強",
    "desc": "基本情報技術者試験・ITパスポート試験に出てくる、システム構成（クライアントサーバ・P2P・デュプレックスシステム・デュアルシステム・ホットスタンバイ・稼働率）・OS（カーネル・デバイスドライバ・スプーリング・パス）・性能の指標（レスポンスタイム・スループット）の用語を、80年代ロックのパワーバラードにしました。",
}
SONGS["テザリングサマー"] = {
    "title": "テザリング・サマー", "sub": "Tethering Summer",
    "lead": ["ネットワークの用語で", "海までドライブする、", "夏のポップス"],
    "terms": ["LAN・WAN", "5G（高速・大容量・低遅延）", "テザリング・ハンドオーバー", "アクセスポイント・SSID・WPA3",
              "スイッチ・ハブ・MACアドレス", "SMTP・POP3・IMAP", "Cookie・プロキシ・HTTPS", "bps"],
    "thumb_at": 60.5,
    "thumb_big": ["テザリング・サマー", "ネットワークの用語"],
    "thumb_small": "LAN・5G・SSID・SMTP・HTTPS…",
    "chapters": [(0, "イントロ"), (8, "LAN と WAN"), (21, "5G"), (35, "テザリング"), (47, "ハンドオーバー（サビ）"),
                 (76, "アクセスポイント・SSID・WPA3"), (90, "スイッチとハブ"), (104, "SMTP・POP3・IMAP"),
                 (117, "ハンドオーバー（サビ2）"), (140, "Cookie・プロキシ・HTTPS"), (168, "bps（最後のサビ）"), (190, "アウトロ")],
    "yt_title": "【勉強ソング】LAN・5G・SSID・SMTPのネットワーク用語で夏のドライブ｜テザリング・サマー（基本情報・ITパスポート）",
    "tags": "#基本情報技術者試験 #ITパスポート #ネットワーク #勉強ソング #資格勉強",
    "desc": "基本情報技術者試験・ITパスポート試験に出てくる、ネットワーク（LAN・WAN・5G・テザリング・ハンドオーバー）・無線LAN（アクセスポイント・SSID・WPA3）・スイッチとハブ・メール（SMTP・POP3・IMAP）・Web（Cookie・プロキシ・HTTPS）・bps の用語を、夏のドライブのポップスにしました。",
    "credit": "映像：コードで描いた、シルクスクリーン印刷の旅行ポスター風のアニメーション（Lemo-Opuscar の画風。MIT License）\n字体：Big Shoulders Display・Zen Kaku Gothic New・Dela Gothic One（SIL Open Font License）",
}
SONGS["ゼロトラスト"] = {
    "title": "ゼロトラスト", "sub": "Zero Trust",
    "lead": ["攻撃の手口と守り方を", "セキュリティの用語で歌う、", "ダークなロック"],
    "terms": ["マルウェア・ウイルス・ワーム・トロイの木馬", "ボット・スパイウェア・キーロガー", "ショルダーハッキング・トラッシング",
              "ゼロトラスト", "標的型・水飲み場型・中間者攻撃", "XSS・DNSキャッシュポイズニング", "認証局・ワンタイムパスワード",
              "ハニーポット・サンドボックス・ペネトレーションテスト", "リスクアセスメント・ISMS・CSIRT", "生体認証・シングルサインオン"],
    "thumb_at": 79.5,
    "thumb_big": ["ゼロトラスト", "セキュリティの用語"],
    "thumb_small": "マルウェア・XSS・ISMS・CSIRT…",
    "chapters": [(0, "イントロ（誰も信じるな）"), (24, "マルウェア・ウイルス・ワーム・トロイの木馬"), (42, "ボット・スパイウェア・キーロガー"),
                 (56, "ショルダーハッキング・トラッシング"), (70, "ゼロトラスト（サビ）"), (97, "標的型・水飲み場型・中間者攻撃"),
                 (112, "XSS・DNSキャッシュポイズニング"), (125, "認証局・ワンタイムパスワード"), (139, "ゼロトラスト（サビ2）"),
                 (167, "ハニーポット・サンドボックス・ペネトレーションテスト"), (187, "リスクアセスメント・ISMS・CSIRT"),
                 (215, "生体認証・シングルサインオン（最後のサビ）"), (240, "セキュリティパッチ（アウトロ）")],
    "yt_title": "【勉強ソング】マルウェア・XSS・ゼロトラストのセキュリティ用語で歌うロック｜ゼロトラスト（基本情報・ITパスポート）",
    "tags": "#基本情報技術者試験 #ITパスポート #情報セキュリティ #勉強ソング #資格勉強",
    "desc": "基本情報技術者試験・ITパスポート試験に出てくる、情報セキュリティ（マルウェア・ソーシャルエンジニアリング・標的型攻撃・中間者攻撃・クロスサイトスクリプティング・DNSキャッシュポイズニング・認証局・ワンタイムパスワード・ゼロトラスト・ハニーポット・サンドボックス・ペネトレーションテスト・リスクアセスメント・ISMS・CSIRT・生体認証・シングルサインオン）の用語を、ダークなロックにしました。",
    "credit": "映像：コードで描いた、網点印刷の調書風のアニメーション（Lemo-Opuscar の画風。MIT License）\n字体：Noto Serif JP・Bagel Fat One・JetBrains Mono・Zen Kaku Gothic New（SIL Open Font License）",
}
SONGS["アイティルダンス"] = {
    "title": "アイティル・ダンス", "sub": "ITIL Dance",
    "lead": ["サービスマネジメントと", "監査の用語で踊る、", "アシッドなダンス曲"],
    "terms": ["サービスデスク・SPOC", "インシデント管理・問題管理", "変更管理・リリース管理・構成管理（CMDB）", "サービスレベル管理・SLA",
              "可用性管理・キャパシティ管理", "ファシリティマネジメント・UPS・自家発電", "免震構造・入退室管理", "ファンクションポイント法・類推見積法",
              "システム監査人・職務分掌", "内部統制・ITガバナンス"],
    "thumb_at": 20.0,
    "thumb_big": ["アイティル・ダンス", "サービスマネジメント"],
    "thumb_small": "SLA・CMDB・UPS・内部統制…",
    "chapters": [(0, "イントロ（サービス・スタート）"), (24, "サービスデスクと SPOC"), (38, "インシデント・問題・変更・リリース管理"),
                 (46, "構成管理（CMDB）"), (54, "サービスレベル管理・SLA・可用性・キャパシティ（サビ）"), (87, "ファシリティマネジメント・UPS"),
                 (102, "自家発電・免震構造・入退室管理"), (110, "ファンクションポイント法"), (117, "サービスレベル管理（サビ2）"),
                 (147, "類推見積法・システム監査人・職務分掌"), (172, "内部統制・ITガバナンス（最後のサビ）"), (198, "アウトロ（シャットダウン）")],
    "yt_title": "【勉強ソング】SLA・CMDB・内部統制のサービスマネジメント用語で踊る｜アイティル・ダンス（基本情報・ITパスポート）",
    "tags": "#基本情報技術者試験 #ITパスポート #サービスマネジメント #勉強ソング #資格勉強",
    "desc": "基本情報技術者試験・ITパスポート試験に出てくる、サービスマネジメント（サービスデスク・インシデント管理・問題管理・変更管理・リリース管理・構成管理・サービスレベル管理・SLA・可用性管理・キャパシティ管理）・ファシリティマネジメント（UPS・自家発電・免震構造・入退室管理）・見積もり（ファンクションポイント法・類推見積法）・システム監査（独立性・職務分掌・内部統制・ITガバナンス）の用語を、アシッドなダンス曲にしました。",
    "credit": "映像：コードで描いた、等角投影のインフォグラフィック風のアニメーション（Lemo-Opuscar の画風。MIT License）\n字体：Jost・Zen Kaku Gothic New（SIL Open Font License）\nITIL は PeopleCert グループの登録商標です。この動画はその団体とは関係ありません",
}
SITES = [("ITパスポート用語ドリル", "https://ip.yogo-drill.com/", GREEN), ("FE用語ドリル", "https://fe.yogo-drill.com/", BLUE)]


def grab(src, t, w, h):
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    raw = subprocess.run([ff, "-loglevel", "error", "-ss", f"{t:.3f}", "-i", str(src), "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                         capture_output=True).stdout
    return Image.frombytes("RGB", (w, h), raw[: w * h * 3])


def panels(info, path):
    """左右の文字（まん中は透明）。"""
    img = Image.new("RGBA", (YW, YH), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    cx = SIDE / 2

    def text(x, y, s, size, col, bold=True):
        d.text((x, y), s, font=font(size, bold), fill=col + (255,), anchor="mm")

    # 左: 曲名と説明
    text(cx, 170, info["title"], 64, GOLD)
    text(cx, 240, info["sub"], 38, CREAM)
    for k, s in enumerate(info["lead"]):
        text(cx, 340 + k * 50, s, 34, CREAM, False)
    for k, s in enumerate(info["terms"]):
        y = 540 + k * 58
        d.rounded_rectangle((cx - 240, y - 24, cx + 240, y + 24), radius=24, fill=mix(BG1, CELL, 0.9) + (215,))
        text(cx, y, s, 28, CREAM)
    # 右: 用語サイトの宣伝
    rx = SIDE + MVW + SIDE / 2
    text(rx, 230, "用語の復習は", 44, CREAM)
    for k, (name, url, col) in enumerate(SITES):
        y = 380 + k * 190
        d.rounded_rectangle((rx - 270, y - 70, rx + 270, y + 70), radius=26, fill=mix(BG1, CELL, 0.9) + (225,), outline=col + (255,), width=4)
        text(rx, y - 20, name, 40, CREAM)
        text(rx, y + 32, url.replace("https://", "").rstrip("/"), 32, GOLD)
    text(rx, 720, "カード・4択・書いて答える", 32, CREAM, False)
    text(rx, 770, "無料・登録なし・スマホで使える", 32, CREAM, False)
    d.rounded_rectangle((rx - 200, 850, rx + 200, 920), radius=35, fill=GOLD + (255,))
    text(rx, 885, "概要欄のリンクから", 34, BG1)
    img.save(path)


FONTS = SONGS_DIR / "フォント"   # Google Fonts（OFL。商用でも無料）。公開しないフォルダに置く
# 曲ごとのサムネイル: 曲名の字体・景色（背景素材の映像の番号と秒）・色
THUMBS = {
    "クリティカルパス": {"font": "ShipporiMincho-ExtraBold.ttf", "clip": 4240, "at": 6.0, "size": 128,
                       "tint": (60, 90, 150), "dark": 0.42, "snow": True, "title_col": (240, 244, 250), "glow": (120, 170, 255),
                       "sub": "〜完了しなかったプロジェクト〜", "line": "プロジェクトマネジメントの用語で歌う、冬の歌"},
    "ワン・ラブ・ストラテジ": {"font": "ReggaeOne-Regular.ttf", "clip": 44499, "at": 6.0, "size": 88,
                          "tint": None, "dark": 0.25, "snow": False, "rasta": True, "glow": (0, 0, 0),
                          "sub": "One Love Strategy", "line": "ストラテジ系の用語を、レゲエで覚える"},
    "コミットしないで": {"font": "KleeOne-SemiBold.ttf", "clip": 4151, "at": 6.0, "size": 124,
                       "tint": None, "dark": 0.2, "snow": False, "title_col": (255, 244, 248), "glow": (255, 120, 170),
                       "sub": "", "line": "コンピュータの用語で歌う、夏の恋の歌"},
    # ui-ux-pro-max の提案（深い紫紺・0＝シアン・1＝ローズ・ドット文字）に合わせた
    "ビットバイト・ダンス": {"font": "DotGothic16-Regular.ttf", "clip": 28900, "at": 6.0, "size": 92,
                          "tint": (17, 10, 36), "dark": 0.3, "snow": False, "title_col": (34, 211, 238), "glow": (244, 63, 94),
                          "sub": "Bit Byte Dance", "line": "0 と 1 の基礎理論で踊る、エレクトロの歌"},
    # ui-ux-pro-max の提案（暗い背景・ネオンのピンク・金色）に合わせた
    "リカーシブルキング": {"font": "DelaGothicOne-Regular.ttf", "clip": 830, "at": 6.0, "size": 96,
                         "tint": (15, 23, 42), "dark": 0.3, "snow": False, "title_col": (245, 179, 1), "glow": (236, 72, 153),
                         "sub": "Recursive King", "line": "アルゴリズムと開発の用語で刻む、IT のラップ"},
    # ui-ux-pro-max の提案（深い紺・ネオンのアシッドグリーン・マゼンタ・シアン）に合わせた
    "ハードウェア・レイヴ": {"font": "RocknRollOne-Regular.ttf", "clip": 50449, "at": 6.0, "size": 92,
                          "tint": (15, 15, 35), "dark": 0.3, "snow": False, "title_col": (190, 242, 100), "glow": (255, 64, 160),
                          "sub": "Hardware Rave", "line": "CPU・メモリ・入出力の用語で上がる、EDM の歌"},
    # ui-ux-pro-max の提案（Retro-Futurism。黒に近い紫・ホットピンク＝主系・エレクトリックブルー＝待機系）に合わせた
    "デュプレックス・ハート": {"font": "RampartOne-Regular.ttf", "clip": 44154, "at": 6.0, "size": 92,
                           "tint": (16, 10, 24), "dark": 0.3, "snow": False, "title_col": (255, 46, 136), "glow": (64, 156, 255),
                           "sub": "Duplex Heart", "line": "システム構成と OS の用語で歌う、80年代ロック"},
    # Lemo-Opuscar のシルクスクリーン旅行ポスターの MV。背景は横長版の1コマ（基地局 B のポスター）、色はポスターのインク
    "テザリングサマー": {"font": "DelaGothicOne-Regular.ttf", "title": "テザリング・サマー", "frame": "テザリングサマー_YouTube.mp4", "at": 206.0, "size": 92,
                       "tint": (21, 48, 74), "dark": 0.25, "snow": False, "title_col": (243, 234, 214), "glow": (239, 106, 62),
                       "sub": "Tethering Summer", "line": "ネットワークの用語で、海までドライブする夏の歌"},
    "ゼロトラスト": {"font": "DelaGothicOne-Regular.ttf", "frame": "ゼロトラスト_YouTube.mp4", "at": 3.5, "size": 104,
                   "tint": (30, 27, 46), "dark": 0.3, "snow": False, "title_col": (242, 180, 44), "glow": (215, 53, 43),
                   "sub": "Zero Trust", "line": "攻撃の手口と守り方を、セキュリティの用語で歌うロック"},
    "アイティルダンス": {"font": "DelaGothicOne-Regular.ttf", "title": "アイティル・ダンス", "frame": "アイティルダンス_YouTube.mp4", "at": 20.0, "size": 84,
                      "tint": (60, 127, 177), "dark": 0.35, "snow": False, "title_col": (251, 244, 230), "glow": (60, 127, 177),
                      "sub": "ITIL Dance", "line": "サービスマネジメントと監査の用語で踊る、ダンス曲"},
}


def thumbnail(name, info, path):
    """曲名に合った字体と、曲に合った景色のサムネイル（1280×720）。"""
    from PIL import ImageFont
    import random
    cfg = THUMBS[name]
    # Lemo-Opuscar で描いた MV は、背景の映像の代わりに横長版の1コマを使う（"frame": ファイル名）
    src = song_dir(name) / cfg["frame"] if cfg.get("frame") else SONGS_DIR / "背景素材" / f"{cfg['clip']}.mp4"
    bg = grab(src, cfg["at"], 1920, 1080).resize((1280, 720), Image.LANCZOS)
    if cfg.get("tint"):
        bg = Image.blend(bg, Image.new("RGB", bg.size, cfg["tint"]), 0.25)
    # 左側を暗くして、曲名を読みやすく
    shade = Image.new("L", (1280, 720))
    sd = ImageDraw.Draw(shade)
    for x in range(1280):
        sd.line((x, 0, x, 720), fill=int(255 * (0.75 * max(0.0, 1 - x / 900)) + 255 * cfg["dark"] * 0.5))
    bg = Image.composite(Image.new("RGB", bg.size, (6, 10, 16)), bg, shade.point(lambda v: min(v, 235)))
    d = ImageDraw.Draw(bg)
    if cfg.get("snow"):
        rnd = random.Random(3)
        for _ in range(140):
            x, y, r = rnd.uniform(0, 1280), rnd.uniform(0, 720), rnd.uniform(1.2, 3.6)
            d.ellipse((x - r, y - r, x + r, y + r), fill=(236, 242, 250))
    f = ImageFont.truetype(str(FONTS / cfg["font"]), cfg["size"])
    title = cfg.get("title", name)   # 曲名の書き方がフォルダ名とちがう曲は THUMBS に "title"
    x0, y0 = 70, 300
    # 光（ぼかした曲名）
    glow = Image.new("RGBA", bg.size, (0, 0, 0, 0))
    ImageDraw.Draw(glow).text((x0, y0), title, font=f, fill=cfg["glow"] + (230,), anchor="ls")
    glow = glow.filter(ImageFilter.GaussianBlur(14))
    bg.paste(glow, (0, 0), glow)
    d = ImageDraw.Draw(bg)
    if cfg.get("rasta"):
        # レゲエの3色（赤・金・緑）を1文字ずつ、黒いふちどり
        cols = [(228, 60, 50), (250, 200, 40), (40, 160, 80)]
        x = x0
        for k, ch in enumerate(title):
            d.text((x, y0), ch, font=f, fill=cols[k % 3], anchor="ls", stroke_width=7, stroke_fill=(10, 10, 10))
            x += f.getlength(ch)
    else:
        d.text((x0, y0), title, font=f, fill=cfg["title_col"], anchor="ls", stroke_width=2, stroke_fill=cfg["glow"])
    sub_font = ImageFont.truetype(str(FONTS / cfg["font"]), 46)
    y = y0 + 70
    if cfg["sub"]:
        d.text((x0 + 4, y), cfg["sub"], font=sub_font, fill=(240, 236, 228), anchor="ls", stroke_width=2, stroke_fill=(10, 10, 10))
        y += 70
    d.text((x0 + 4, y + 10), cfg["line"], font=font(36), fill=(240, 236, 228), anchor="ls", stroke_width=2, stroke_fill=(10, 10, 10))
    d.rounded_rectangle((x0, 600, x0 + 430, 666), radius=33, fill=GOLD)
    d.text((x0 + 215, 633), "ITパスポート・基本情報", font=font(32), fill=BG1, anchor="mm")
    bg.save(path, quality=93)


def description(info, path):
    ch = "\n".join(f"{t // 60}:{t % 60:02d} {s}" for t, s in info["chapters"])
    sites = "\n".join(f"・{n}：{u}" for n, u, _ in SITES)
    text = f"""{info['yt_title']}

{info['desc']}
歌詞に合わせて、用語の意味を図で解説しています。

▼ 用語の復習は、無料の単語帳サイトで（登録なし・スマホで使えます）
{sites}

▼ チャプター
{ch}

▼ この動画で出てくる用語
{"・".join(info["terms"])}

曲：Suno で作成
{info.get('credit', '映像素材：Mixkit')}

{info['tags']}
"""
    path.write_text(text, encoding="utf-8")


def lyric_rows(name):
    """歌詞（[見出し] の行は外す）と行ごとの [開始秒, 終了秒] を組にする。"""
    d = song_dir(name)
    lines = [ln.strip() for ln in (d / f"{name}_歌詞.txt").read_text(encoding="utf-8").splitlines()
             if ln.strip() and not (ln.strip().startswith("[") and ln.strip().endswith("]"))]
    times = json.loads((d / f"{name}_時間.json").read_text(encoding="utf-8"))
    if len(lines) != len(times):
        sys.exit(f"歌詞の行の数（{len(lines)}）と時間の数（{len(times)}）が合いません: {name}")
    return [(a, b, t) for t, (a, b) in zip(lines, times)]


def srt_time(t):
    ms = int(round(t * 1000))
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


def write_srt(rows, path):
    out = [f"{k}\n{srt_time(a)} --> {srt_time(b)}\n{t}\n" for k, (a, b, t) in enumerate(rows, 1)]
    path.write_text("\n".join(out), encoding="utf-8")


def subtitles(name):
    """YouTube 用の字幕ファイル（SRT）。横長版（フル）と、ショート版（make_reel_cut.py の切り方に合わせた時間）。
    YouTube Studio の「字幕」から上げる（API の今の権限では上げられない）。"""
    import make_reel_cut
    rows = lyric_rows(name)
    d = song_dir(name)
    write_srt(rows, d / f"{name}_字幕.srt")
    if name in make_reel_cut.CUTS:
        segs = make_reel_cut.CUTS[name][0]
        short, off = [], 0.0
        for k, (a, b) in enumerate(segs):
            for s0, e0, t in rows:
                if a <= s0 < b:
                    short.append((off + s0 - a, off + min(e0, b) - a, t))
            off += (b - a) - make_reel_cut.XFADE
        write_srt(short, d / f"{name}_ショート_字幕.srt")


def make(name, info):
    mv = song_dir(name) / f"{name}_MV.mp4"
    bgv = WORK / f"{name}_MV_背景.mp4"
    out = song_dir(name) / f"{name}_YouTube.mp4"
    tmp = WORK
    pan = tmp / f"{name}_YouTube_左右.png"
    panels(info, pan)
    thumbnail(name, info, song_dir(name) / f"{name}_YouTube_サムネイル.jpg")
    description(info, song_dir(name) / f"{name}_YouTube_説明文.txt")
    subtitles(name)
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    fc = (f"[1:v]scale={YW}:-2,crop={YW}:{YH},boxblur=18:2,colorchannelmixer=rr=0.45:gg=0.45:bb=0.45[bg];"
          f"[0:v]scale={MVW}:{YH}[mv];[bg][mv]overlay={SIDE}:0[a];[a][2:v]overlay=0:0:format=auto,format=yuv420p[v]")
    work = out.with_name(out.stem + "_作成中.mp4")
    cmd = [ff, "-y", "-loglevel", "error", "-i", str(mv), "-i", str(bgv), "-loop", "1", "-i", str(pan),
           "-filter_complex", fc, "-map", "[v]", "-map", "0:a", "-shortest",
           "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-r", "60", "-c:a", "copy", "-movflags", "+faststart", str(work)]
    if subprocess.run(cmd).returncode != 0:
        sys.exit(f"YouTube の動画を作れませんでした: {name}")
    if out.exists():
        out.replace(out.with_name(out.stem + "_前の版.mp4"))
    work.replace(out)
    print(out)


def meta_only(name, info):
    """横長の動画は make_mv_*.py --youtube で作ったものを使い、サムネイルと説明文だけ作る。"""
    mv = song_dir(name) / f"{name}_MV.mp4"
    bgv = WORK / f"{name}_MV_背景.mp4"
    thumbnail(name, info, song_dir(name) / f"{name}_YouTube_サムネイル.jpg")
    description(info, song_dir(name) / f"{name}_YouTube_説明文.txt")
    subtitles(name)
    print(song_dir(name) / f"{name}_YouTube_サムネイル.jpg")


if __name__ == "__main__":
    args = sys.argv[1:]
    meta = "--meta" in args
    names = [a for a in args if a != "--meta"] or list(SONGS)
    for n in names:
        (meta_only if meta else make)(n, SONGS[n])
