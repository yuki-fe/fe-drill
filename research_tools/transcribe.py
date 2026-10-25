"""音声（wav）を文字に起こして「[mm:ss] 文」の行で書く。.venv-asr で動かす（video_research.py が呼ぶ）。"""
import argparse
import sys

from faster_whisper import WhisperModel

sys.stdout.reconfigure(encoding="utf-8")
ap = argparse.ArgumentParser()
ap.add_argument("wav")
ap.add_argument("out")
ap.add_argument("--model", default="large-v3-turbo")
ap.add_argument("--lang", default=None, help="言語（なければ自動）")
args = ap.parse_args()

model = WhisperModel(args.model, device="cpu", compute_type="int8")
segs, info = model.transcribe(args.wav, language=args.lang, vad_filter=True, beam_size=5)
print("言語:", info.language, flush=True)
lines = []
for s in segs:
    t = int(s.start)
    lines.append(f"[{t // 60:02d}:{t % 60:02d}] {s.text.strip()}")
    print(lines[-1], flush=True)
open(args.out, "w", encoding="utf-8").write("\n".join(lines) + "\n")
