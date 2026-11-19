# -*- coding: utf-8 -*-
"""
Broadcast-Grade Procedural F1 Trackside Texture Generator (Pillow + NumPy)
Outputs to textures/:
  - pit_garage.png  (2048 x 512)  : 6-bay F1 team pit garages + hospitality mezzanine
  - ad_boards.png   (2048 x 256)  : 4-panel motorsport sponsor hoardings
  - bigscreen.png   (2048 x 1152) : 16:9 F1 Live Timing Tower + Silverstone Track Telemetry
  - drs_board.png   (512 x 320)   : FIA emerald-green DRS zone activation marker board
  - brake_150.png / brake_100.png / brake_50.png (512 x 320) : FIA distance marker boards
"""
import json
import math
import os
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

PROJ = r"D:\项目session\blender-supercar"
TEX_DIR = os.path.join(PROJ, "textures")
TRACK_JSON = os.path.join(PROJ, "track_data", "silverstone_track.json")
os.makedirs(TEX_DIR, exist_ok=True)


def get_font(size, mono=False):
    candidates = (
        ["consolab.ttf", "lucon.ttf", "arialbd.ttf"]
        if mono
        else ["bahnschrift.ttf", "arialbd.ttf", "segoeuib.ttf", "impact.ttf", "arial.ttf"]
    )
    font_dir = r"C:\Windows\Fonts"
    for fn in candidates:
        fp = os.path.join(font_dir, fn)
        if os.path.exists(fp):
            try:
                return ImageFont.truetype(fp, size)
            except Exception:
                continue
    return ImageFont.load_default()


def draw_centered(draw, box, text, font, fill, stroke_w=0, stroke_fill=(0, 0, 0)):
    x0, y0, x1, y1 = box
    bbox = draw.textbbox((0, 0), text, font=font, stroke_width=stroke_w)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    tx = x0 + (x1 - x0 - tw) / 2 - bbox[0]
    ty = y0 + (y1 - y0 - th) / 2 - bbox[1]
    draw.text((tx, ty), text, font=font, fill=fill, stroke_width=stroke_w, stroke_fill=stroke_fill)


