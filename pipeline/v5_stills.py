# -*- coding: utf-8 -*-
"""
V5 交付剧照与 Contact Sheet 生成器：
1) 直接从工程渲染全部 26 个镜头代表帧（1080p / 32 samples）并拼装高清标注版 contact_sheet.jpg：
     blender -b LATEST/v5_stage_anim.blend -P pipeline/v5_stills.py -- --render
2) 从已有序列帧 renders_v5/frames/f_*.jpg 抽帧并拼图：
     python pipeline/v5_stills.py
3) 仅根据现有 renders_v5/stills/shot_*.jpg 重新拼装 contact_sheet.jpg：
     python pipeline/v5_stills.py --sheet-only
"""
import os
import sys
import shutil
import subprocess

PROJ = r"D:\项目session\blender-supercar"
FR = os.path.join(PROJ, "renders_v5", "frames")
OUT = os.path.join(PROJ, "renders_v5", "stills")
os.makedirs(OUT, exist_ok=True)

ARGV = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
DO_RENDER = "--render" in ARGV
SHEET_ONLY = "--sheet-only" in ARGV

SHOTS = [
    (60, "01_rear_chase"),
    (160, "02_onboard"),
    (250, "03_chase_rise"),
    (350, "04_hairpin"),
    (440, "05_chase_aintree"),
    (520, "06_orbit1"),
    (600, "07_chase_accel"),
    (700, "08_fast_pan"),
    (760, "09_wheel_macro"),
    (820, "10_chase_fast"),
    (870, "11_orbit_brooklands"),
    (950, "12_luffield"),
    (1040, "13_chase_woodcote"),
    (1120, "14_woodcote_tele"),
    (1200, "15_heli_drop"),
    (1300, "16_orbit_copse"),
    (1380, "17_chase_copse"),
    (1470, "18_maggotts"),
    (1560, "19_chase_rise2"),
    (1640, "20_onboard3"),
    (1730, "21_stowe_tele"),
    (1830, "22_orbit_stowe"),
    (1920, "23_chase_low"),
    (2010, "24_heli_reveal"),
    (2090, "25_club"),
    (2145, "26_aerial_out"),
]


def render_with_blender():
    import bpy
    sc = bpy.context.scene
    if not bpy.data.filepath:
        default_blend = os.path.join(PROJ, "LATEST", "v5_stage_anim.blend")
        bpy.ops.wm.open_mainfile(filepath=default_blend)
        sc = bpy.context.scene

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
    sc.eevee.taa_render_samples = 32
    sc.eevee.use_raytracing = True
    sc.render.resolution_x = 1920
    sc.render.resolution_y = 1080
    sc.render.resolution_percentage = 100
    sc.render.use_motion_blur = True
    sc.render.image_settings.file_format = 'JPEG'
    sc.render.image_settings.quality = 95

    meta_lines = []
    for f, name in SHOTS:
        cam = active_cam_for_frame(f)
        sc.camera = cam
        sc.frame_set(f)
        deps = bpy.context.evaluated_depsgraph_get()
        cam_eval = cam.evaluated_get(deps) if cam else None
        lens = cam_eval.data.lens if cam_eval else 0.0
        fstop = cam_eval.data.dof.aperture_fstop if cam_eval else 0.0
        dof_on = (cam_eval.data.dof.use_dof and cam_eval.data.dof.focus_object is not None) if cam_eval else False
        dst = os.path.join(OUT, "shot_%s.jpg" % name)
        sc.render.filepath = dst
        bpy.ops.render.render(write_still=True)
        tag = f"{int(round(lens))}mm f/{fstop:.1f}" + (" DOF" if dof_on else "")
        meta_lines.append(f"{name}|{f}|{tag}")
        print(f"RENDERED shot_{name}.jpg (f={f}, {tag})")

    sc.camera = orig_cam
    meta_file = os.path.join(OUT, ".stills_meta.txt")
    with open(meta_file, "w", encoding="utf-8") as fp:
        fp.write("\n".join(meta_lines) + "\n")


def build_contact_sheet_pil(made):
    from PIL import Image, ImageDraw, ImageFont

    meta_map = {}
    meta_file = os.path.join(OUT, ".stills_meta.txt")
    if os.path.exists(meta_file):
        with open(meta_file, encoding="utf-8") as fp:
            for line in fp:
                parts = line.strip().split("|")
                if len(parts) == 3:
                    meta_map[parts[0]] = parts[2]

    tw, th = 384, 216
    bar_h = 24
    cols = 5
    rows = (len(made) + cols - 1) // cols
    header_h = 36
    sheet = Image.new("RGB", (cols * tw, header_h + rows * (th + bar_h)), (12, 13, 16))
    d = ImageDraw.Draw(sheet)

    font = None
    title_font = None
    for candidate in (r"C:\Windows\Fonts\consolab.ttf", r"C:\Windows\Fonts\consola.ttf", r"C:\Windows\Fonts\arial.ttf"):
        if os.path.exists(candidate):
            try:
                font = ImageFont.truetype(candidate, 13)
                title_font = ImageFont.truetype(candidate, 16)
                break
            except Exception:
                pass

    d.text((14, 9), "V5 SILVERSTONE FULL LAP  |  26 SHOTS  |  1920x1080 EEVEE (AgX + Broadcast DOF + Telemetry Rig)",
           fill=(225, 230, 238), font=title_font or font)

    for i, (f, name, path) in enumerate(made):
        im = Image.open(path).convert("RGB").resize((tw, th), Image.Resampling.LANCZOS)
        x = (i % cols) * tw
        y = header_h + (i // cols) * (th + bar_h)
        sheet.paste(im, (x, y))
        # Subtle cell border
        d.rectangle([x, y, x + tw - 1, y + th + bar_h - 1], outline=(32, 35, 42), width=1)
        cam_tag = meta_map.get(name, "")
        label = f"{name} (f{f})" + (f"  [{cam_tag}]" if cam_tag else "")
        d.text((x + 7, y + th + 4), label, fill=(205, 212, 222), font=font)

    out = os.path.join(OUT, "contact_sheet.jpg")
    sheet.save(out, quality=94, subsampling=0)
    print("contact sheet:", out, sheet.size)


if DO_RENDER:
    render_with_blender()
    # Build contact sheet via PIL if available here, else invoke system Python cleanly
    try:
        import PIL  # noqa: F401
        made = [(f, name, os.path.join(OUT, f"shot_{name}.jpg"))
                for f, name in SHOTS if os.path.exists(os.path.join(OUT, f"shot_{name}.jpg"))]
        build_contact_sheet_pil(made)
    except ImportError:
        env = os.environ.copy()
        env.pop("PYTHONHOME", None)
        env.pop("PYTHONPATH", None)
        res = subprocess.run(["python", os.path.abspath(__file__), "--sheet-only"], env=env, check=False)
        if res.returncode != 0:
            raise RuntimeError(f"contact_sheet build failed with code {res.returncode}")
else:
    made = []
    for f, name in SHOTS:
        dst = os.path.join(OUT, "shot_%s.jpg" % name)
        if not SHEET_ONLY:
            src = os.path.join(FR, "f_%04d.jpg" % f)
            if os.path.exists(src):
                shutil.copyfile(src, dst)
            elif not os.path.exists(dst):
                print("MISS", f)
                continue
        if os.path.exists(dst):
            made.append((f, name, dst))
    print("stills:", len(made))
    if made:
        build_contact_sheet_pil(made)
