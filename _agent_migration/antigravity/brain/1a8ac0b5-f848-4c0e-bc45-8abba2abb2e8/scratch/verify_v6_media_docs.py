# -*- coding: utf-8 -*-
"""
Read-only V6 Spider-Verse Isolation, Stills, Poster, Clips, Audio & Docs Verification
Strictly uses PIL/NumPy + ffprobe/ffmpeg + wave/numpy + SHA256 (NEVER LLM binary read_file!).
"""
import os
import glob
import json
import wave
import hashlib
import subprocess
import numpy as np
from PIL import Image

PROJ = r"D:\项目session\blender-supercar"
SCRATCH = r"C:\Users\86052\.gemini\antigravity\brain\1a8ac0b5-f848-4c0e-bc45-8abba2abb2e8\scratch"
V5_HASH_JSON = os.path.join(SCRATCH, "v5_baseline_hashes.json")
FFMPEG = r"C:\Users\86052\scoop\shims\ffmpeg.exe"
FFPROBE = r"C:\Users\86052\scoop\shims\ffprobe.exe"
OUT_TXT = os.path.join(SCRATCH, "v6_media_docs_report.txt")

lines = []

# 1. Verify 100% V5 Isolation via SHA256 baseline + LATEST directory listing
lines.append("=== 1. V5 ISOLATION SHA256 CHECK ===")
base = json.load(open(V5_HASH_JSON, encoding="utf-8"))
v5_diffs = []
for rel, meta in base.items():
    fp = os.path.join(PROJ, rel)
    if not os.path.exists(fp):
        v5_diffs.append(f"DELETED: {rel}")
        continue
    h = hashlib.sha256()
    with open(fp, "rb") as f:
        while True:
            b = f.read(1024 * 1024)
            if not b:
                break
            h.update(b)
    if h.hexdigest() != meta["sha256"]:
        v5_diffs.append(f"MODIFIED: {rel}")
latest_files = sorted(os.listdir(os.path.join(PROJ, "LATEST")))
lines.append(f"  Checked {len(base)} V5 files -> diffs={len(v5_diffs)} ({v5_diffs})")
lines.append(f"  LATEST/ contents: {latest_files}")
lines.append("")

# 2. Check V6 Textures
lines.append("=== 2. V6 SPIDER-VERSE TEXTURES ===")
v6_tex_dir = os.path.join(PROJ, "v6_spiderverse", "textures")
if os.path.exists(v6_tex_dir):
    for fn in sorted(os.listdir(v6_tex_dir)):
        fp = os.path.join(v6_tex_dir, fn)
        if os.path.isfile(fp) and fn.lower().endswith((".png", ".jpg")):
            im = Image.open(fp).convert("RGB")
            arr = np.asarray(im, dtype=np.float32)
            lines.append(f"  {fn:<26} size={im.size} bytes={os.path.getsize(fp):>8} meanRGB={[round(float(x),1) for x in arr.mean(axis=(0,1))]}")
else:
    lines.append("  MISSING v6_spiderverse/textures!")
lines.append("")

# 3. Check V6 Stills + contact_sheet_v6.jpg + comic_page_sheet.jpg
lines.append("=== 3. V6 STILLS & COMIC PAGE POSTER ===")
stills_dir = os.path.join(PROJ, "renders_v6", "stills")
if os.path.exists(stills_dir):
    sfiles = sorted(f for f in os.listdir(stills_dir) if f.lower().endswith((".jpg", ".png")))
    lines.append(f"  Total files in renders_v6/stills: {len(sfiles)}")
    lines.append(f"  {'File':<34} {'SizePx':<14} {'Bytes':>9} {'MeanL':>6} {'P05':>5} {'P95':>5} {'SatMean':>7} {'Clip%':>6}")
    for fn in sfiles:
        fp = os.path.join(stills_dir, fn)
        im = Image.open(fp).convert("RGB")
        arr = np.asarray(im, dtype=np.float32)
        lum = 0.2126 * arr[:, :, 0] + 0.7152 * arr[:, :, 1] + 0.0722 * arr[:, :, 2]
        mx = arr.max(axis=2)
        mn = arr.min(axis=2)
        sat = np.where(mx > 1.0, (mx - mn) / np.maximum(mx, 1.0), 0.0)
        p05, p95 = [float(x) for x in np.percentile(lum, [5, 95])]
        clip_pct = float((mx >= 250).mean() * 100.0)
        lines.append(f"  {fn:<34} {str(im.size):<14} {os.path.getsize(fp):>9} {lum.mean():>6.1f} {p05:>5.1f} {p95:>5.1f} {sat.mean():>7.3f} {clip_pct:>6.2f}")
