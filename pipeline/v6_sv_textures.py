# -*- coding: utf-8 -*-
"""
V6 Spider-Verse Stylized Edition — Comic-Book & Halftone Texture Generator
Outputs to v6_spiderverse/textures/ (100% isolated from V5 textures/):
  - sv_pit_garage.png  (2048 x 512)
  - sv_ad_boards.png   (2048 x 256)
  - sv_bigscreen.png   (2048 x 1152)
  - sv_brake_150.png / sv_brake_100.png / sv_brake_50.png (512 x 320)
  - sv_drs_board.png   (512 x 320)
  - sv_paper_grain.png (1024 x 1024, tileable comic paper & print speckle)
"""
import json
import math
import os
import numpy as np
from PIL import Image, ImageDraw, ImageFont

PROJ = r"D:\项目session\blender-supercar"
OUT_DIR = os.path.join(PROJ, "v6_spiderverse", "textures")
TRACK_JSON = os.path.join(PROJ, "track_data", "silverstone_track.json")
os.makedirs(OUT_DIR, exist_ok=True)


def get_font(size, mono=False):
    candidates = (
        ["consolab.ttf", "arialbd.ttf"]
        if mono
        else ["impact.ttf", "bahnschrift.ttf", "arialbd.ttf", "segoeuib.ttf", "arial.ttf"]
    )
    fdir = r"C:\Windows\Fonts"
    for fn in candidates:
        fp = os.path.join(fdir, fn)
        if os.path.exists(fp):
            try:
                return ImageFont.truetype(fp, size)
            except Exception:
                continue
    return ImageFont.load_default()


def draw_misreg_text(draw, box, text, font, main_col, cyan_off=(-4, -2), mag_off=(4, 2), ink_w=4):
    """Spider-Verse CMYK print misregistration + bold comic ink outline typography."""
    x0, y0, x1, y1 = box
    bb = draw.textbbox((0, 0), text, font=font, stroke_width=ink_w)
    tw, th = bb[2] - bb[0], bb[3] - bb[1]
    tx = x0 + (x1 - x0 - tw) / 2 - bb[0]
    ty = y0 + (y1 - y0 - th) / 2 - bb[1]
    # Cyan & Magenta misregistered shadow plates
    draw.text((tx + cyan_off[0], ty + cyan_off[1]), text, font=font, fill=(0, 235, 255))
    draw.text((tx + mag_off[0], ty + mag_off[1]), text, font=font, fill=(255, 28, 128))
    # Crisp hand-inked dark indigo outline + main pop fill
    draw.text((tx, ty), text, font=font, fill=main_col, stroke_width=ink_w, stroke_fill=(12, 10, 26))


def apply_benday_halftone(arr, dot_pitch=14, angle_deg=22.5, strength=0.28, mask=None):
    """Vectorized rotated Ben-Day halftone dot screen overlay on an RGB float32 [0..255] array."""
    H, W, _ = arr.shape
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    th = math.radians(angle_deg)
    u = (xx * math.cos(th) - yy * math.sin(th)) / dot_pitch
    v = (xx * math.sin(th) + yy * math.cos(th)) / dot_pitch
    du = u - np.round(u)
    dv = v - np.round(v)
    dist = np.sqrt(du * du + dv * dv)
    # Vary dot radius across vertical gradient
    grad = np.linspace(0.46, 0.16, H, dtype=np.float32)[:, None]
    dots = (dist < grad).astype(np.float32)
    if mask is not None:
        dots *= mask
    # Shift halftone dots toward vibrant comic cyan/magenta/indigo contrast
    out = arr.copy()
    out[:, :, 0] = np.clip(out[:, :, 0] * (1.0 - strength * 0.65 * dots) + 18.0 * dots * strength, 0, 255)
    out[:, :, 1] = np.clip(out[:, :, 1] * (1.0 - strength * 0.40 * dots), 0, 255)
    out[:, :, 2] = np.clip(out[:, :, 2] * (1.0 - strength * 0.15 * dots) + 42.0 * dots * strength, 0, 255)
    return out


