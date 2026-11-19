# -*- coding: utf-8 -*-
import bpy
from mathutils import Vector

scene = bpy.context.scene
rig = bpy.data.objects["RIG_F1_Race"]
deps = bpy.context.evaluated_depsgraph_get()
markers = sorted(scene.timeline_markers, key=lambda m: m.frame)

def active_cam(f):
    c = scene.camera
    for m in markers:
        if m.frame <= f:
            c = m.camera
    return c

for f in (277, 374, 1160, 1170, 1372, 1415, 1730):
    scene.frame_set(f)
    deps.update()
    cam = active_cam(f).evaluated_get(deps)
    rig_e = rig.evaluated_get(deps)
    cpos = cam.matrix_world.translation.copy()
    car_pos = (rig_e.matrix_world @ rig_e.pose.bones["Bone_Root"].matrix).translation + Vector((0, 0, 0.48))
    vec = car_pos - cpos
    d = vec.length
    u = vec.normalized()
    hit, loc, norm, idx, hob, _ = scene.ray_cast(deps, cpos + u * 0.5, u, distance=d - 1.1)
    print(f"f={f:4d} cam={cam.name:24s} cpos={tuple(round(x,2) for x in cpos)} car={tuple(round(x,2) for x in car_pos)} dist={d:.2f}")
    if hit and hob:
        print(f"   HIT {hob.name:26s} at {tuple(round(x,2) for x in loc)} (dist={(loc-cpos).length:.2f}) hob.loc={tuple(round(x,2) for x in hob.matrix_world.translation)}")