else:
    lines.append("  MISSING renders_v6/stills!")
lines.append("")

# 4. Check 3x 96-frame Showcase Clip Sequences + Impact Frame signature (f=1698..1699)
lines.append("=== 4. V6 3x 96-FRAME CLIP SEQUENCES & IMPACT FRAME CHECK ===")
CLIPS = [
    ("clip1_miles_1610", 61, 156),
    ("clip2_gwen_65", 1290, 1385),
    ("clip3_2099_impact", 1650, 1745),
]
for cname, f0, f1 in CLIPS:
    cdir = os.path.join(PROJ, "renders_v6", "clips_frames", cname)
    if not os.path.exists(cdir):
        lines.append(f"  {cname}: MISSING DIR!")
        continue
    present = [f for f in range(f0, f1 + 1) if os.path.exists(os.path.join(cdir, f"f_{f:04d}.jpg"))]
    im0 = Image.open(os.path.join(cdir, f"f_{present[0]:04d}.jpg")) if present else None
    # Check frame-to-frame difference on sample consecutive frames (confirm smooth 24fps camera vs frozen frames)
    diffs = []
    for ff in range(f0, min(f0 + 8, f1)):
        p_a = os.path.join(cdir, f"f_{ff:04d}.jpg")
        p_b = os.path.join(cdir, f"f_{ff+1:04d}.jpg")
        if os.path.exists(p_a) and os.path.exists(p_b):
            aa = np.asarray(Image.open(p_a).convert("RGB"), dtype=np.float32)
            bb = np.asarray(Image.open(p_b).convert("RGB"), dtype=np.float32)
            diffs.append(round(float(np.abs(aa - bb).mean()), 2))
    lines.append(f"  {cname:<22} expected={f1-f0+1} found={len(present)} res={im0.size if im0 else None} step_MAD_first8={diffs}")

# Check Impact Frame f=1698..1699 vs f=1695 in clip3_2099_impact
c3dir = os.path.join(PROJ, "renders_v6", "clips_frames", "clip3_2099_impact")
for ff in (1695, 1697, 1698, 1699, 1700, 1701):
    fp = os.path.join(c3dir, f"f_{ff:04d}.jpg")
    if os.path.exists(fp):
        arr = np.asarray(Image.open(fp).convert("RGB"), dtype=np.float32)
        lum = 0.2126 * arr[:, :, 0] + 0.7152 * arr[:, :, 1] + 0.0722 * arr[:, :, 2]
        bw_extreme = float(((lum < 25.0) | (lum > 220.0)).mean() * 100.0)
        lines.append(f"    ImpactCheck f={ff}: meanL={lum.mean():.1f} stdL={lum.std():.1f} extremeBW%={bw_extreme:.1f}% meanRGB={[round(float(x),1) for x in arr.mean(axis=(0,1))]}")
lines.append("")

