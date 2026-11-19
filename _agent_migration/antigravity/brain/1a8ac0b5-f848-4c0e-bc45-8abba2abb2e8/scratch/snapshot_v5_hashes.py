# -*- coding: utf-8 -*-
"""
Snapshot SHA256 hashes & mtimes of all V5 deliverables to verify 100% V5 isolation in V6 QA.
"""
import os, glob, json, hashlib

PROJ = r"D:\项目session\blender-supercar"
SCRATCH = r"C:\Users\86052\.gemini\antigravity\brain\1a8ac0b5-f848-4c0e-bc45-8abba2abb2e8\scratch"
OUT = os.path.join(SCRATCH, "v5_baseline_hashes.json")

PATTERNS = [
    "LATEST/*",
    "pipeline/v5_*.py",
    "pipeline/gen_textures.py",
    "pipeline/render_v5.py",
    "pipeline/render_clay.py",
    "pipeline/synth_sfx.py",
    "pipeline/mux_v5.sh",
    "pipeline/mux_clay.sh",
    "textures/*",
    "docs/README_V5.md",
    "renders_v5/*.mp4",
    "renders_v5/*.m4a",
    "renders_v5/*.wav",
    "renders_v5/stills/contact_sheet.jpg",
    "renders_v5/clay_stills/contact_sheet_clay.jpg",
]

snap = {}
for pat in PATTERNS:
    for fp in sorted(glob.glob(os.path.join(PROJ, pat))):
        if os.path.isfile(fp):
            rel = os.path.relpath(fp, PROJ).replace("\\", "/")
            h = hashlib.sha256()
            with open(fp, "rb") as f:
                while True:
                    b = f.read(1024 * 1024)
                    if not b:
                        break
                    h.update(b)
            snap[rel] = {"size": os.path.getsize(fp), "sha256": h.hexdigest()}

with open(OUT, "w", encoding="utf-8") as f:
    json.dump(snap, f, indent=2, ensure_ascii=False)
print(f"Snapshotted {len(snap)} V5 files -> {OUT}")
