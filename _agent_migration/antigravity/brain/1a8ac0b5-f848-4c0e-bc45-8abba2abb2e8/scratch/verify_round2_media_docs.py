# -*- coding: utf-8 -*-
"""
Read-only Round 2 Media (Stills, Clay Stills, Audio WAV/M4A, MP4s) & Docs Verification Suite
NEVER opens images via LLM read_file — strictly uses PIL/numpy + ffprobe/ffmpeg + wave/numpy.
"""
import os
import json
import wave
import subprocess
import numpy as np
from PIL import Image

PROJ = r"D:\项目session\blender-supercar"
SCRATCH = r"C:\Users\86052\.gemini\antigravity\brain\1a8ac0b5-f848-4c0e-bc45-8abba2abb2e8\scratch"
FFMPEG = r"C:\Users\86052\scoop\shims\ffmpeg.exe"
FFPROBE = r"C:\Users\86052\scoop\shims\ffprobe.exe"
OUT_TXT = os.path.join(SCRATCH, "round2_media_docs_report.txt")

out = []

# 1. Inspect Color Stills (renders_v5/stills/) & Clay Stills (renders_v5/clay_stills/)
def check_image_dir(title, folder):
    out.append(f"=== {title}: {folder} ===")
    if not os.path.exists(folder):
        out.append("  MISSING FOLDER!")
        return
    files = sorted(f for f in os.listdir(folder) if f.lower().endswith((".jpg", ".jpeg", ".png")))
    out.append(f"  Image count: {len(files)}")
    out.append(f"  {'File':<34} {'SizePx':<13} {'Bytes':>9} {'MeanL':>6} {'P05':>5} {'P50':>5} {'P95':>5} {'Clip%':>6} {'SkyStep':>7}")
    for fn in files:
        fp = os.path.join(folder, fn)
        sz = os.path.getsize(fp)
        im = Image.open(fp).convert("RGB")
        arr = np.asarray(im, dtype=np.float32)
        lum = 0.2126 * arr[:, :, 0] + 0.7152 * arr[:, :, 1] + 0.0722 * arr[:, :, 2]
        p05, p50, p95 = [float(x) for x in np.percentile(lum, [5, 50, 95])]
        clip_pct = float((arr.max(axis=2) >= 250).mean() * 100.0)
        top = lum[:max(2, int(lum.shape[0] * 0.22)), :]
        sky_step = float(np.abs(np.diff(top.mean(axis=1))).max())
        out.append(f"  {fn:<34} {str(im.size):<13} {sz:>9} {lum.mean():>6.1f} {p05:>5.1f} {p50:>5.1f} {p95:>5.1f} {clip_pct:>6.2f} {sky_step:>7.2f}")
    out.append("")

check_image_dir("COLOR STILLS", os.path.join(PROJ, "renders_v5", "stills"))
check_image_dir("CLAY STILLS", os.path.join(PROJ, "renders_v5", "clay_stills"))

# 2. Inspect WAV directly via wave + numpy (NaN/clipping/DC/click check/fade-out)
wav_p = os.path.join(PROJ, "renders_v5", "sfx_engine_90s.wav")
out.append("=== WAV DIRECT SIGNAL AUDIT ===")
if os.path.exists(wav_p):
    with wave.open(wav_p, "rb") as wf:
        ch = wf.getnchannels()
        sw = wf.getsampwidth()
        sr = wf.getframerate()
        nf = wf.getnframes()
        raw = wf.readframes(nf)
    pcm = np.frombuffer(raw, dtype=np.int16).reshape(-1, ch).astype(np.float32) / 32768.0
    dur = nf / float(sr)
    peak = float(np.abs(pcm).max())
    peak_db = 20.0 * np.log10(max(peak, 1e-9))
    rms_db = 20.0 * np.log10(max(float(np.sqrt(np.mean(pcm ** 2))), 1e-9))
    clipped_samples = int((np.abs(pcm) >= 0.999).sum())
    # Check max sample-to-sample jump (detect digital clicks/glitches at shot cuts)
    max_jump = float(np.abs(np.diff(pcm, axis=0)).max())
    # Check last 0.2s RMS (fade out check)
    tail_rms_db = 20.0 * np.log10(max(float(np.sqrt(np.mean(pcm[-int(sr * 0.2):] ** 2))), 1e-9))
    out.append(f"  sfx_engine_90s.wav: ch={ch} sw={sw*8}bit sr={sr}Hz frames={nf} dur={dur:.4f}s")
    out.append(f"  peak={peak:.4f} ({peak_db:.2f} dBFS) rms={rms_db:.2f} dBFS clipped_samples={clipped_samples} max_step_jump={max_jump:.4f} tail_0.2s_rms={tail_rms_db:.2f} dBFS")