# ---------------------------------------------------------------------------
# 1. pit_garage.png (2048 x 512) — 6 F1 team bays (each 341px = 6m in world)
#    Note: PIL y=0 is TOP of image -> UV v=1.0 (roof), y=H is BOTTOM -> UV v=0.0 (ground)
# ---------------------------------------------------------------------------
def build_pit_garage():
    W, H = 2048, 512
    img = Image.new("RGB", (W, H), (18, 20, 25))
    dr = ImageDraw.Draw(img)

    teams = [
        ("ORACLE RACING", "01", (16, 24, 58), (220, 28, 36), (245, 192, 18)),
        ("PETRONAS GP", "44", (26, 30, 36), (0, 198, 178), (210, 220, 230)),
        ("SCUDERIA CORSA", "16", (52, 12, 16), (228, 24, 30), (250, 218, 24)),
        ("PAPAYA AERO", "04", (28, 28, 34), (245, 122, 16), (40, 175, 245)),
        ("AMR PERFORMANCE", "14", (10, 42, 36), (0, 155, 118), (205, 235, 45)),
        ("APEX MOTORSPORT", "10", (14, 30, 62), (32, 118, 240), (235, 72, 148)),
    ]

    # Upper hospitality mezzanine (y = 0 .. 196 -> top 38% of 8m building = 3.0m VIP glass)
    dr.rectangle([0, 0, W, 196], fill=(16, 20, 28))
    # Warm interior lounge ceiling glow gradient
    arr = np.asarray(img, dtype=np.float32)
    yy = np.linspace(0.0, 1.0, 196)[:, None]
    lounge_glow = (1.0 - np.abs(yy - 0.52) * 1.55).clip(0.0, 1.0)
    arr[:196, :, 0] += lounge_glow * 78.0
    arr[:196, :, 1] += lounge_glow * 56.0
    arr[:196, :, 2] += lounge_glow * 34.0
    img = Image.fromarray(arr.clip(0, 255).astype(np.uint8))
    dr = ImageDraw.Draw(img)

    # Architectural glass mullions & balcony slab
    for mx in range(0, W, 64):
        dr.rectangle([mx, 10, mx + 4, 186], fill=(24, 28, 36))
    dr.rectangle([0, 0, W, 14], fill=(32, 35, 42))
    dr.rectangle([0, 96, W, 101], fill=(38, 44, 54))
    dr.rectangle([0, 184, W, 204], fill=(42, 46, 54))

    f_team = get_font(22)
    f_num = get_font(34)
    f_sub = get_font(15, mono=True)

    bay_w = W / len(teams)
    for i, (tname, cnum, bg_c, pri_c, sec_c) in enumerate(teams):
        x0 = int(round(i * bay_w))
        x1 = int(round((i + 1) * bay_w))
        bw = x1 - x0

        # Concrete pier columns between bays
        dr.rectangle([x0, 204, x1, H], fill=(34, 37, 43))
        pad = 14
        bx0, bx1 = x0 + pad, x1 - pad

        # Team fascia header above garage door (y = 206 .. 274)
        dr.rectangle([x0 + 4, 206, x1 - 4, 274], fill=bg_c)
        dr.rectangle([x0 + 4, 264, x1 - 4, 270], fill=pri_c)
        dr.rectangle([x0 + 4, 270, x1 - 4, 274], fill=sec_c)

        # Car number badge on left of fascia
        dr.rounded_rectangle([x0 + 14, 214, x0 + 72, 258], radius=6, fill=pri_c)
        draw_centered(dr, (x0 + 14, 214, x0 + 72, 258), cnum, f_num, (250, 250, 252))
        dr.text((x0 + 84, 220), tname, font=f_team, fill=(238, 242, 248))
        dr.text((x0 + 85, 244), "SILVERSTONE PIT BAY", font=f_sub, fill=(168, 178, 195))

        # Open garage interior (y = 278 .. H)
        dr.rectangle([bx0, 278, bx1, H], fill=(14, 16, 21))

        # Perspektive ceiling LED light-rig Planks inside garage
        for ly, inset, lum in ((288, 18, 235), (304, 34, 195), (320, 50, 150)):
            dr.rectangle([bx0 + inset, ly, bx1 - inset, ly + 6], fill=(lum, lum, min(255, int(lum * 1.04))))
        # Central overhead gantry beam
        mid_x = (bx0 + bx1) // 2
        dr.rectangle([mid_x - 24, 282, mid_x + 24, 336], fill=(28, 32, 40))
        dr.rectangle([mid_x - 18, 290, mid_x + 18, 298], fill=pri_c)

        # Back wall telemetry screens & tool cabinets
        dr.rectangle([bx0 + 36, 338, bx1 - 36, 456], fill=(24, 27, 34))
        # Left & right red/team tool cabinets
        cab_c = tuple(max(20, int(c * 0.72)) for c in pri_c)
        dr.rectangle([bx0 + 16, 376, bx0 + 78, 492], fill=cab_c)
        dr.rectangle([bx1 - 78, 376, bx1 - 16, 492], fill=cab_c)
        for dy in range(386, 484, 16):
            dr.line([(bx0 + 20, dy), (bx0 + 74, dy)], fill=(210, 215, 222), width=2)
            dr.line([(bx1 - 74, dy), (bx1 - 20, dy)], fill=(210, 215, 222), width=2)

        # Glowing telemetry monitor bank on rear wall
        for m_idx in range(3):
            mx0 = bx0 + 88 + m_idx * 48
            mx1 = mx0 + 40
            dr.rectangle([mx0, 362, mx1, 396], fill=(12, 34, 52), outline=(65, 80, 98), width=2)
            dr.line([(mx0 + 5, 386), (mx0 + 16, 374), (mx0 + 27, 380), (mx1 - 5, 368)], fill=(40, 225, 240), width=2)

        # Tire warmers stack on right side
        for ty in (428, 458):
            dr.rounded_rectangle([bx1 - 68, ty, bx1 - 24, ty + 24], radius=5, fill=(22, 22, 25), outline=sec_c, width=2)

        # Epoxy pit garage floor with reflection highlight & safety yellow threshold line
        dr.rectangle([bx0, 476, bx1, H], fill=(30, 33, 40))
        dr.rectangle([bx0 + 40, 482, bx1 - 40, 494], fill=(52, 58, 68))
        dr.rectangle([bx0, 504, bx1, H], fill=(215, 172, 24))

        # Roller-shutter side guide rails
        dr.rectangle([bx0 - 4, 276, bx0 + 3, H], fill=(70, 76, 86))
        dr.rectangle([bx1 - 3, 276, bx1 + 4, H], fill=(70, 76, 86))

    out_path = os.path.join(TEX_DIR, "pit_garage.png")
    img.save(out_path, optimize=True)
    print("Saved:", out_path, img.size)


