# -*- coding: utf-8 -*-
"""选取卡点片段并输出切点方案（分块计算，低内存）"""
import wave, json
import numpy as np

WAV = r"D:\项目session\blender-supercar\pipeline\audio.wav"
w = wave.open(WAV, "rb"); sr = w.getframerate(); nch = w.getnchannels()
x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32)
if nch > 1:
    x = x.reshape(-1, nch).mean(axis=1)
x /= 32768.0
w.close()

hop, win = 512, 1024
nf = 1 + (len(x) - win) // hop
window = np.hanning(win).astype(np.float32)
flux = np.zeros(nf, dtype=np.float32)
prev = None
for i in range(nf):
    seg = x[i * hop:i * hop + win] * window
    cur = np.abs(np.fft.rfft(seg))
    if prev is not None:
        d = cur - prev
        flux[i] = float(d[d > 0].sum())
    prev = cur
env_sr = sr / hop
del x

data = json.load(open(r"D:\项目session\blender-supercar\pipeline\beats.json"))
bpm = data["bpm"]; period = data["beat_period"]; phase = data["phase"]
print("detected BPM", round(bpm, 3), "period", round(period, 4), "phase", phase)

bpm_int = 108.0
period_int = 60.0 / bpm_int
print("normalized BPM", bpm_int, "period", round(period_int, 5), "54beat =", round(54 * period_int, 3), "s")

def nearest_down(t):
    k = round((t - phase) / (period * 8))
    return phase + k * period * 8

cand = nearest_down(241.5)
print("chosen 8-beat downbeat:", round(cand, 3))

seg_start = cand
seg_len = 54 * period_int
idx = int(seg_start * env_sr)
print("onset strength @downbeat:", round(float(flux[max(0, idx - 2):idx + 3].max()), 1))

beats_local = []
for j in range(55):
    t = seg_start + j * period_int
    i0 = int(t * env_sr)
    e_ = float(flux[max(0, i0 - 1):i0 + 2].max())
    beats_local.append((j, round(t - seg_start, 4), round(t, 4), round(e_, 1)))

print("\n beat   t_rel    flux")
for b in beats_local:
    print(f"  {b[0]:3d}  {b[1]:7.3f}  {b[3]:7.1f} {'#' * int(min(36, b[3] / 5))}")

bars = []
for j in range(0, 52, 4):
    v = float(np.mean([beats_local[j + k][3] for k in range(4)]))
    bars.append([j // 4, round(j * period_int, 3), round(v, 1)])
print("\n bar   t      energy")
for b in bars:
    print(f"  {b[0]:3d} {b[1]:6.2f} {b[2]:7.1f} {'#' * int(min(36, b[2] / 5))}")

json.dump({"seg_start": seg_start, "seg_len": seg_len, "bpm": bpm_int,
           "period": period_int, "beats": beats_local, "bars": bars},
          open(r"D:\项目session\blender-supercar\pipeline\cue.json", "w"))
print("\nSAVED cue.json")