else:
    out.append("  MISSING sfx_engine_90s.wav!")
out.append("")

# 3. Inspect MP4 & M4A files via ffprobe + ffmpeg volumedetect
MEDIA_FILES = [
    "f1_silverstone_clay_silent.mp4",
    "f1_silverstone_clay_1080p.mp4",
    "sfx_engine_90s.wav",
    "audio_v5_sfx_mix_90s.m4a",
    "f1_silverstone_clay_sfx_1080p.mp4",
    "f1_silverstone_lap_sfx_1080p.mp4",
    "f1_silverstone_lap_1080p.mp4",
]
out.append("=== FFPROBE & VOLUMEDETECT AUDIT ===")
for fn in MEDIA_FILES:
    fp = os.path.join(PROJ, "renders_v5", fn)
    if not os.path.exists(fp):
        out.append(f"  {fn}: MISSING!")
        continue
    pr = subprocess.run(
        [FFPROBE, "-v", "error", "-show_format", "-show_streams", "-of", "json", fp],
        capture_output=True, text=True, encoding="utf-8", errors="replace"
    )
    info = json.loads(pr.stdout) if pr.stdout else {}
    fmt = info.get("format", {})
    streams_desc = []
    has_audio = False
    for st in info.get("streams", []):
        ct = st.get("codec_type")
        if ct == "video":
            streams_desc.append(f"V:{st.get('codec_name')} {st.get('width')}x{st.get('height')} r={st.get('r_frame_rate')} nb={st.get('nb_frames')}")
        elif ct == "audio":
            has_audio = True
            streams_desc.append(f"A:{st.get('codec_name')} {st.get('sample_rate')}Hz {st.get('channels')}ch dur={float(st.get('duration', 0)):.3f}s")
    vol_str = ""
    if has_audio:
        vr = subprocess.run(
            [FFMPEG, "-hide_banner", "-i", fp, "-vn", "-af", "volumedetect", "-f", "null", "NUL"],
            capture_output=True, text=True, encoding="utf-8", errors="replace"
        )
        mean_v = max_v = "?"
        for line in vr.stderr.splitlines():
            if "mean_volume:" in line:
                mean_v = line.split("mean_volume:")[1].strip()
            elif "max_volume:" in line:
                max_v = line.split("max_volume:")[1].strip()
        vol_str = f" | mean={mean_v}, max={max_v}"
    out.append(f"  {fn:<36} size={int(fmt.get('size', 0)):>10} dur={float(fmt.get('duration', 0)):.4f}s | {' + '.join(streams_desc)}{vol_str}")
out.append("")

# 4. Docs Consistency Check
DOCS = [
    os.path.join(PROJ, "README.md"),
    os.path.join(PROJ, "LATEST", "README.txt"),
    os.path.join(PROJ, "docs", "README_V5.md"),
]
KEY_TERMS = [
    "v5_env.py", "v5_anim.py", "v5_clay.py", "v5_stills.py", "v5_viewport_fast.py",
    "synth_sfx.py", "sfx_engine_90s.wav", "f1_silverstone_lap_sfx_1080p.mp4", "f1_silverstone_clay_sfx_1080p.mp4"
]
out.append("=== DOCS CONSISTENCY CHECK ===")
for dp in DOCS:
    if not os.path.exists(dp):
        out.append(f"  MISSING DOC: {dp}")
        continue
    txt = open(dp, encoding="utf-8", errors="replace").read()
    present = [k for k in KEY_TERMS if k in txt]
    missing = [k for k in KEY_TERMS if k not in txt]
    out.append(f"  {os.path.relpath(dp, PROJ):<22} len={len(txt):>5} chars | present={len(present)}/{len(KEY_TERMS)} | missing={missing}")

report_str = "\n".join(out)
with open(OUT_TXT, "w", encoding="utf-8") as f:
    f.write(report_str)
print(report_str)
