# -*- coding: utf-8 -*-
"""分析 After Hours：BPM / 拍点 / 段落能量，用于动画卡点"""
import wave, sys, json
import numpy as np

WAV = r"D:\项目session\blender-supercar\pipeline\audio.wav"

w = wave.open(WAV, "rb")
sr = w.getframerate()
n = w.getnframes()
ch = w.getnchannels()
raw = w.readframes(n)
w.close()
x = np.frombuffer(raw, dtype=np.int16).astype(np.float32)
if ch > 1:
    x = x.reshape(-1, ch).mean(axis=1)
x /= 32768.0
dur = len(x) / sr
print(f"sr={sr} dur={dur:.1f}s")

# ---- onset envelope: 频谱通量 ----
hop = 512
win = 1024
nframes = 1 + (len(x) - win) // hop
window = np.hanning(win).astype(np.float32)
S = np.empty((nframes, win // 2 + 1), dtype=np.float32)
for i in range(nframes):
    seg = x[i * hop: i * hop + win] * window
    S[i] = np.abs(np.fft.rfft(seg))
S = np.log1p(S * 100.0)
flux = np.maximum(0.0, np.diff(S, axis=0)).sum(axis=1)
flux = np.concatenate([[0.0], flux])
env_sr = sr / hop                     # 86.13 Hz
print("env frames", len(flux), "env_sr", round(env_sr, 2))

# ---- BPM: 自相关 ----
e = flux - flux.mean()
ac = np.correlate(e, e, mode="full")[len(e) - 1:]
ac /= (ac[0] + 1e-9)
best = []
lo_lag = int(env_sr * 60 / 180.0)
hi_lag = int(env_sr * 60 / 60.0)
for lag in range(lo_lag, hi_lag):
    bpm = 60.0 * env_sr / lag
    strength = ac[lag]
    if lag * 2 < len(ac):
        strength += 0.5 * ac[lag * 2]
    best.append((strength, bpm, lag))
best.sort(reverse=True)
print("top BPM candidates:", [(round(b, 2), round(s, 4)) for s, b, l in best[:8]])

bpm = best[0][1]
# 常见做法：把结果归一到 70-160 区间
while bpm < 70:
    bpm *= 2
while bpm > 160:
    bpm /= 2
print("chosen BPM:", round(bpm, 3), "beat=", round(60 / bpm, 4), "s")

# ---- 相位：找最佳拍网格偏移 ----
period = 60.0 / bpm
env_period = period * env_sr
best_phase, best_score = 0.0, -1
for ph in np.arange(0, env_period, 0.25):
    idx = np.arange(ph, len(flux) - 1, env_period).astype(int)
    sc = flux[idx].mean()
    if sc > best_score:
        best_score, best_phase = sc, ph
phase_sec = best_phase / env_sr
print("phase(s):", round(phase_sec, 3), "score", round(best_score, 4))

beats = []
t = phase_sec
while t < dur:
    if t >= 0:
        beats.append(round(t, 4))
    t += period
print("beat count in full song:", len(beats))

# ---- 段落能量（每 0.5 s RMS）----
seg = int(sr * 0.5)
rms = np.array([np.sqrt(np.mean(x[i:i + seg] ** 2) + 1e-12)
                for i in range(0, len(x) - seg, seg)])
sm = np.convolve(rms, np.ones(8) / 8, mode="same")
sm = sm / (sm.max() + 1e-9)

# ---- 找 30 s 最高能量窗口 ----
win_len = 60          # 30 s = 60 个 0.5s 段
best_w, best_e = 0, -1
for i in range(len(sm) - win_len):
    e_ = sm[i:i + win_len].mean()
    if e_ > best_e:
        best_e, best_w = e_, i
print("best 30s window:", best_w * 0.5, "->", best_w * 0.5 + 30, "energy", round(best_e, 3))
# 第二、第三
order = np.argsort([-sm[i:i + win_len].mean() for i in range(len(sm) - win_len)])
seen = []
for i in order:
    t0 = i * 0.5
    if all(abs(t0 - s) > 40 for s in seen):
        seen.append(t0)
    if len(seen) >= 5:
        break
print("top30 windows:", [(round(t, 1), round(sm[int(t * 2):int(t * 2) + win_len].mean(), 3)) for t in seen])

json.dump({"bpm": bpm, "beat_period": period, "phase": phase_sec,
           "beats": beats, "dur": dur,
           "top30": seen}, open(r"D:\项目session\blender-supercar\pipeline\beats.json", "w"))
print("SAVED beats.json")