"""2つの曲が同じ演奏か、どれだけずれているかを調べる（音の大きさの流れの相関）。"""
import subprocess
import sys

import numpy as np
import imageio_ffmpeg

ff = imageio_ffmpeg.get_ffmpeg_exe()
SR = 8000


def load(p):
    r = subprocess.run([ff, "-hide_banner", "-i", p], capture_output=True).stderr.decode("utf-8", "ignore")
    info = [l.strip() for l in r.splitlines() if "Duration" in l or "Audio:" in l]
    raw = subprocess.run([ff, "-v", "quiet", "-i", p, "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"], capture_output=True).stdout
    return np.frombuffer(raw, dtype=np.float32), info


a, ia = load(sys.argv[1])
b, ib = load(sys.argv[2])
print("前:", ia)
print("新:", ib)
hop = 80  # 10ms
ea = np.array([np.sqrt(np.mean(a[i:i + hop] ** 2)) for i in range(0, len(a) - hop, hop)])
eb = np.array([np.sqrt(np.mean(b[i:i + hop] ** 2)) for i in range(0, len(b) - hop, hop)])
n = min(len(ea), len(eb))
ea0, eb0 = ea - ea.mean(), eb - eb.mean()
best = None
for lag in range(-300, 301):   # ±3秒
    if lag >= 0:
        x, y = ea0[lag:n], eb0[: n - lag]
    else:
        x, y = ea0[: n + lag], eb0[-lag:n]
    c = float(np.dot(x, y) / (np.linalg.norm(x) * np.linalg.norm(y) + 1e-9))
    if best is None or c > best[1]:
        best = (lag, c)
print(f"いちばん合うずれ: {best[0] * 10} ミリ秒（正なら新しい曲が早い）・相関 {best[1]:.3f}")
# 区間ごとの相関（途中から別の演奏になっていないか）
lag = best[0]
for s in range(0, n - 3000, 3000):
    x = ea0[s + max(lag, 0): s + 3000 + max(lag, 0)]
    y = eb0[s + max(-lag, 0): s + 3000 + max(-lag, 0)]
    m = min(len(x), len(y))
    c = float(np.dot(x[:m], y[:m]) / (np.linalg.norm(x[:m]) * np.linalg.norm(y[:m]) + 1e-9))
    print(f"  {s / 100:5.0f}秒〜 相関 {c:.3f}")
