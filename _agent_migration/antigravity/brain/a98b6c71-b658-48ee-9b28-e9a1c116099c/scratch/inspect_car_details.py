# -*- coding: utf-8 -*-
import bpy
from mathutils import Vector

rig = bpy.data.objects["RIG_F1_Race"]
scene = bpy.context.scene
scene.frame_set(1)
deps = bpy.context.evaluated_depsgraph_get()

print("=== STEERING & COCKPIT OBJECTS ===")
target_prefixes = ("GEO_F1_Cockpit", "GEO_F1_Steering", "GEO_F1_ShiftLED", "GEO_F1_Halo",
                   "GEO_F1_Overhead_TCam", "GEO_F1_FIA_RainLight", "GEO_F1_Exhaust",
                   "GEO_F1_Brake")
for o in sorted(bpy.data.objects, key=lambda x: x.name):
    if o.name.startswith(target_prefixes):
        vgs = [vg.name for vg in o.vertex_groups] if hasattr(o, "vertex_groups") else []
        mods = [(m.name, m.type, getattr(m, "object", None)) for m in o.modifiers]
        bb = [o.matrix_world @ Vector(c) for c in o.bound_box]
        mn = tuple(round(min(v[i] for v in bb), 3) for i in range(3))
        mx = tuple(round(max(v[i] for v in bb), 3) for i in range(3))
        print(f"  {o.name:32s} parent_type={o.parent_type:8s} parent_bone={o.parent_bone!r:20s} vgs={vgs} mods={[(a,b) for a,b,_ in mods]} loc={tuple(round(x,3) for x in o.location)} bbox_local_approx=({mn}..{mx})")

print("\n=== BONE CONSTRAINTS DETAIL ===")
for pb in rig.pose.bones:
    for c in pb.constraints:
        info = {k: getattr(c, k) for k in dir(c) if k.startswith(("use_", "min_", "max_", "owner_space", "target_space"))}
        print(f"  {pb.name}.{c.name} ({c.type}): {info}")

print("\n=== RIG DRIVERS DETAIL ===")
if rig.animation_data:
    for d in rig.animation_data.drivers:
        vars_info = [(v.name, v.type, [(t.id.name if t.id else None, t.data_path) for t in v.targets]) for v in d.driver.variables]
        print(f"  {d.data_path}[{d.array_index}] expr={d.driver.expression!r} vars={vars_info}")

print("\n=== MAT_BRAKE_HEATGLOW & MAT_NEON_ORANGE DETAIL ===")
for mname in ("Mat_Brake_HeatGlow", "Mat_BrakeDisc_CarbonCeramic", "Mat_Caliper_Anodized", "Mat_Neon_Orange", "Mat_Steering_LCD_Telemetry"):
    m = bpy.data.materials.get(mname)
    if not m:
        continue
    print(f"Material: {m.name} (users={m.users})")
    if m.node_tree:
        for n in m.node_tree.nodes:
            inps = {inp.name: getattr(inp, "default_value", None) for inp in n.inputs}
            clean_inps = {}
            for k, v in inps.items():
                if hasattr(v, "__len__") and not isinstance(v, str):
                    clean_inps[k] = tuple(round(float(x), 4) for x in v)
                elif isinstance(v, (int, float)):
                    clean_inps[k] = round(float(v), 4)
            print(f"  Node {n.name} ({n.type}): {clean_inps}")
        if m.node_tree.animation_data:
            for d in m.node_tree.animation_data.drivers:
                vars_info = [(v.name, v.type, [(t.id.name if t.id else None, t.data_path) for t in v.targets]) for v in d.driver.variables]
                print(f"  Driver {d.data_path}[{d.array_index}] expr={d.driver.expression!r} vars={vars_info}")

print("\n=== CHECK LOCAL REST COORDINATES IN v4_stage_rig.blend / v5_stage_env.blend ===")
bpy.ops.wm.open_mainfile(filepath=r"D:\项目session\blender-supercar\LATEST\v5_stage_env.blend")
rig2 = bpy.data.objects["RIG_F1_Race"]
for name in ("GEO_F1_Cockpit_SteeringWheel", "GEO_F1_Steering_LCDScreen", "GEO_F1_Halo_CenterPylon",
             "GEO_F1_Halo_Hoop", "GEO_F1_Overhead_TCam", "GEO_F1_Nosecone", "GEO_F1_FIA_RainLight",
             "GEO_F1_BrakeGlow_FL", "GEO_F1_BrakeDisc_FL", "GEO_F1_BrakeCaliper_FL"):
    o = bpy.data.objects.get(name)
    if o:
        bb = [o.matrix_world @ Vector(c) for c in o.bound_box]
        mn = tuple(round(min(v[i] for v in bb), 3) for i in range(3))
        mx = tuple(round(max(v[i] for v in bb), 3) for i in range(3))
        print(f"  ENV {name:30s}: parent_type={o.parent_type} parent_bone={o.parent_bone!r} bbox={mn} .. {mx}")
