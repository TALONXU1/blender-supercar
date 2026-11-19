# -*- coding: utf-8 -*-
import bpy, os
from mathutils import Vector

PROJ = r"D:\项目session\blender-supercar"
bpy.ops.wm.open_mainfile(filepath=os.path.join(PROJ, "LATEST", "v5_stage_anim.blend"))
scene = bpy.context.scene
rig = bpy.data.objects["RIG_F1_Race"]

# 1. Check Mat_Brake_HeatGlow driver and GEO_F1_BrakeGlow_FL geometry at a heavy braking frame
m_bg = bpy.data.materials.get("Mat_Brake_HeatGlow")
if m_bg and m_bg.node_tree and m_bg.node_tree.animation_data:
    for d in m_bg.node_tree.animation_data.drivers:
        print("BrakeGlow DRV:", d.data_path, "expr=", d.driver.expression, "is_valid=", d.is_valid)
        for v in d.driver.variables:
            t = v.targets[0]
            print("  var:", v.name, "id_type=", t.id_type, "id=", t.id.name if t.id else None, "path=", t.data_path)

# Find frame with max brake_heat
max_bh = (-1.0, 1)
for f in range(1, 2162, 5):
    scene.frame_set(f)
    bh = rig.get("brake_heat", 0.0)
    if bh > max_bh[0]:
        max_bh = (bh, f)
print("Max brake_heat sampled:", max_bh)

scene.frame_set(max_bh[1])
dg = bpy.context.evaluated_depsgraph_get()
m_bg_eval = m_bg.evaluated_get(dg)
for n in m_bg_eval.node_tree.nodes:
    if n.type == 'EMISSION':
        print("At max brake_heat frame, evaluated Mat_Brake_HeatGlow strength =", n.inputs[1].default_value)

for nm in ("GEO_F1_BrakeGlow_FL", "GEO_F1_BrakeDisc_FL", "GEO_F1_BrakeCaliper_FL", "GEO_F1_BrakeDuct_FL", "GEO_F1_RimSpokes_FL"):
    ob = bpy.data.objects.get(nm)
    if ob:
        bb = [Vector(c) for c in ob.bound_box]
        mn = Vector((min(v.x for v in bb), min(v.y for v in bb), min(v.z for v in bb)))
        mx = Vector((max(v.x for v in bb), max(v.y for v in bb), max(v.z for v in bb)))
        print(f"  {nm:<26} hide_render={ob.hide_render} verts={len(ob.data.vertices)} local_min={[round(x,3) for x in mn]} local_max={[round(x,3) for x in mx]}")

# 2. Check cockpit / steering wheel / halo / T-cam bounds in car Bone_Heading space
scene.frame_set(1)
dg = bpy.context.evaluated_depsgraph_get()
reval = rig.evaluated_get(dg)
car_inv = (reval.matrix_world @ reval.pose.bones["Bone_Heading"].matrix).inverted()
for nm in ("GEO_F1_Cockpit_SteeringWheel", "GEO_F1_Steering_LCDScreen", "GEO_F1_Halo_Hoop", "GEO_F1_Halo_CenterPylon", "GEO_F1_Nosecone", "GEO_F1_Airbox_Scoop"):
    ob = bpy.data.objects.get(nm)
    if ob:
        ob_e = ob.evaluated_get(dg)
        pts = [car_inv @ ob_e.matrix_world @ Vector(c) for c in ob_e.bound_box]
        mn = [round(min(p[i] for p in pts), 3) for i in range(3)]
        mx = [round(max(p[i] for p in pts), 3) for i in range(3)]
        print(f"  CAR_LOCAL {nm:<30} min={mn} max={mx}")

# 3. Check ALL V5_Hangar_* and V5_HedgeRing minimum distance to V5_Track vertices!
track_ob = bpy.data.objects["V5_Track"]
track_pts = [track_ob.matrix_world @ v.co for v in list(track_ob.data.vertices)[::8]]
for i in range(6):
    h_ob = bpy.data.objects.get(f"V5_Hangar_{i}")
    if h_ob:
        hc = h_ob.matrix_world.translation
        dmin = min((hc.xy - tp.xy).length for tp in track_pts)
        print(f"  V5_Hangar_{i}: loc=({hc.x:.1f}, {hc.y:.1f}) dims={[round(x,1) for x in h_ob.dimensions]} min_dist_to_track={dmin:.1f}m")

hedge = bpy.data.objects.get("V5_HedgeRing")
if hedge:
    h_pts = [hedge.matrix_world @ v.co for v in list(hedge.data.vertices)[::4]]
    dmin_h = min(min((hp.xy - tp.xy).length for tp in track_pts) for hp in h_pts)
    max_track_r = max((tp.xy - hedge.location.xy).length for tp in track_pts)
    print(f"  V5_HedgeRing: min_dist_to_track={dmin_h:.1f}m, max_track_radius_from_hedge_center={max_track_r:.1f}m")

# 4. Full occlusion breakdown of Cam_S20_StoweTele (every 2 frames)
cam20 = bpy.data.objects["Cam_S20_StoweTele"]
car_set = {o.name for o in bpy.data.objects if o.type == 'MESH' and not o.name.startswith("V5_")}
occ20 = {}
for f in range(1682, 1789, 2):
    scene.frame_set(f)
    dg = bpy.context.evaluated_depsgraph_get()
    cp = cam20.evaluated_get(dg).matrix_world.translation
    rp = (rig.evaluated_get(dg).matrix_world @ rig.evaluated_get(dg).pose.bones["Bone_Root"].matrix).translation + Vector((0, 0, 0.5))
    dv = rp - cp
    hit, loc, _, _, ho, _ = scene.ray_cast(dg, cp + dv.normalized()*0.05, dv.normalized(), distance=dv.length - 0.15)
    if hit and ho and ho.name not in car_set:
        occ20.setdefault(ho.name, []).append(f)
print("Cam_S20_StoweTele blockers by object:", occ20)