# 5. Check V6 WAV + M4A + 4 MP4s
lines.append("=== 5. V6 AUDIO & MP4 DELIVERABLES ===")
wav_sv = os.path.join(PROJ, "renders_v6", "sfx_spiderverse_90s.wav")
if os.path.exists(wav_sv):
    with wave.open(wav_sv, "rb") as wf:
        ch, sw, sr, nf = wf.getnchannels(), wf.getsampwidth(), wf.getframerate(), wf.getnframes()
        pcm = np.frombuffer(wf.readframes(nf), dtype=np.int16).reshape(-1, ch).astype(np.float32) / 32768.0
    peak_db = 20.0 * np.log10(max(float(np.abs(pcm).max()), 1e-9))
    clipped = int((np.abs(pcm) >= 0.999).sum())
    # Check RMS around portal cuts & impact frame (70.71s)
    def win_rms_db(t_sec, w=0.18):
        i0 = max(0, int((t_sec - w/2) * sr))
        i1 = min(nf, int((t_sec + w/2) * sr))
        return round(20.0 * np.log10(max(float(np.sqrt(np.mean(pcm[i0:i1] ** 2))), 1e-9)), 2)
    lines.append(f"  sfx_spiderverse_90s.wav: {sr}Hz {sw*8}bit {ch}ch dur={nf/sr:.4f}s peak={peak_db:.2f}dBFS clipped={clipped}")
    lines.append(f"    Portal1(32.8s)={win_rms_db(32.8)}dB | Portal2(66.7s)={win_rms_db(66.7)}dB | ImpactStowe(70.71s)={win_rms_db(70.71)}dB (vs pre-impact 70.2s={win_rms_db(70.2)}dB)")
else:
    lines.append("  MISSING sfx_spiderverse_90s.wav!")

V6_MEDIA = [
    "sfx_spiderverse_90s.wav",
    "audio_v6_sv_mix_90s.m4a",
    "clip1_miles_1610.mp4",
    "clip2_gwen_65.mp4",
    "clip3_2099_impact.mp4",
    "v6_spiderverse_showcase_12s.mp4",
]
for fn in V6_MEDIA:
    fp = os.path.join(PROJ, "renders_v6", fn)
    if not os.path.exists(fp):
        lines.append(f"  {fn}: MISSING!")
        continue
    pr = subprocess.run([FFPROBE, "-v", "error", "-show_format", "-show_streams", "-of", "json", fp],
                        capture_output=True, text=True, encoding="utf-8", errors="replace")
    info = json.loads(pr.stdout) if pr.stdout else {}
    fmt = info.get("format", {})
    s_desc = []
    for st in info.get("streams", []):
        if st.get("codec_type") == "video":
            s_desc.append(f"V:{st.get('codec_name')} {st.get('width')}x{st.get('height')} r={st.get('r_frame_rate')} nb={st.get('nb_frames')}")
        elif st.get("codec_type") == "audio":
            s_desc.append(f"A:{st.get('codec_name')} {st.get('sample_rate')}Hz {st.get('channels')}ch dur={float(st.get('duration', 0)):.3f}s")
    vr = subprocess.run([FFMPEG, "-hide_banner", "-i", fp, "-vn", "-af", "volumedetect", "-f", "null", "NUL"],
                        capture_output=True, text=True, encoding="utf-8", errors="replace")
    mv = xv = "?"
    for ln in vr.stderr.splitlines():
        if "mean_volume:" in ln: mv = ln.split("mean_volume:")[1].strip()
        if "max_volume:" in ln: xv = ln.split("max_volume:")[1].strip()
    lines.append(f"  {fn:<34} size={int(fmt.get('size',0)):>9} dur={float(fmt.get('duration',0)):.4f}s | {' + '.join(s_desc)} | mean={mv}, max={xv}")
lines.append("")

# 6. Docs check
lines.append("=== 6. V6 DOCS CHECK ===")
for rel in ("README.md", "docs/README_V6_SPIDERVERSE.md", "docs/README_V5.md"):
    fp = os.path.join(PROJ, rel)
    lines.append(f"  {rel:<30} exists={os.path.exists(fp)} size={os.path.getsize(fp) if os.path.exists(fp) else 0}")

out_s = "\n".join(lines)
with open(OUT_TXT, "w", encoding="utf-8") as f:
    f.write(out_s)
print(out_s)
