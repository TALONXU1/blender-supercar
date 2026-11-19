# -*- coding: utf-8 -*-
"""Extra targeted previews + geometry/material audit on LATEST/v5_stage_env.blend"""
import bpy, json, math, os, time
from mathutils import Vector

PROJ = r"D:\项目session\blender-supercar"
BLEND = os.path.join(PROJ, "LATEST", "v5_stage_env.blend")
OUT = os.path.join(PROJ, "renders_v5", "preview")
TRACK = os.path.join(PROJ, "track_data", "silverstone_track.json")

bpy.ops.wm.open_mainfile(filepath=BLEND)
sc = bpy.context.scene
pts = json.load(open(TRACK, encoding="utf-8"))["points"]
N = len(pts)

# 1. Audit collections, root objects, orphans, road specular, clearances
root_objs = [o.name for o in sc.collection.objects]
unbucketed_v5 = [
    o.name for o in bpy.data.objects
    if (o.name.startswith("V5_") or o.name.startswith("LGT_V5") or o.type == 'EMPTY')
    and not any(c.name.startswith("V5_0") for c in o.users_collection)
]
road_spec_violations = []
for mn in ("V5_Asphalt", "V5_RubberLine", "V5_BrakingRubber", "V5_WhiteLine",
           "V5_CurbRed", "V5_CurbWhite", "V5_SausageYellow", "V5_SausageBlack", "V5_Gravel"):
    m = bpy.data.materials.get(mn)
    if m and m.node_tree:
        for n in m.node_tree.nodes:
            if n.type == 'BSDF_PRINCIPLED':
                sp = n.inputs['Specular IOR Level'].default_value
                if sp > 0.0301:
                    road_spec_violations.append((mn, sp))

# Check min distance from Hangars, HedgeRing, Grandstands, SausageKerbs, ApexBollards to racing_xy & centerline
rxy = [(p["racing_xy"][0], p["racing_xy"][1]) for p in pts]
cxy = [(p["xy"][0], p["xy"][1]) for p in pts]

def min_dist_mesh(ob, ref_pts, step=4):
    mw = ob.matrix_world
    vs = [mw @ v.co for v in ob.data.vertices]
    if len(vs) > 400:
        vs = vs[:: max(1, len(vs) // 400)]
    best = 1e9
    for v in vs:
        vx, vy = v.x, v.y
        d = min(math.hypot(vx - rx, vy - ry) for rx, ry in ref_pts[::step])
        if d < best:
            best = d
    return best

min_hangar = min(min_dist_mesh(o, cxy, 4) for o in bpy.data.objects if o.name.startswith("V5_Hangar_"))
min_hedge = min_dist_mesh(bpy.data.objects["V5_HedgeRing"], cxy, 4)
min_stand = min(min_dist_mesh(o, cxy, 4) for o in bpy.data.objects if o.type == 'MESH' and o.name.startswith("V5_Stand_"))
min_sausage_rxy = min_dist_mesh(bpy.data.objects["V5_Kerb_Sausage"], rxy, 1)
min_bollard_rxy = min_dist_mesh(bpy.data.objects["V5_ApexBollards"], rxy, 1)

print("=== SCENE AUDIT ===")
print("Total objects:", len(bpy.data.objects), "| Root objs:", root_objs)
print("Unbucketed V5/Empty objs:", unbucketed_v5)
print("Road specular > 0.03 violations:", road_spec_violations)
print(f"Clearances: Hangar_to_XY={min_hangar:.1f}m | Hedge_to_XY={min_hedge:.1f}m | Stand_to_XY={min_stand:.1f}m")
print(f"Clearances: Sausage_to_racing_xy={min_sausage_rxy:.2f}m | Bollard_to_racing_xy={min_bollard_rxy:.2f}m")

# 2. Render 3 extra targeted 1600x900 shots (Pit/Timing/ExitLED, Sky+DRS+Skids, Car Hero)
def at_s(s):
    s = s % pts[-1]["s"]
    lo, hi = 0, N - 1
    while hi - lo > 1:
        m = (lo + hi) // 2
        if pts[m]["s"] <= s:
            lo = m
        else:
            hi = m
    f = (s - pts[lo]["s"]) / max(pts[lo + 1]["s"] - pts[lo]["s"], 1e-9)
    x = pts[lo]["xy"][0] * (1 - f) + pts[lo + 1]["xy"][0] * f
    y = pts[lo]["xy"][1] * (1 - f) + pts[lo + 1]["xy"][1] * f
    a = math.radians(pts[lo]["heading_deg"])
    b = math.radians(pts[lo + 1]["heading_deg"])
    d = (b - a + math.pi) % (2 * math.pi) - math.pi
    h = a + d * f
    return Vector((x, y, 0.0)), h, Vector((math.sin(h), -math.cos(h), 0.0))

cd = bpy.data.cameras.new("CAM_EXTRA")
cam = bpy.data.objects.new("CAM_EXTRA", cd)
sc.collection.objects.link(cam)
sc.camera = cam
cd.clip_start = 0.5
cd.clip_end = 9000
sc.render.engine = 'BLENDER_EEVEE'
sc.eevee.taa_render_samples = 32
sc.eevee.use_raytracing = True
sc.render.resolution_x = 1920
sc.render.resolution_y = 1080
sc.render.image_settings.file_format = 'JPEG'
sc.render.image_settings.quality = 94
sc.view_settings.view_transform = 'AgX'
for lk in ('High Contrast', 'AgX - High Contrast', 'Medium High Contrast'):
    try:
        sc.view_settings.look = lk
        break
    except Exception:
        continue
sc.view_settings.exposure = 0.50

def shoot(name, loc, tgt, lens):
    t0 = time.time()
    loc = Vector(loc)
    d = Vector(tgt) - loc
    cam.location = loc
    cam.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    cd.lens = lens
    sc.render.filepath = os.path.join(OUT, name + ".jpg")
    bpy.ops.render.render(write_still=True)
    print(f"EXTRA SHOT {name}: {time.time() - t0:.2f} s")

# 06: Pit lane + garage + pit-wall timing stand + pit exit green LED
p1, h1, r1 = at_s(135.0)
p2, _, r2 = at_s(240.0)
shoot("06_pit_lane", p1 + r1 * (-14.5) + Vector((0, 0, 2.1)), p2 + r2 * (-15.5) + Vector((0, 0, 2.2)), 42)

# 07: Low-angle dusk sky + DRS board + Stowe heavy braking skidmarks
p3, h3, r3 = at_s(4242.0)
p4, _, r4 = at_s(4310.0)
shoot("07_sky_drs", p3 + r3 * (-2.0) + Vector((0, 0, 1.05)), p4 + r4 * (-2.5) + Vector((0, 0, 4.5)), 32)

# 08: Car hero material close-up (paint clearcoat, carbon wing weave, tire tread vs sidewall)
shoot("08_car_hero", (-3.1, 3.4, 1.15), (0.0, 0.2, 0.42), 48)
