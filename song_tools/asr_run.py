"""曲を文字に起こして、言葉ごとの時間を JSON に書く。"""
import json
import sys
import types
# av（音声の読み込み）は Windows のアプリ制御に止められることがある（19.0.1 も 2026-10-28 に止められた）。
# 音は raw を numpy で渡すので av は使わない。読み込めないときは空のモジュールで代える
try:
    import av  # noqa: F401
except ImportError:
    sys.modules["av"] = types.ModuleType("av")
from faster_whisper import WhisperModel

src, out, lyr = sys.argv[1], sys.argv[2], sys.argv[3]
lyrics = open(lyr, encoding="utf-8").read()
model = WhisperModel("large-v3-turbo", device="cpu", compute_type="int8")
import numpy as np
audio = np.fromfile(src, dtype=np.int16).astype(np.float32) / 32768
segs, info = model.transcribe(
    audio, language="ja", word_timestamps=True, vad_filter=False, beam_size=5,
    initial_prompt=lyrics.replace("\n", " ")[:300], condition_on_previous_text=False)
words, lines = [], []
for s in segs:
    lines.append([round(s.start, 2), round(s.end, 2), s.text])
    print(f"{s.start:7.2f} {s.end:7.2f} {s.text}", flush=True)
    for w in s.words or []:
        words.append([round(w.start, 2), round(w.end, 2), w.word, round(w.probability, 3)])
json.dump({"segments": lines, "words": words}, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=0)
print("words", len(words))