# ---------------------------------------------------------------------------
# 2. ad_boards.png (2048 x 256) — 4 crisp sponsor hoardings (512px each)
# ---------------------------------------------------------------------------
def build_ad_boards():
    W, H = 2048, 256
    img = Image.new("RGB", (W, H), (14, 18, 24))
    dr = ImageDraw.Draw(img)

    f_big = get_font(86)
    f_med = get_font(34)
    f_tag = get_font(22, mono=True)

    panels = [
        # (bg, border, accent, title, subtitle, text_col)
        ((6, 78, 58), (0, 178, 122), (240, 248, 245), "ARAMCO", "POWERING MOTORSPORT INNOVATION", (244, 250, 248)),
        ((218, 178, 12), (208, 24, 28), (20, 20, 22), "PIRELLI", "P ZERO  •  OFFICIAL TYRE PARTNER", (18, 18, 20)),
        ((10, 58, 38), (196, 162, 62), (238, 214, 128), "ROLEX", "OFFICIAL TIMEPIECE  •  SILVERSTONE", (242, 232, 198)),
        ((158, 18, 24), (242, 242, 246), (25, 28, 36), "ORACLE", "CLOUD TELEMETRY & AI ANALYTICS", (246, 246, 248)),
    ]

    pw = W // 4
    for i, (bg, brd, acc, title, sub, tcol) in enumerate(panels):
        x0 = i * pw
        x1 = (i + 1) * pw
        dr.rectangle([x0, 0, x1 - 1, H - 1], fill=bg)
        # Top & bottom accent bars
        dr.rectangle([x0, 0, x1 - 1, 14], fill=brd)
        dr.rectangle([x0, H - 15, x1 - 1, H - 1], fill=brd)
        # Diagonal motorsport speed chevrons on left & right edges
        for dx in (18, 42):
            pts_l = [(x0 + dx, H - 22), (x0 + dx + 16, H - 22), (x0 + dx + 42, 22), (x0 + dx + 26, 22)]
            pts_r = [(x1 - dx - 42, H - 22), (x1 - dx - 26, H - 22), (x1 - dx, 22), (x1 - dx - 16, 22)]
            dr.polygon(pts_l, fill=brd)
            dr.polygon(pts_r, fill=brd)

        draw_centered(dr, (x0 + 60, 28, x1 - 60, 158), title, f_big, tcol)
        draw_centered(dr, (x0 + 50, 166, x1 - 50, 222), sub, f_tag, acc if i != 1 else (175, 18, 22))
        # Side frame divider
        dr.rectangle([x0, 0, x0 + 6, H], fill=(22, 24, 28))
        dr.rectangle([x1 - 6, 0, x1, H], fill=(22, 24, 28))

    out_path = os.path.join(TEX_DIR, "ad_boards.png")
    img.save(out_path, optimize=True)
    print("Saved:", out_path, img.size)


