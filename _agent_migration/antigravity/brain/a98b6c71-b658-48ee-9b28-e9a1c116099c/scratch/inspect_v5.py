# -*- coding: utf-8 -*-
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree
import bmesh

print("=== COLLECTIONS ===")
def dump_coll(c, indent=0):
    objs = [o.name for o in c.objects]
    print("  " * indent + f"[{c.name}] direct_objs={len(objs)} sample={objs[:8]}")
    for ch in c.children:
        dump_coll(ch, indent + 1)

dump_coll(bpy.context.scene.collection)
print("Unlinked collections:", [c.name for c in bpy.data.collections if c.name not in [x.name for x in bpy.context.scene.collection.children_recursive]])

print("\n=== ALL NON-V5 OBJECTS ===")
for o in sorted(bpy.data.objects, key=lambda x: x.name):
    if not o.name.startswith("V5_") and not o.name.startswith("Cam_"):
        mats = [m.name if m else None for m in getattr(o.data, "materials", [])] if hasattr(o.data, "materials") else []
        colls = [c.name for c in o.users_collection]
        print(f"  {o.name:34s} type={o.type:8s} parent={o.parent.name if o.parent else None} colls={colls} mats={mats}")

print("\n=== RIG BONES & CONSTRAINTS & DRIVERS ===")
rig = bpy.data.objects.get("RIG_F1_Race")
if rig:
    print("Custom props:", {k: rig[k] for k in rig.keys()})
    for pb in rig.pose.bones:
        print(f"  Bone: {pb.name:24s} parent={pb.parent.name if pb.parent else None} rot_mode={pb.rotation_mode} head={tuple(round(x,3) for x in pb.bone.head_local)} tail={tuple(round(x,3) for x in pb.bone.tail_local)}")
        for cn in pb.constraints:
            print(f"    constraint: {cn.name} ({cn.type})")
    if rig.animation_data and rig.animation_data.drivers:
        print("  Rig drivers:")
        for d in rig.animation_data.drivers:
            print(f"    {d.data_path}[{d.array_index}] -> {d.driver.expression}")

print("\n=== OBJECT DRIVERS & CONSTRAINTS (CAR PARTS) ===")
for o in sorted(bpy.data.objects, key=lambda x: x.name):
    if not o.name.startswith("V5_"):
        if o.animation_data and o.animation_data.drivers:
            for d in o.animation_data.drivers:
                print(f"  ObjDriver {o.name}: {d.data_path}[{d.array_index}] -> {d.driver.expression}")
        for m in o.modifiers:
            print(f"  Modifier {o.name}: {m.name} ({m.type}) obj={getattr(m, 'object', None)}")
        for cn in o.constraints:
            print(f"  Constraint {o.name}: {cn.name} ({cn.type}) target={getattr(cn, 'target', None)} subtarget={getattr(cn, 'subtarget', '')}")

print("\n=== CAR MATERIALS DETAIL ===")
car_mats = set()
for o in bpy.data.objects:
    if o.type == 'MESH' and not o.name.startswith("V5_") and not o.name.startswith("GEO_Race"):
        for m in o.data.materials:
            if m:
                car_mats.add(m)
for m in sorted(car_mats, key=lambda x: x.name):
    nodes = [(n.name, n.type) for n in m.node_tree.nodes] if m.node_tree else []
    drivers = [d.data_path for d in m.node_tree.animation_data.drivers] if (m.node_tree and m.node_tree.animation_data) else []
    print(f"  Mat {m.name:28s}: nodes={nodes} drivers={drivers}")

print("\n=== EMPTIES IN SCENE ===")
for o in sorted(bpy.data.objects, key=lambda x: x.name):
    if o.type == 'EMPTY':
        print(f"  Empty {o.name:28s} colls={[c.name for c in o.users_collection]} children={len(o.children)}")

print("\n=== CAMERA RAYCAST & GROUND CHECK (STEP 1) ===")
scene = bpy.context.scene
depsgraph = bpy.context.evaluated_depsgraph_get()

# Determine active camera per frame from timeline markers
markers = sorted(scene.timeline_markers, key=lambda m: m.frame)
def active_cam_at(f):
    cur = scene.camera
    for m in markers:
        if m.frame <= f and m.camera:
            cur = m.camera
        elif m.frame > f:
            break
    return cur

car_objs = set()
for o in bpy.data.objects:
    if o.type == 'MESH' and (not o.name.startswith("V5_")) and (not o.name.startswith("GEO_Race")):
        car_objs.add(o.name)

occlusions = {}
low_cams = []
for f in range(1, scene.frame_end + 1, 2):
    scene.frame_set(f)
    depsgraph.update()
    cam = active_cam_at(f)
    cam_eval = cam.evaluated_get(depsgraph)
    rig_eval = rig.evaluated_get(depsgraph)
    cam_pos = cam_eval.matrix_world.translation.copy()
    if cam_pos.z < 0.18:
        low_cams.append((f, cam.name, round(cam_pos.z, 3)))
    pb_root = rig_eval.pose.bones["Bone_Root"]
    car_pos = (rig_eval.matrix_world @ pb_root.matrix).translation + Vector((0, 0, 0.48))
    vec = car_pos - cam_pos
    dist = vec.length
    if dist > 0.6:
        direction = vec.normalized()
        # Raycast starting 0.5m from camera (clip_start) up to dist - 0.8m
        cur_origin = cam_pos + direction * 0.5
        rem = dist - 1.3
        while rem > 0.05:
            hit, loc, norm, idx, hit_ob, mat = scene.ray_cast(depsgraph, cur_origin, direction, distance=rem)
            if not hit or hit_ob is None:
                break
            if hit_ob.name in car_objs or hit_ob.name == "V5_SkyDome":
                # advance past car part (e.g. onboard nosecone)
                step = (loc - cur_origin).length + 0.05
                cur_origin = loc + direction * 0.05
                rem -= step
                continue
            occlusions.setdefault((cam.name, hit_ob.name), []).append((f, round((loc - cam_pos).length, 2), round(dist, 2)))
            break

print("Low camera frames (<0.18m):", low_cams[:20], "total:", len(low_cams))
print("Camera occlusions:")
for (cname, hname), hits in sorted(occlusions.items()):
    frames = [x[0] for x in hits]
    print(f"  {cname:26s} blocked by {hname:28s}: {len(frames)} frames (f={min(frames)}..{max(frames)}, sample={hits[:3]})")