def add_crosshatch(arr, spacing=12, strength=0.22, mask=None):
    """45-degree comic pen hatching lines in shadow bands."""
    H, W, _ = arr.shape
    yy, xx = np.mgrid[0:H, 0:W]
    stripe = (((xx + yy) % spacing) < 2).astype(np.float32)
    if mask is not None:
        stripe *= mask
    return np.clip(arr * (1.0 - strength * stripe[:, :, None]), 0, 255)


# ---------------------------------------------------------------------------
# 1. sv_pit_garage.png (2048 x 512) — 6 Comic-Inked F1 Pit Bays
# ---------------------------------------------------------------------------
def build_sv_pit_garage():
    W, H = 2048, 512
    img = Image.new("RGB", (W, H), (20, 16, 42))
    dr = ImageDraw.Draw(img)

    INK = (12, 10, 24)
    # Upper mezzanine: Spider-Verse magenta/cyan/violet expressionist window blocks
    dr.rectangle([0, 0, W, 198], fill=(28, 18, 58))
    for wx in range(16, W - 16, 84):
        wcol = (0, 215, 245) if ((wx // 84) % 3 == 0) else ((248, 45, 138) if ((wx // 84) % 3 == 1) else (255, 196, 36))
        dr.rectangle([wx, 22, wx + 66, 174], fill=wcol, outline=INK, width=5)
        # Diagonal comic glass reflection slash
        dr.polygon([(wx + 8, 168), (wx + 24, 168), (wx + 56, 28), (wx + 40, 28)], fill=(255, 252, 245))
    dr.rectangle([0, 182, W, 204], fill=INK)
    dr.rectangle([0, 188, W, 198], fill=(0, 232, 255))

    teams = [
        ("APEX VORTEX", "01", (235, 26, 74), (0, 228, 255), (255, 214, 28)),
        ("NEON TURBO", "44", (0, 198, 212), (255, 42, 146), (248, 248, 252)),
        ("CRIMSON GP", "16", (245, 52, 36), (255, 218, 24), (0, 228, 255)),
        ("SOLAR PULSE", "04", (255, 138, 18), (38, 196, 255), (255, 42, 138)),
        ("HYPER ION", "14", (18, 188, 132), (222, 248, 42), (255, 52, 145)),
        ("NOVA CORSA", "10", (68, 82, 248), (255, 56, 156), (0, 238, 255)),
    ]
    f_num = get_font(42)
    f_team = get_font(30)

    bay_w = W / len(teams)
    for i, (tname, cnum, c1, c2, c3) in enumerate(teams):
        x0 = int(round(i * bay_w))
        x1 = int(round((i + 1) * bay_w))
        # Structural comic inked pillar
        dr.rectangle([x0, 204, x1, H], fill=(34, 28, 64), outline=INK, width=6)
        # Bold team fascia with diagonal speed slashes
        dr.rectangle([x0 + 8, 210, x1 - 8, 280], fill=c1, outline=INK, width=5)
        dr.polygon([(x1 - 92, 210), (x1 - 56, 210), (x1 - 80, 280), (x1 - 116, 280)], fill=c2)
        dr.polygon([(x1 - 48, 210), (x1 - 20, 210), (x1 - 44, 280), (x1 - 72, 280)], fill=c3)
        dr.rectangle([x0 + 16, 218, x0 + 78, 272], fill=(18, 14, 36), outline=c3, width=4)
        draw_misreg_text(dr, (x0 + 16, 218, x0 + 78, 272), cnum, f_num, (255, 255, 255), (-2, -1), (2, 1), ink_w=3)
        dr.text((x0 + 90, 226), tname, font=f_team, fill=(255, 255, 255), stroke_width=4, stroke_fill=INK)

        # Open stylized garage interior
        bx0, bx1 = x0 + 18, x1 - 18
        dr.rectangle([bx0, 286, bx1, H - 6], fill=(16, 14, 34), outline=INK, width=6)
        # Bold graphic overhead light bars
        for ly, inset, col_l in ((298, 16, (255, 252, 235)), (318, 36, c2), (336, 56, c3)):
            dr.rectangle([bx0 + inset, ly, bx1 - inset, ly + 10], fill=col_l, outline=INK, width=2)
        # Stylized comic tool chests & telemetry screens
        dr.rectangle([bx0 + 14, 382, bx0 + 82, 492], fill=c1, outline=INK, width=4)
        dr.rectangle([bx1 - 82, 382, bx1 - 14, 492], fill=c1, outline=INK, width=4)
        dr.rectangle([bx0 + 96, 364, bx1 - 96, 430], fill=(18, 36, 68), outline=c2, width=4)
        dr.line([(bx0 + 106, 414), (bx0 + 138, 382), (bx0 + 172, 404), (bx1 - 108, 376)], fill=(0, 245, 255), width=5)
        # Hazard chevron floor strip
        dr.rectangle([bx0 + 4, 490, bx1 - 4, H - 8], fill=c3, outline=INK, width=3)

    arr = np.asarray(img, dtype=np.float32)
    arr = apply_benday_halftone(arr, dot_pitch=12, angle_deg=18.0, strength=0.26)
    sh_mask = np.zeros((H, W), dtype=np.float32)
    sh_mask[280:, :] = 1.0
    arr = add_crosshatch(arr, spacing=11, strength=0.18, mask=sh_mask)
    out_p = os.path.join(OUT_DIR, "sv_pit_garage.png")
    Image.fromarray(arr.astype(np.uint8)).save(out_p, optimize=True)
    print("Saved:", out_p)


# ---------------------------------------------------------------------------
# 2. sv_ad_boards.png (2048 x 256) — 4 Pop-Art Comic F1 Hoardings
# ---------------------------------------------------------------------------
def build_sv_ad_boards():
    W, H = 2048, 256
    img = Image.new("RGB", (W, H), (14, 12, 28))
    dr = ImageDraw.Draw(img)
    INK = (12, 10, 24)
    f_big = get_font(96)
    f_sub = get_font(28, mono=True)

    boards = [
        ((238, 24, 82), (0, 235, 255), (255, 232, 36), "APEX GP", "SILVERSTONE GRAND PRIX"),
        ((255, 206, 18), (242, 24, 78), (18, 16, 38), "HYPER ZERO", "SLICK COMPOUND RACING"),
        ((0, 198, 224), (255, 42, 148), (255, 255, 255), "CHRONO V6", "OFFICIAL SPLIT TIMING"),
        ((92, 34, 218), (0, 242, 215), (255, 218, 38), "TURBO AERO", "GROUND EFFECT TELEMETRY"),
    ]
    pw = W // 4
    for i, (bg, slash_c, txt_c, title, sub) in enumerate(boards):
        x0, x1 = i * pw, (i + 1) * pw
        dr.rectangle([x0 + 4, 4, x1 - 5, H - 5], fill=bg, outline=INK, width=10)
        # Bold comic speed slashes
        for dx in (24, 62):
            pts = [(x0 + dx, H - 14), (x0 + dx + 26, H - 14), (x0 + dx + 68, 14), (x0 + dx + 42, 14)]
            dr.polygon(pts, fill=slash_c, outline=INK)
            pts2 = [(x1 - dx - 68, H - 14), (x1 - dx - 42, H - 14), (x1 - dx, 14), (x1 - dx - 26, 14)]
            dr.polygon(pts2, fill=slash_c, outline=INK)
        draw_misreg_text(dr, (x0 + 70, 20, x1 - 70, 164), title, f_big, txt_c, (-4, -2), (4, 2), ink_w=6)
        dr.rectangle([x0 + 84, 174, x1 - 84, 232], fill=INK)
        dr.text((x0 + 104, 184), sub, font=f_sub, fill=(255, 248, 240))

    arr = apply_benday_halftone(np.asarray(img, dtype=np.float32), dot_pitch=10, angle_deg=26.0, strength=0.25)
    out_p = os.path.join(OUT_DIR, "sv_ad_boards.png")
    Image.fromarray(arr.astype(np.uint8)).save(out_p, optimize=True)
    print("Saved:", out_p)


# ---------------------------------------------------------------------------
# 3. sv_bigscreen.png (2048 x 1152) — Comic-Inked F1 Telemetry & Circuit Screen
# ---------------------------------------------------------------------------
def build_sv_bigscreen():
    W, H = 2048, 1152
    img = Image.new("RGB", (W, H), (18, 14, 42))
    dr = ImageDraw.Draw(img)
    INK = (10, 8, 22)

    # Diagonal Spider-Verse comic panels with white/inked gutters
    dr.polygon([(20, 20), (W - 20, 20), (W - 20, 116), (20, 116)], fill=(238, 24, 86), outline=INK, width=8)
    draw_misreg_text(dr, (40, 24, W - 40, 112), "SILVERSTONE GP  //  LAP 52 LIVE TELEMETRY", get_font(56), (255, 252, 240), (-4, -2), (4, 2), ink_w=5)

    # Left slanted leaderboard panel
    dr.polygon([(24, 140), (636, 140), (604, H - 24), (24, H - 24)], fill=(26, 20, 58), outline=INK, width=8)
    dr.line([(24, 140), (636, 140), (604, H - 24), (24, H - 24), (24, 140)], fill=(0, 235, 255), width=4)

    rows = [
        ("01", "VER", "1:25.84", (255, 38, 118)),
        ("02", "HAM", "+0.114", (0, 232, 245)),
        ("03", "NOR", "+0.208", (255, 152, 24)),
        ("04", "LEC", "+0.319", (255, 58, 52)),
        ("05", "RUS", "+0.405", (0, 232, 245)),
        ("06", "PIA", "+0.488", (255, 152, 24)),
        ("07", "SAI", "+0.612", (255, 58, 52)),
        ("08", "ALO", "+0.744", (42, 238, 148)),
    ]
    f_row = get_font(42)
    f_gap = get_font(36, mono=True)
    for idx, (rk, cd, gp, rcol) in enumerate(rows):
        y0 = 168 + idx * 116
        dr.polygon([(46, y0), (596 - idx * 3, y0), (586 - idx * 3, y0 + 96), (46, y0 + 96)],
                   fill=(36, 28, 76), outline=INK, width=5)
        dr.rectangle([46, y0, 124, y0 + 96], fill=rcol, outline=INK, width=4)
        draw_misreg_text(dr, (46, y0, 124, y0 + 96), rk, f_row, (255, 255, 255), (-2, -1), (2, 1), ink_w=3)
        dr.text((146, y0 + 22), cd, font=f_row, fill=(255, 252, 245), stroke_width=4, stroke_fill=INK)
        dr.text((326, y0 + 26), gp, font=f_gap, fill=(0, 242, 255), stroke_width=3, stroke_fill=INK)

    # Right circuit & speed panel
    dr.polygon([(666, 140), (W - 24, 140), (W - 24, 836), (642, 836)], fill=(22, 18, 52), outline=INK, width=8)
    if os.path.exists(TRACK_JSON):
        pts = json.load(open(TRACK_JSON, encoding="utf-8"))["points"]
        xs = [p["xy"][0] for p in pts]
        ys = [p["xy"][1] for p in pts]
        mnx, mxx, mny, mxy = min(xs), max(xs), min(ys), max(ys)
        sc = min(980.0 / (mxx - mnx), 600.0 / (mxy - mny)) * 0.88
        ox = 1320 - (mnx + mxx) * 0.5 * sc
        oy = 492 + (mny + mxy) * 0.5 * sc
        poly = [(ox + pts[k]["xy"][0] * sc, oy - pts[k]["xy"][1] * sc) for k in range(0, len(pts), 3)]
        poly.append(poly[0])
        # Misregistered cyan/magenta/ink circuit trace!
        dr.line([(x - 6, y - 4) for x, y in poly], fill=(0, 238, 255), width=22, joint="curve")
        dr.line([(x + 6, y + 4) for x, y in poly], fill=(255, 32, 138), width=22, joint="curve")
        dr.line(poly, fill=INK, width=28, joint="curve")
        dr.line(poly, fill=(255, 232, 42), width=12, joint="curve")

    # Bottom Pop-Art Speed Cards
    cards = [("331 KM/H", "V-MAX", (0, 232, 255)), ("GEAR 8", "12,400 RPM", (255, 42, 138)), ("6.4 G", "APEX LOAD", (255, 214, 28))]
    cw = (W - 660 - 48) // 3
    for ci, (big_v, lbl_v, ccol) in enumerate(cards):
        cx0 = 648 + ci * (cw + 14)
        cx1 = cx0 + cw
        dr.rectangle([cx0, 862, cx1, H - 24], fill=ccol, outline=INK, width=8)
        draw_misreg_text(dr, (cx0 + 12, 876, cx1 - 12, 1024), big_v, get_font(82), (255, 255, 255), (-4, -2), (4, 2), ink_w=6)
        dr.rectangle([cx0 + 24, 1034, cx1 - 24, H - 40], fill=INK)
        draw_misreg_text(dr, (cx0 + 24, 1034, cx1 - 24, H - 40), lbl_v, get_font(34), ccol, (0, 0), (0, 0), ink_w=1)

    arr = apply_benday_halftone(np.asarray(img, dtype=np.float32) * 0.90, dot_pitch=14, angle_deg=20.0, strength=0.24)
    out_p = os.path.join(OUT_DIR, "sv_bigscreen.png")
    Image.fromarray(arr.astype(np.uint8)).save(out_p, optimize=True)
    print("Saved:", out_p)


# ---------------------------------------------------------------------------
# 4. Brake Boards (150/100/50), DRS Board, and Seamless Comic Paper Grain
# ---------------------------------------------------------------------------
def build_sv_markers_and_paper():
    W, H = 512, 320
    INK = (10, 8, 22)
    f_num = get_font(184)
    f_drs = get_font(162)

    for lbl in ("150", "100", "50"):
        img = Image.new("RGB", (W, H), (252, 244, 222))
        dr = ImageDraw.Draw(img)
        dr.rectangle([8, 8, W - 9, H - 9], outline=INK, width=16)
        dr.polygon([(8, 8), (W - 8, 8), (W - 8, 64), (8, 42)], fill=(245, 28, 88), outline=INK)
        draw_misreg_text(dr, (20, 48, W - 20, H - 16), lbl, f_num, (22, 18, 42), (-5, -3), (5, 3), ink_w=6)
        arr = apply_benday_halftone(np.asarray(img, dtype=np.float32), dot_pitch=10, angle_deg=15.0, strength=0.18)
        out_p = os.path.join(OUT_DIR, f"sv_brake_{lbl}.png")
        Image.fromarray(arr.astype(np.uint8)).save(out_p, optimize=True)
        print("Saved:", out_p)

    # DRS Board
    img = Image.new("RGB", (W, H), (0, 212, 136))
    dr = ImageDraw.Draw(img)
    dr.rectangle([8, 8, W - 9, H - 9], outline=INK, width=16)
    dr.polygon([(24, H - 20), (84, H - 20), (144, 20), (84, 20)], fill=(0, 245, 255))
    draw_misreg_text(dr, (20, 18, W - 20, 232), "DRS", f_drs, (255, 255, 255), (-5, -3), (5, 3), ink_w=8)
    dr.rectangle([38, 236, W - 38, 294], fill=INK)
    draw_misreg_text(dr, (38, 236, W - 38, 294), "ZONE ACTIVE", get_font(40), (255, 232, 38), (0, 0), (0, 0), ink_w=2)
    arr = apply_benday_halftone(np.asarray(img, dtype=np.float32), dot_pitch=10, angle_deg=22.0, strength=0.22)
    out_p = os.path.join(OUT_DIR, "sv_drs_board.png")
    Image.fromarray(arr.astype(np.uint8)).save(out_p, optimize=True)
    print("Saved:", out_p)

    # Seamless 1024x1024 Comic Print Paper Fiber + Micro Halftone Grain (neutral ~0.50 centered for overlay)
    PW = 1024
    rng = np.random.default_rng(2099)
    yy, xx = np.mgrid[0:PW, 0:PW].astype(np.float32)
    # Periodic linen/paper weave + multi-octave print speckle (strictly periodic so 100% tileable!)
    weave_x = np.sin(2 * math.pi * xx / 8.0) * 0.25 + np.sin(2 * math.pi * (xx + yy * 0.5) / 21.0) * 0.25
    weave_y = np.cos(2 * math.pi * yy / 9.0) * 0.25 + np.cos(2 * math.pi * (yy - xx * 0.5) / 19.0) * 0.25
    fine = rng.normal(0.0, 0.08, (PW, PW)).astype(np.float32)
    # Diagonal comic ink tooth
    tooth = (((xx * 0.866 + yy * 0.5) % 6.0) < 2.2).astype(np.float32) * 0.06 - 0.03
    val = np.clip(0.52 + 0.07 * (weave_x + weave_y) + fine + tooth, 0.15, 0.88)
    # Warm vintage comic newsprint tint
    paper = np.stack([
        val * 255.0 * 1.03,
        val * 255.0 * 1.00,
        val * 255.0 * 0.94,
    ], axis=-1).clip(0, 255).astype(np.uint8)
    out_p = os.path.join(OUT_DIR, "sv_paper_grain.png")
    Image.fromarray(paper).save(out_p, optimize=True)
    print("Saved:", out_p)


# ---------------------------------------------------------------------------
# 5. sv_skyscraper_facade.png (1024 x 2048) & sv_neon_signs.png (1024 x 2048)
#    Nueva York 2099 x Neo-Monaco Comic Skyscraper Windows & Vertical Neon Signs
# ---------------------------------------------------------------------------
def build_sv_city_textures():
    # A) Skyscraper Facade (1024 x 2048): dark obsidian-indigo comic glass + glowing halftone rooms
    W, H = 1024, 2048
    img = Image.new("RGB", (W, H), (8, 8, 20))
    dr = ImageDraw.Draw(img)
    INK = (4, 4, 12)
    rng = np.random.default_rng(1610)

    cols, rows = 16, 48
    cw, ch = W // cols, H // rows
    palette = [
        (0, 232, 255),    # Electric Cyan
        (255, 34, 132),   # Spider-Verse Hot Magenta
        (255, 196, 38),   # Warm Comic Gold
        (132, 56, 255),   # 2099 Ultraviolet
        (255, 78, 54),    # Coral Crimson
        (220, 245, 255),  # Crisp White Studio
    ]
    for r in range(rows):
        # Mechanical dark setback floors every 12 stories with neon trim band
        if r % 12 == 0:
            dr.rectangle([0, r * ch, W, (r + 1) * ch], fill=(12, 10, 28), outline=INK, width=4)
            trim_c = (0, 238, 255) if (r // 12) % 2 == 0 else (255, 28, 118)
            dr.rectangle([0, r * ch + 6, W, r * ch + 16], fill=trim_c)
            continue
        for c in range(cols):
            x0, y0 = c * cw + 6, r * ch + 5
            x1, y1 = (c + 1) * cw - 6, (r + 1) * ch - 5
            roll = rng.random()
            if roll < 0.34:
                wcol = palette[int(rng.integers(0, len(palette)))]
                if rng.random() < 0.45:
                    wcol = tuple(int(v * 0.58) for v in wcol)
                dr.rectangle([x0, y0, x1, y1], fill=wcol, outline=INK, width=3)
                # Comic diagonal window blind / reflection slash
                if rng.random() < 0.35:
                    dr.line([(x0 + 4, y1 - 4), (x1 - 4, y0 + 4)], fill=(255, 255, 255), width=3)
            else:
                dr.rectangle([x0, y0, x1, y1], fill=(14, 16, 36), outline=INK, width=2)

    # Bold vertical architectural comic ribs
    for x_rib in range(0, W + 1, 256):
        dr.rectangle([max(0, x_rib - 8), 0, min(W, x_rib + 8), H], fill=(16, 18, 40), outline=INK, width=3)

    arr = apply_benday_halftone(np.asarray(img, dtype=np.float32), dot_pitch=10, angle_deg=22.5, strength=0.26)
    out_fac = os.path.join(OUT_DIR, "sv_skyscraper_facade.png")
    Image.fromarray(arr.astype(np.uint8)).save(out_fac, optimize=True)
    print("Saved:", out_fac)

    # B) Vertical Cyber-Comic Neon Signs Atlas (1024 x 2048 — 4 vertical columns of 256px each)
    SW, SH = 1024, 2048
    simg = Image.new("RGB", (SW, SH), (8, 6, 18))
    sdr = ImageDraw.Draw(simg)
    signs = [
        ((245, 18, 86), (0, 242, 255), (255, 238, 48), ["A", "P", "E", "X", "//", "99"]),
        ((0, 212, 248), (255, 36, 142), (255, 255, 255), ["S", "K", "Y", "//", "G", "P"]),
        ((118, 28, 248), (0, 248, 212), (255, 208, 32), ["N", "E", "O", "//", "V", "6"]),
        ((255, 132, 16), (255, 24, 96), (255, 252, 240), ["M", "A", "X", "//", "G", "T"]),
    ]
    f_vert = get_font(168)
    col_w = SW // 4
    for idx, (bg_c, brd_c, fg_c, chars) in enumerate(signs):
        x0, x1 = idx * col_w + 10, (idx + 1) * col_w - 10
        sdr.rectangle([x0, 16, x1, SH - 16], fill=(16, 12, 34), outline=brd_c, width=10)
        sdr.rectangle([x0 + 14, 34, x1 - 14, 156], fill=bg_c, outline=INK, width=6)
        step_y = (SH - 240) // len(chars)
        for ci, ch_txt in enumerate(chars):
            cy0 = 190 + ci * step_y
            cy1 = cy0 + step_y - 24
            sdr.rounded_rectangle([x0 + 18, cy0, x1 - 18, cy1], radius=16, fill=bg_c if ci % 2 == 0 else (22, 18, 48), outline=brd_c, width=5)
            draw_misreg_text(sdr, (x0 + 18, cy0, x1 - 18, cy1), ch_txt, f_vert, fg_c, (-5, -3), (5, 3), ink_w=6)

    sarr = apply_benday_halftone(np.asarray(simg, dtype=np.float32), dot_pitch=12, angle_deg=18.0, strength=0.22)
    out_sgn = os.path.join(OUT_DIR, "sv_neon_signs.png")
    Image.fromarray(sarr.astype(np.uint8)).save(out_sgn, optimize=True)
    print("Saved:", out_sgn)


if __name__ == "__main__":
    build_sv_pit_garage()
    build_sv_ad_boards()
    build_sv_bigscreen()
    build_sv_markers_and_paper()
    build_sv_city_textures()
    print("V6 SPIDER-VERSE TEXTURES COMPLETE.")
