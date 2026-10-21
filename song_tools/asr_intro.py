"""曲の最初の40秒だけを文字に起こして、言葉ごとの時間を出す。"""
import sys
import numpy as np
from faster_whisper import WhisperModel

audio = np.fromfile(sys.argv[1], dtype=np.int16).astype(np.float32) / 32768
audio = audio[: 16000 * int(sys.argv[2] if len(sys.argv) > 2 else 40)]
model = WhisperModel("large-v3-turbo", device="cpu", compute_type="int8")
segs, _ = model.transcribe(audio, language="ja", word_timestamps=True, beam_size=5, condition_on_previous_text=False,
                           initial_prompt="Yeah mon ワン・ラブ・ストラテジ 島の風に乗せて 経営の話をしようぜ Everybody 戦略 戦略 Irie",
                           no_repeat_ngram_size=3, vad_filter=True)
for s in segs:
    print(f"{s.start:6.2f} {s.end:6.2f} {s.text}")
    for w in s.words or []:
        print(f"    {w.start:6.2f} {w.end:6.2f} {w.word}")