# ---------------------------------------------------------------------------
# 3. bigscreen.png (2048 x 1152) — Broadcast F1 Live Timing + Circuit Telemetry
# ---------------------------------------------------------------------------
def build_bigscreen():
    W, H = 2048, 1152
    img = Image.new("RGB", (W, H), (10, 14, 22))

    # Subtle dark radial broadcast background gradient on right pane
    arr = np.zeros((H, W, 3), dtype=np.float32)
    yy, xx = np.mgrid[0:H, 0:W]
    nx = (xx - W * 0.64) / (W * 0.5)
    ny = (yy - H * 0.50) / (H * 0.5)
    rad = np.sqrt(nx * nx + ny * ny)
    glow = np.clip(1.0 - rad * 0.75, 0.0, 1.0)
    arr[:, :, 0] = 10 + glow * 16
    arr[:, :, 1] = 15 + glow * 28
    arr[:, :, 2] = 26 + glow * 48
    # Fine LED matrix scanlines (subtle broadcast screen feel)
    scan = 0.94 + 0.06 * ((yy % 4) < 2).astype(np.float32)
    arr *= scan[:, :, None]
    img = Image.fromarray(arr.clip(0, 255).astype(np.uint8))
    dr = ImageDraw.Draw(img)

    # Top Championship Header Bar
    dr.rectangle([0, 0, W, 96], fill=(16, 20, 30))
    dr.rectangle([0, 90, W, 96], fill=(225, 24, 32))

    f_hdr = get_font(44)
    f_sub = get_font(28, mono=True)
    f_pos = get_font(34)
    f_drv = get_font(36)
    f_gap = get_font(30, mono=True)
    f_tel_big = get_font(84)
    f_tel_lbl = get_font(26, mono=True)

    # F1 red badge
    dr.rounded_rectangle([28, 18, 152, 76], radius=8, fill=(225, 24, 32))
    draw_centered(dr, (28, 18, 152, 76), "F1", f_hdr, (255, 255, 255))
    dr.text((176, 24), "BRITISH GRAND PRIX  •  SILVERSTONE CIRCUIT", font=f_hdr, fill=(240, 244, 250))
    dr.rounded_rectangle([W - 380, 20, W - 32, 76], radius=8, fill=(28, 36, 52), outline=(0, 215, 195), width=2)
    draw_centered(dr, (W - 380, 20, W - 32, 76), "QUALIFYING  •  Q3 LIVE", f_sub, (80, 240, 225))

    # Left Timing Tower (x = 24 .. 620, y = 120 .. 1120)
    dr.rounded_rectangle([24, 120, 624, 1124], radius=14, fill=(14, 18, 27), outline=(44, 54, 74), width=3)
    dr.rectangle([24, 120, 624, 188], fill=(24, 30, 44))
    dr.text((48, 136), "POS  DRIVER", font=f_sub, fill=(170, 184, 206))
    dr.text((410, 136), "INTERVAL", font=f_sub, fill=(170, 184, 206))

    drivers = [
        ("1", "VER", (30, 65, 215), "1:25.842", "S", (225, 32, 36), True),
        ("2", "HAM", (0, 205, 182), "+0.114", "S", (225, 32, 36), False),
        ("3", "NOR", (245, 126, 20), "+0.208", "S", (225, 32, 36), False),
        ("4", "LEC", (225, 28, 34), "+0.319", "S", (225, 32, 36), False),
        ("5", "RUS", (0, 205, 182), "+0.405", "S", (225, 32, 36), False),
        ("6", "PIA", (245, 126, 20), "+0.488", "M", (238, 198, 24), False),
        ("7", "SAI", (225, 28, 34), "+0.612", "S", (225, 32, 36), False),
        ("8", "ALO", (0, 162, 122), "+0.744", "M", (238, 198, 24), False),
        ("9", "GAS", (36, 124, 242), "+0.891", "S", (225, 32, 36), False),
        ("10", "ALB", (28, 148, 245), "+1.026", "S", (225, 32, 36), False),
    ]

    row_h = 91
    for idx, (pos, code, tcol, gap, comp, ccol, fastest) in enumerate(drivers):
        ry0 = 196 + idx * row_h
        ry1 = ry0 + row_h - 8
        bg_row = (26, 22, 46) if fastest else ((20, 25, 36) if idx % 2 == 0 else (16, 21, 31))
        dr.rounded_rectangle([38, ry0, 610, ry1], radius=8, fill=bg_row)
        # Position box
        dr.rounded_rectangle([46, ry0 + 12, 102, ry1 - 12], radius=6, fill=(34, 42, 58))
        draw_centered(dr, (46, ry0 + 12, 102, ry1 - 12), pos, f_pos, (245, 248, 252))
        # Team color stripe
        dr.rectangle([114, ry0 + 12, 124, ry1 - 12], fill=tcol)
        # Driver code
        dr.text((142, ry0 + 20), code, font=f_drv, fill=(246, 248, 252))
        # Fastest lap purple badge
        if fastest:
            dr.rounded_rectangle([244, ry0 + 22, 326, ry1 - 22], radius=6, fill=(158, 36, 218))
            draw_centered(dr, (244, ry0 + 22, 326, ry1 - 22), "PURP", get_font(22), (255, 255, 255))
        # Interval
        gcol = (205, 110, 255) if fastest else (228, 236, 246)
        dr.text((352, ry0 + 24), gap, font=f_gap, fill=gcol)
        # Tire compound circle
        cx, cy_c = 572, (ry0 + ry1) // 2
        dr.ellipse([cx - 22, cy_c - 22, cx + 22, cy_c + 22], outline=ccol, width=5, fill=(18, 20, 26))
        draw_centered(dr, (cx - 22, cy_c - 22, cx + 22, cy_c + 22), comp, get_font(24), (245, 245, 248))

    # Right Main Panel: Real Silverstone Track Map + Telemetry Gauges
    dr.rounded_rectangle([654, 120, W - 28, 846], radius=16, fill=(12, 18, 28), outline=(38, 56, 82), width=3)
    dr.text((690, 144), "LIVE CIRCUIT TRACKER  •  SECTOR TELEMETRY", font=f_sub, fill=(115, 215, 240))

    if os.path.exists(TRACK_JSON):
        pts = json.load(open(TRACK_JSON, encoding="utf-8"))["points"]
        xs = [p["xy"][0] for p in pts]
        ys = [p["xy"][1] for p in pts]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        map_x0, map_y0, map_x1, map_y1 = 740, 210, 1560, 800
        scale = min((map_x1 - map_x0) / (max_x - min_x), (map_y1 - map_y0) / (max_y - min_y)) * 0.90
        ox = (map_x0 + map_x1) / 2 - (min_x + max_x) / 2 * scale
        oy = (map_y0 + map_y1) / 2 + (min_y + max_y) / 2 * scale

        def to_px(p):
            return (ox + p["xy"][0] * scale, oy - p["xy"][1] * scale)

        # Draw dark outer outline first
        poly_all = [to_px(pts[k]) for k in range(0, len(pts), 3)]
        poly_all.append(poly_all[0])
        dr.line(poly_all, fill=(36, 50, 72), width=26, joint="curve")

        # Draw 3 colored F1 sectors (S1 Red, S2 Cyan, S3 Purple)
        n = len(poly_all) - 1
        s1 = poly_all[: n // 3 + 1]
        s2 = poly_all[n // 3 : 2 * n // 3 + 1]
        s3 = poly_all[2 * n // 3 :]
        dr.line(s1, fill=(235, 48, 56), width=12, joint="curve")
        dr.line(s2, fill=(0, 222, 235), width=12, joint="curve")
        dr.line(s3, fill=(186, 68, 248), width=12, joint="curve")

        # Car live beacon dot on Hangar Straight
        cpx, cpy = to_px(pts[int(len(pts) * 0.76)])
        dr.ellipse([cpx - 18, cpy - 18, cpx + 18, cpy + 18], fill=(255, 255, 255), outline=(0, 235, 255), width=5)

    # Sector split boxes on right side of map
    sectors = [
        ("SECTOR 1", "27.914", (235, 48, 56)),
        ("SECTOR 2", "35.602", (0, 222, 235)),
        ("SECTOR 3", "22.326", (186, 68, 248)),
    ]
    for si, (slbl, stime, scol) in enumerate(sectors):
        sy0 = 230 + si * 180
        dr.rounded_rectangle([1610, sy0, W - 64, sy0 + 148], radius=12, fill=(18, 26, 40), outline=scol, width=3)
        dr.rectangle([1610, sy0, 1624, sy0 + 148], fill=scol)
        dr.text((1648, sy0 + 22), slbl, font=f_tel_lbl, fill=(175, 190, 212))
        dr.text((1648, sy0 + 64), stime, font=get_font(54, mono=True), fill=(246, 248, 252))

    # Bottom Telemetry HUD Strip (y = 870 .. 1124)
    cards = [
        ("SPEED", "331", "KM/H", (0, 225, 238)),
        ("GEAR / RPM", "8TH", "12,140 RPM", (65, 235, 135)),
        ("DRS ZONE", "OPEN", "HANGAR STR", (45, 235, 95)),
        ("PEAK LAT G", "6.3G", "MAGGOTTS", (245, 178, 32)),
    ]
    cw = (W - 654 - 28 - 36) // 4
    for ci, (clbl, cval, cunit, ccol) in enumerate(cards):
        cx0 = 654 + ci * (cw + 12)
        cx1 = cx0 + cw
        dr.rounded_rectangle([cx0, 872, cx1, 1124], radius=14, fill=(16, 22, 34), outline=(44, 60, 86), width=3)
        dr.rectangle([cx0, 872, cx1, 884], fill=ccol)
        dr.text((cx0 + 26, 900), clbl, font=f_tel_lbl, fill=(168, 184, 208))
        dr.text((cx0 + 26, 944), cval, font=f_tel_big, fill=(248, 250, 252))
        dr.text((cx0 + 28, 1058), cunit, font=f_tel_lbl, fill=ccol)

    # Mild tone compression (* 0.86) so emission=1.15 under AgX High Contrast stays super crisp without clipping
    arr = (np.asarray(img, dtype=np.float32) * 0.86).clip(0, 255).astype(np.uint8)
    img = Image.fromarray(arr)
    out_path = os.path.join(TEX_DIR, "bigscreen.png")
    img.save(out_path, optimize=True)
    print("Saved:", out_path, img.size)


# ---------------------------------------------------------------------------
# 4. Brake Distance Boards (150 / 100 / 50) & FIA DRS Activation Board
# ---------------------------------------------------------------------------
def build_marker_boards():
    W, H = 512, 320
    f_num = get_font(176)
    f_drs = get_font(154)
    f_sub = get_font(36, mono=True)

    for label in ("150", "100", "50"):
        img = Image.new("RGB", (W, H), (228, 230, 232))
        dr = ImageDraw.Draw(img)
        dr.rectangle([10, 10, W - 11, H - 11], outline=(20, 22, 26), width=12)
        dr.rectangle([0, 0, W, 30], fill=(205, 24, 28))
        draw_centered(dr, (20, 32, W - 20, H - 18), label, f_num, (16, 18, 22))
        out_path = os.path.join(TEX_DIR, f"brake_{label}.png")
        img.save(out_path, optimize=True)
        print("Saved:", out_path, img.size)

    # FIA DRS Zone Activation Board (emerald green reflective panel + crisp white border & text)
    img = Image.new("RGB", (W, H), (8, 128, 62))
    dr = ImageDraw.Draw(img)
    dr.rectangle([12, 12, W - 13, H - 13], outline=(236, 242, 238), width=12)
    draw_centered(dr, (24, 24, W - 24, 224), "DRS", f_drs, (242, 248, 244))
    dr.rectangle([48, 232, W - 48, 290], fill=(12, 34, 22))
    draw_centered(dr, (48, 232, W - 48, 290), "DETECTION / ZONE", f_sub, (120, 245, 165))
    out_path = os.path.join(TEX_DIR, "drs_board.png")
    img.save(out_path, optimize=True)
    print("Saved:", out_path, img.size)


if __name__ == "__main__":
    build_pit_garage()
    build_ad_boards()
    build_bigscreen()
    build_marker_boards()
    print("ALL TEXTURES GENERATED SUCCESSFULLY.")
