# -*- coding: utf-8 -*-
"""
V6 SPIDER-VERSE STILLS & COMIC-BOOK MULTI-PANEL PAGE POSTER GENERATOR
Neo-Monaco x Nueva York 2099 Sky-Harbor 3D Mega-Circuit Edition (1,281f / 24 Shots)

输入: v6_spiderverse/v6_stage_anim_sv.blend
输出:
  - renders_v6/stills/shot_01_*.jpg .. shot_24_*.jpg  (24 张 1080p 2.39:1 风格化大片剧照)
  - renders_v6/stills/contact_sheet_v6.jpg            (6x4 三幕平行宇宙色标总览图)
  - renders_v6/stills/comic_page_sheet.jpg            (蜘蛛侠平行宇宙斜切分镜漫画海报页)

用法:
  blender -b -t 8 -P pipeline/v6_sv_stills.py -- --render
  python pipeline/v6_sv_stills.py --sheet-only
"""
import glob
import math
import os
import subprocess
import sys

PROJ = r"D:\项目session\blender-supercar"
BLEND_DEFAULT = os.path.join(PROJ, "v6_spiderverse", "v6_stage_anim_sv.blend")
OUT = os.path.join(PROJ, "renders_v6", "stills")
os.makedirs(OUT, exist_ok=True)

ARGV = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
DO_RENDER = "--render" in ARGV
SHEET_ONLY = "--sheet-only" in ARGV

SHOTS = [
    (28,   "01_canyon_fpv_drop"),
    (82,   "02_scraper_front_wing"),
    (128,  "03_chicane_whip_pan"),
    (188,  "04_halo_cockpit_canyon"),
    (248,  "05_viaduct_fov_warp"),
    (282,  "06_eau_rouge_sparks"),
    (348,  "07_raidillon_sky_climb"),
    (406,  "08_moon_crest_tele300"),
    (456,  "09_bridge_pylon_reveal"),
    (508,  "10_cable_stay_side"),
    (568,  "11_bridge_deck_pursuit"),
    (635,  "12_banked_wall_rail"),
    (695,  "13_bowl_whip_orbit"),
    (755,  "14_corkscrew_crest_dive"),
    (815,  "15_corkscrew_plunge_pov"),
    (868,  "16_bottom_out_sparks"),
    (922,  "17_tunnel_portal_warp"),
    (975,  "18_tunnel_cockpit_strobe"),
    (1022, "19_tunnel_whip_orbit180"),
    (1058, "20_harbor_brake_slam"),
    (1132, "21_hairpin_wheel_macro"),
    (1175, "22_harbor_launch_chase"),
    (1222, "23_wet_mirror_skyline"),
    (1262, "24_finish_gantry_rise"),
]


def act_info(frame):
    if frame <= 427:
        return "E-1610", (235, 42, 78)     # Miles Crimson
    elif frame <= 894:
        return "E-65", (36, 214, 198)      # Gwen Teal-Aqua
    return "E-928", (188, 72, 255)         # 2099 Ultraviolet


