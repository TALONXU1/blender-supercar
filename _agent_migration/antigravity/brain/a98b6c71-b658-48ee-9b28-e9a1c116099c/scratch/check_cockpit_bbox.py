# -*- coding: utf-8 -*-
import bpy
from mathutils import Vector

bpy.ops.wm.open_mainfile(filepath=r"D:\项目session\blender-supercar\LATEST\v5_stage_env.blend")
for o in sorted(bpy.data.objects, key=lambda x: x.name):
    if any(k in o.name for k in ("Headrest", "BucketSeat", "Halo", "SteeringWheel", "Overhead_TCam", "HoloHUD")):
        bb = [o.matrix_world @ Vector(c) for c in o.bound_box]
        mn = tuple(round(min(v[i] for v in bb), 3) for i in range(3))
        mx = tuple(round(max(v[i] for v in bb), 3) for i in range(3))
        print(f"{o.name:34s}: X=[{mn[0]:+.3f}..{mx[0]:+.3f}] Y=[{mn[1]:+.3f}..{mx[1]:+.3f}] Z=[{mn[2]:+.3f}..{mx[2]:+.3f}]")
