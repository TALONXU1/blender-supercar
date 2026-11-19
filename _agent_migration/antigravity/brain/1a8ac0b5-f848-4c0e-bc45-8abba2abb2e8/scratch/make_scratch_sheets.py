# -*- coding: utf-8 -*-
"""
Build scratch contact sheet of newly rendered clay_frames (all 26 shots + extra transition frames)
ONLY writes to scratch directory!
"""
import os
from PIL import Image, ImageDraw

PROJ = r"D:\项目session\blender-supercar"
CLAY_FR = os.path.join(PROJ, "renders_v5", "clay_frames")
COLOR_FR = os.path.join(PROJ, "renders_v5", "frames")
SCRATCH = r"C:\Users\86052\.gemini\antigravity\brain\1a8ac0b5-f848-4c0e-bc45-8abba2abb2e8\scratch"
os.makedirs(SCRATCH, exist_ok=True)

SHOTS = [
    (60, "S01_RearChase"), (160, "S02_Onboard"), (250, "S03_ChaseRise"),
    (350, "S04_Hairpin"), (440, "S05_ChaseAintree"), (520, "S06_Orbit1"),
    (600, "S07_ChaseAccel"), (700, "S08_FastPan"), (760, "S09_WheelMacro"),
    (820, "S09b_ChaseFast"), (870, "S10_OrbitBrooklands"), (950, "S11_Luffield"),
    (1040, "S12_ChaseWoodcote"), (1120, "S13_WoodcoteTele"), (1200, "S14_HeliDrop"),
    (1300, "S15_OrbitCopse"), (1380, "S16_ChaseCopse"), (1470, "S17_Maggotts"),
    (1560, "S18_ChaseRise2"), (1640, "S19_Onboard3"), (1730, "S20_StoweTele"),
    (1830, "S21_OrbitStowe"), (1920, "S22_ChaseLow"), (2010, "S23_HeliReveal"),
    (2090, "S24_Club"), (2145, "S25_AerialOut"),
]

# Count clay frames and check completeness
clay_files = sorted(f for f in os.listdir(CLAY_FR) if f.endswith(".jpg")) if os.path.exists(CLAY_FR) else []
color_files = sorted(f for f in os.listdir(COLOR_FR) if f.endswith(".jpg")) if os.path.exists(COLOR_FR) else []
print(f"clay_frames count: {len(clay_files)} (first={clay_files[0] if clay_files else None}, last={clay_files[-1] if clay_files else None})")
print(f"color frames count: {len(color_files)} (first={color_files[0] if color_files else None}, last={color_files[-1] if color_files else None})")

def make_sheet(fr_dir, out_name):
    tw, th = 480, 270
    cols, rows = 4, 7
    sheet = Image.new("RGB", (cols * tw, rows * (th + 22)), (12, 12, 15))
    d = ImageDraw.Draw(sheet)
    for i, (f, name) in enumerate(SHOTS):
        p = os.path.join(fr_dir, f"f_{f:04d}.jpg")
        if not os.path.exists(p):
            continue
        im = Image.open(p).convert("RGB").resize((tw, th), Image.LANCZOS)
        x = (i % cols) * tw
        y = (i // cols) * (th + 22)
        sheet.paste(im, (x, y))
        d.text((x + 8, y + th + 4), f"{name} (f={f})", fill=(220, 225, 230))
    out_p = os.path.join(SCRATCH, out_name)
    sheet.save(out_p, quality=92)
    print("Saved sheet:", out_p, sheet.size)

make_sheet(CLAY_FR, "round1_clay_26shots.jpg")
make_sheet(COLOR_FR, "round1_color_26shots.jpg")