def render_with_blender():
    import bpy
    if not bpy.data.filepath or "v6_stage_anim_sv" not in os.path.basename(bpy.data.filepath):
        bpy.ops.wm.open_mainfile(filepath=BLEND_DEFAULT)
    sc = bpy.context.scene

    # Remove stale shot_*.jpg or _impact_*.jpg from previous drafts so only the 24 Sky-Harbor stills remain
    expected = {f"shot_{name}.jpg" for _, name in SHOTS} | {"_impact_f1067.jpg"}
    for old_p in glob.glob(os.path.join(OUT, "shot_*.jpg")) + glob.glob(os.path.join(OUT, "_impact_*.jpg")):
        if os.path.basename(old_p) not in expected:
            try:
                os.remove(old_p)
            except OSError:
                pass

    markers = sorted(sc.timeline_markers, key=lambda m: m.frame)

    def active_cam_for_frame(f):
        cur = sc.camera
        for mk in markers:
            if mk.frame <= f and mk.camera:
                cur = mk.camera
            elif mk.frame > f:
                break
        return cur

    orig_cam = sc.camera
    sc.render.engine = 'BLENDER_EEVEE'
    sc.eevee.use_raytracing = True
    if hasattr(sc.eevee, "ray_tracing_method"):
        sc.eevee.ray_tracing_method = 'SCREEN'
    if hasattr(sc.eevee, "ray_tracing_options"):
        sc.eevee.ray_tracing_options.resolution_scale = '2'
        sc.eevee.ray_tracing_options.trace_max_roughness = 0.55
    if hasattr(sc.eevee, "shadow_pool_size"):
        sc.eevee.shadow_pool_size = '1024'
    if hasattr(sc.render, "compositor_device"):
        sc.render.compositor_device = 'CPU'
    if hasattr(sc.render, "compositor_precision"):
        sc.render.compositor_precision = 'FULL'
    if hasattr(sc.render, "use_compositor_frames_cache"):
        sc.render.use_compositor_frames_cache = False
    if sc.view_layers:
        sc.view_layers[0].use_pass_emit = False
        if hasattr(sc.view_layers[0], "pass_cryptomatte_depth"):
            sc.view_layers[0].pass_cryptomatte_depth = 6
    sc.eevee.taa_render_samples = 20
    sc.render.resolution_x = 1920
    sc.render.resolution_y = 1080
    sc.render.resolution_percentage = 100
    sc.render.use_motion_blur = True
    sc.render.motion_blur_shutter = 0.07
    sc.render.image_settings.file_format = 'JPEG'
    sc.render.image_settings.quality = 95

    blend_mtime = os.path.getmtime(BLEND_DEFAULT) if os.path.exists(BLEND_DEFAULT) else 0.0
    for f, name in SHOTS:
        dst = os.path.join(OUT, f"shot_{name}.jpg")
        if os.path.exists(dst) and os.path.getmtime(dst) >= blend_mtime and os.path.getsize(dst) > 25000:
            print(f"V6 STILL UP-TO-DATE: shot_{name}.jpg", flush=True)
            continue
        sc.camera = active_cam_for_frame(f)
        sc.frame_set(f)
        sc.render.filepath = dst
        bpy.ops.render.render(write_still=True)
        print(f"V6 STILL RENDERED: shot_{name}.jpg (f={f}, {act_info(f)[0]})", flush=True)

    # Ensure Impact Frame f=1067 preview exists for the comic page action inset
    clip_impact = os.path.join(PROJ, "renders_v6", "clips_frames", "clip3_2099_impact", "f_1067.jpg")
    aux_impact = os.path.join(OUT, "_impact_f1067.jpg")
    if not os.path.exists(clip_impact):
        sc.camera = active_cam_for_frame(1067)
        sc.frame_set(1067)
        sc.render.filepath = aux_impact
        bpy.ops.render.render(write_still=True)
        print("V6 IMPACT INSET RENDERED: _impact_f1067.jpg", flush=True)

    sc.camera = orig_cam


def _load_fonts():
    from PIL import ImageFont
    f_small = f_med = f_big = f_hero = None
    bold_candidates = (
        r"C:\Windows\Fonts\impact.ttf",
        r"C:\Windows\Fonts\arialbd.ttf",
        r"C:\Windows\Fonts\consolab.ttf",
    )
    mono_candidates = (
        r"C:\Windows\Fonts\consolab.ttf",
        r"C:\Windows\Fonts\arialbd.ttf",
    )
    for c in mono_candidates:
        if os.path.exists(c):
            try:
                f_small = ImageFont.truetype(c, 13)
                f_med = ImageFont.truetype(c, 18)
                break
            except Exception:
                pass
    for c in bold_candidates:
        if os.path.exists(c):
            try:
                f_big = ImageFont.truetype(c, 28)
                f_hero = ImageFont.truetype(c, 54)
                break
            except Exception:
                pass
    return f_small, f_med, f_big, f_hero


