"""音声認識の結果（言葉ごとの時間）と歌詞を突き合わせて、歌詞の各行の [開始, 終了] を作る。"""
import difflib
import json
import re
import sys
import unicodedata

asr = json.load(open(sys.argv[1], encoding="utf-8"))
lyr_path, out_path = sys.argv[2], sys.argv[3]
lines = [ln.strip() for ln in open(lyr_path, encoding="utf-8") if ln.strip()]


def norm(s):
    s = unicodedata.normalize("NFKC", s).lower()
    return re.sub(r"[\s・、。,.!?！？()（）「」『』=＝÷+＋−\-²~〜]", "", s)


# 認識した文字の列と、1文字ごとの時間
rc, rt = [], []
for s, e, w, p in asr["words"]:
    n = norm(w)
    for k, ch in enumerate(n):
        rc.append(ch)
        rt.append(s + (e - s) * (k + 0.5) / max(1, len(n)))
# 歌詞の文字の列と、行の番号
lc, li = [], []
for i, ln in enumerate(lines):
    for ch in norm(ln):
        lc.append(ch)
        li.append(i)

sm = difflib.SequenceMatcher(None, lc, rc, autojunk=False)
lt = [None] * len(lc)
for a, b, n in sm.get_matching_blocks():
    for k in range(n):
        lt[a + k] = rt[b + k]
matched = sum(x is not None for x in lt)
print(f"歌詞 {len(lc)} 文字のうち {matched} 文字が一致")

# 行ごとに、一致した文字の時間から開始・終了を決める
res = []
for i, ln in enumerate(lines):
    ts = [lt[k] for k in range(len(lc)) if li[k] == i and lt[k] is not None]
    res.append([min(ts), max(ts)] if len(ts) >= 2 else None)
# 一致がない行は前後から補う
for i in range(len(res)):
    if res[i] is None:
        prev = next((res[j] for j in range(i - 1, -1, -1) if res[j]), None)
        nxt = next((res[j] for j in range(i + 1, len(res)) if res[j]), None)
        s = prev[1] + 0.3 if prev else (nxt[0] - 5)
        e = nxt[0] - 0.3 if nxt else s + 5
        res[i] = [s, e]
# 文字の時間は文字のまん中なので、少し広げる。次の行と重ならないように
for i in range(len(res)):
    s, e = res[i]
    s -= 0.25
    e += 0.35
    if i + 1 < len(res):
        e = min(e, res[i + 1][0] - 0.3)
    res[i] = [round(s, 2), round(max(e, s + 0.8), 2)]
for (s, e), ln in zip(res, lines):
    print(f"{s:7.2f} {e:7.2f}  {ln}")
json.dump(res, open(out_path, "w", encoding="utf-8"), indent=0)