def build_contact_sheet_v6(made):
    from PIL import Image, ImageDraw

    f_small, f_med, _, _ = _load_fonts()
    tw, th = 384, 216
    bar_h = 26
    cols = 6
    rows = (len(made) + cols - 1) // cols
    header_h = 48
    W_tot = cols * tw
    sheet = Image.new("RGB", (W_tot, header_h + rows * (th + bar_h)), (12, 11, 20))
    d = ImageDraw.Draw(sheet)

    # Top multiverse accent stripe
    d.rectangle([0, 0, W_tot // 3, 5], fill=(235, 42, 78))
    d.rectangle([W_tot // 3, 0, (2 * W_tot) // 3, 5], fill=(36, 214, 198))
    d.rectangle([(2 * W_tot) // 3, 0, W_tot, 5], fill=(188, 72, 255))
    d.text(
        (16, 14),
        "V6 SPIDER-VERSE SKY-HARBOR 2099  //  24-SHOT 3D MEGA-CIRCUIT COLOR SCRIPT  (E-1610 MILES | E-65 GWEN | E-928 2099)",
        fill=(244, 242, 250),
        font=f_med or f_small,
    )

    for i, (f, name, path) in enumerate(made):
        im = Image.open(path).convert("RGB").resize((tw, th), Image.Resampling.LANCZOS)
        x = (i % cols) * tw
        y = header_h + (i // cols) * (th + bar_h)
        sheet.paste(im, (x, y))
        tag, badge_col = act_info(f)
        d.rectangle([x, y + th, x + tw - 1, y + th + bar_h - 1], fill=(18, 17, 28))
        d.rectangle([x + 6, y + th + 5, x + 64, y + th + bar_h - 5], fill=badge_col)
        d.text((x + 11, y + th + 6), tag, fill=(12, 12, 18), font=f_small)
        d.text((x + 72, y + th + 6), f"{name} (f{f})", fill=(228, 232, 242), font=f_small)
        d.rectangle([x, y, x + tw - 1, y + th + bar_h - 1], outline=(42, 40, 58), width=1)

    out_path = os.path.join(OUT, "contact_sheet_v6.jpg")
    sheet.save(out_path, quality=95, subsampling=0)
    print("V6 CONTACT SHEET:", out_path, sheet.size)


def _paste_polygon_panel(page, img_path, poly, shadow_col=(24, 210, 230), shadow_off=(10, 10), border_w=7):
    from PIL import Image, ImageDraw

    xs = [p[0] for p in poly]
    ys = [p[1] for p in poly]
    x0, y0, x1, y1 = min(xs), min(ys), max(xs), max(ys)
    bw, bh = max(1, x1 - x0), max(1, y1 - y0)

    src = Image.open(img_path).convert("RGB")
    sw, sh = src.size
    # Strip 2.39:1 letterbox bars (138px top & bottom on 1920x1080) so comic panels bleed edge-to-edge
    if sh == 1080 and sw == 1920:
        src = src.crop((0, 138, sw, sh - 138))
        sw, sh = src.size

    scale = max(bw / sw, bh / sh) * 1.03
    nw, nh = int(round(sw * scale)), int(round(sh * scale))
    resized = src.resize((nw, nh), Image.Resampling.LANCZOS)
    cx = (nw - bw) // 2
    cy = (nh - bh) // 2
    cropped = resized.crop((cx, cy, cx + bw, cy + bh))

    mask = Image.new("L", (bw, bh), 0)
    md = ImageDraw.Draw(mask)
    local_poly = [(px - x0, py - y0) for px, py in poly]
    md.polygon(local_poly, fill=255)

    d = ImageDraw.Draw(page)
    sh_poly = [(px + shadow_off[0], py + shadow_off[1]) for px, py in poly]
    d.polygon(sh_poly, fill=shadow_col)
    ink_sh = [(px + shadow_off[0] + 4, py + shadow_off[1] + 4) for px, py in poly]
    d.polygon(ink_sh, outline=(14, 12, 22), width=3)

    page.paste(cropped, (x0, y0), mask)

    d.line(poly + [poly[0]], fill=(250, 248, 242), width=border_w + 4, joint="curve")
    d.line(poly + [poly[0]], fill=(14, 12, 20), width=border_w, joint="curve")


def _draw_halftone_corner(draw, cx, cy, radius, dot_step, max_r, color):
    for gx in range(cx - radius, cx + radius + 1, dot_step):
        for gy in range(cy - radius, cy + radius + 1, dot_step):
            dist = math.hypot(gx - cx, gy - cy)
            if dist < radius:
                r = max_r * (1.0 - dist / radius) ** 1.3
                if r >= 1.1:
                    draw.ellipse([gx - r, gy - r, gx + r, gy + r], fill=color)


def _draw_caption_box(draw, x, y, w, h, text, bg_col=(255, 214, 42), fg_col=(14, 12, 20), font=None):
    skew = 10
    pts = [(x + skew, y), (x + w + skew, y), (x + w, y + h), (x, y + h)]
    sh = [(px + 5, py + 5) for px, py in pts]
    draw.polygon(sh, fill=(14, 12, 20))
    draw.polygon(pts, fill=bg_col)
    draw.line(pts + [pts[0]], fill=(14, 12, 20), width=4)
    draw.text((x + 16, y + (h - 20) // 2), text, fill=fg_col, font=font)


def build_comic_page_poster(still_map):
    from PIL import Image, ImageDraw
    import numpy as np

    _, f_med, f_big, f_hero = _load_fonts()
    W, H = 2200, 3100
    rng = np.random.default_rng(2099)
    base = np.empty((H, W, 3), dtype=np.uint8)
    noise = rng.integers(-5, 6, size=(H, W, 1), dtype=np.int16)
    paper_rgb = np.array([[[245, 240, 229]]], dtype=np.int16) + noise
    base[:] = np.clip(paper_rgb, 0, 255).astype(np.uint8)
    page = Image.fromarray(base, mode="RGB")
    d = ImageDraw.Draw(page)

    # Halftone Ben-Day corner accents
    _draw_halftone_corner(d, 90, 210, 340, 18, 6.5, (235, 42, 78))
    _draw_halftone_corner(d, W - 80, 1480, 380, 18, 6.5, (36, 214, 198))
    _draw_halftone_corner(d, 110, H - 100, 360, 18, 6.5, (188, 72, 255))

    # Print registration marks (+) in outer margins
    for rx, ry in ((38, 38), (W - 38, 38), (38, H - 38), (W - 38, H - 38)):
        d.ellipse([rx - 12, ry - 12, rx + 12, ry + 12], outline=(20, 20, 26), width=2)
        d.line([(rx - 18, ry), (rx + 18, ry)], fill=(20, 20, 26), width=2)
        d.line([(rx, ry - 18), (rx, ry + 18)], fill=(20, 20, 26), width=2)

    # Top Comic Issue Masthead Banner
    d.polygon([(70, 58), (W - 70, 58), (W - 92, 168), (70, 168)], fill=(16, 14, 26))
    d.polygon([(70, 162), (790, 162), (782, 174), (70, 174)], fill=(235, 42, 78))
    d.polygon([(790, 162), (1490, 162), (1482, 174), (782, 174)], fill=(36, 214, 198))
    d.polygon([(1490, 162), (W - 92, 162), (W - 96, 174), (1482, 174)], fill=(188, 72, 255))

    d.text((102, 78), "SKY-HARBOR 2099: ACROSS THE APEX", fill=(252, 248, 240), font=f_hero or f_big)
    d.rectangle([W - 442, 74, W - 118, 148], fill=(255, 214, 42), outline=(14, 12, 20), width=4)
    d.text((W - 424, 84), "ISSUE #06 // 3D MEGA-CIRCUIT", fill=(14, 12, 20), font=f_med)
    d.text((W - 424, 114), "2.39:1 SCOPE | 12FPS ON-TWOS", fill=(190, 18, 48), font=f_med)

    def pick(*keys):
        for k in keys:
            if k in still_map and os.path.exists(still_map[k]):
                return still_map[k]
        return next(iter(still_map.values()))

    # Panel 1: Top Wide Diagonal Hero Slash (Act I — Earth-1610 Eau-Rouge Spark Scrape)
    p1 = [(76, 204), (2124, 204), (2124, 765), (76, 845)]
    _paste_polygon_panel(page, pick("06_eau_rouge_sparks", "01_canyon_fpv_drop"), p1,
                         shadow_col=(235, 42, 78), shadow_off=(11, 11))
    _draw_caption_box(d, 108, 228, 650, 48, "ACT I // EARTH-1610 — EAU-ROUGE +42M TITANIUM SPARKS",
                      bg_col=(255, 214, 42), font=f_med)

    # Panel 2 (Left Angled) & Panel 3 (Right Angled): Skyscraper Halo Cockpit + 300mm Moon Crest
    p2 = [(76, 882), (1145, 838), (1075, 1425), (76, 1455)]
    p3 = [(1182, 835), (2124, 798), (2124, 1395), (1112, 1423)]
    _paste_polygon_panel(page, pick("04_halo_cockpit_canyon", "02_scraper_front_wing"), p2,
                         shadow_col=(32, 208, 245), shadow_off=(-9, 10))
    _paste_polygon_panel(page, pick("08_moon_crest_tele300", "07_raidillon_sky_climb"), p3,
                         shadow_col=(255, 208, 38), shadow_off=(10, 10))
    _draw_caption_box(d, 104, 1378, 500, 44, "SKYSCRAPER CANYON // HALO POV & 12FPS STEER",
                      bg_col=(36, 214, 198), font=f_med)
    _draw_caption_box(d, 1505, 826, 580, 44, "300MM TELEPHOTO // RAIDILLON MOON CREST",
                      bg_col=(255, 214, 42), font=f_med)

    # Panel 4: Center Full-Width Diagonal Splash (Act II — Earth-65 17.4 deg Banked Bowl)
    p4 = [(76, 1492), (2124, 1432), (2124, 2125), (76, 2195)]
    _paste_polygon_panel(page, pick("12_banked_wall_rail", "09_bridge_pylon_reveal", "11_bridge_deck_pursuit"),
                         p4, shadow_col=(36, 214, 198), shadow_off=(12, 12))
    _draw_caption_box(d, 108, 1520, 690, 48, "ACT II // EARTH-65 — 17.4 DEG BANKED BOWL & SKY-BRIDGE",
                      bg_col=(255, 92, 186), fg_col=(14, 12, 20), font=f_med)

    # Panel 5 (Bottom Left) & Panel 6 (Bottom Right): Act III — Earth-928 2099 Strobe Tunnel & Wet Skyline
    p5 = [(76, 2232), (1195, 2190), (1110, 2995), (76, 2995)]
    p6 = [(1232, 2188), (2124, 2160), (2124, 2995), (1148, 2995)]
    _paste_polygon_panel(page, pick("19_tunnel_whip_orbit180", "17_tunnel_portal_warp"), p5,
                         shadow_col=(188, 72, 255), shadow_off=(-10, 11))
    _paste_polygon_panel(page, pick("23_wet_mirror_skyline", "21_hairpin_wheel_macro"), p6,
                         shadow_col=(235, 32, 72), shadow_off=(11, 11))
    _draw_caption_box(d, 104, 2918, 560, 46, "ACT III // EARTH-928 — 341 KM/H CYBER TUNNEL",
                      bg_col=(188, 72, 255), fg_col=(250, 248, 255), font=f_med)
    _draw_caption_box(d, 1485, 2918, 605, 46, "WET MIRROR NEON // HARBOR SKYLINE FINALE",
                      bg_col=(235, 42, 78), fg_col=(252, 248, 242), font=f_med)

    # Panel 7: Overlapping Tilted Action Inset — 2-Frame Graphic Impact Slam (f=1067)
    clip_imp = os.path.join(PROJ, "renders_v6", "clips_frames", "clip3_2099_impact", "f_1067.jpg")
    aux_imp = os.path.join(OUT, "_impact_f1067.jpg")
    imp_path = clip_imp if os.path.exists(clip_imp) else (aux_imp if os.path.exists(aux_imp) else pick("20_harbor_brake_slam"))
    p7 = [(855, 2065), (1505, 2025), (1455, 2425), (805, 2465)]
    d.polygon([(835, 2045), (1525, 2005), (1475, 2445), (785, 2485)], fill=(252, 248, 240))
    _paste_polygon_panel(page, imp_path, p7, shadow_col=(235, 28, 62), shadow_off=(9, 9), border_w=8)
    _draw_caption_box(d, 845, 2418, 515, 42, "IMPACT FRAME // f1067 HARBOR SLAM!",
                      bg_col=(255, 214, 42), font=f_med)

    # Outer page framing rule
    d.rectangle([52, 42, W - 52, H - 42], outline=(18, 16, 26), width=5)

    out_poster = os.path.join(OUT, "comic_page_sheet.jpg")
    page.save(out_poster, quality=95, subsampling=0)
    print("V6 COMIC PAGE POSTER:", out_poster, page.size)


if DO_RENDER:
    render_with_blender()
    try:
        import PIL  # noqa: F401
        made = [(f, name, os.path.join(OUT, f"shot_{name}.jpg"))
                for f, name in SHOTS if os.path.exists(os.path.join(OUT, f"shot_{name}.jpg"))]
        build_contact_sheet_v6(made)
        build_comic_page_poster({name: path for _, name, path in made})
    except ImportError:
        env = os.environ.copy()
        env.pop("PYTHONHOME", None)
        env.pop("PYTHONPATH", None)
        res = subprocess.run(["python", os.path.abspath(__file__), "--sheet-only"], env=env, check=False)
        if res.returncode != 0:
            raise RuntimeError(f"v6_sv_stills sheet generation failed with code {res.returncode}")
else:
    made = [(f, name, os.path.join(OUT, f"shot_{name}.jpg"))
            for f, name in SHOTS if os.path.exists(os.path.join(OUT, f"shot_{name}.jpg"))]
    print("v6 stills found:", len(made))
    if made:
        build_contact_sheet_v6(made)
        build_comic_page_poster({name: path for _, name, path in made})
