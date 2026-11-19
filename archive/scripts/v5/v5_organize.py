# -*- coding: utf-8 -*-
"""
V5 场景可编辑化：把程序生成的环境整理成"能手工编辑"的工程
  1) 原点归位：所有 ZV5_ 环境对象的 origin 从 (0,0,0) 挪到各自几何中心
     （否则你在 Blender 里选中赛道按 G 拖，是绕一千米外的原点转，看起来"动不了"）
  2) 集合分组：Road / Terrain / Barriers / Stands / Pit / Props / Lighting
  3) 保留 world 变换不变，渲染结果不受影响（纯工程整理）

用法: blender -b -P pipeline/v5_organize.py
"""
import bpy
import os
from mathutils import Vector

PROJ = r"D:\项目session\blender-supercar"
BLEND = os.path.join(PROJ, "LATEST", "v5_stage_anim.blend")

bpy.ops.wm.open_mainfile(filepath=BLEND)

GROUPS = {
    "V5_01_Road": ("V5_Track", "V5_RacingLine", "V5_Line_", "V5_Kerb_",
                   "V5_StartLine", "V5_PitLane", "V5_PitLine", "V5_PitBoxLine"),
    "V5_02_Terrain": ("V5_Ground", "V5_Verge_", "V5_Gravel_", "V5_HedgeRing", "V5_SkyDome"),
    "V5_03_Barriers": ("V5_Barrier", "V5_FencePosts"),
    "V5_04_Stands": ("V5_Stand_", "V5_Flag_"),
    "V5_05_Pit": ("V5_PitWall", "V5_PitGarage", "V5_PitRoof", "V5_PitTop"),
    "V5_06_Props": ("V5_Ad_", "V5_Brake_", "V5_Screen_", "V5_Bridge_",
                    "V5_Marshal_", "V5_FieldMasts", "V5_Hangar_",
                    "V5_Gantry", "V5_StartLight"),
    "V5_07_Lighting": ("LGT_V5",),
}

# ---------- 1. 原点归位 ----------
moved = 0
for ob in list(bpy.data.objects):
    if ob.type != 'MESH':
        continue
    if not (ob.name.startswith("V5_") or ob.name.startswith("GEO_Race")):
        continue
    if len(ob.data.vertices) == 0:
        continue
    bb = [ob.matrix_world @ Vector(c) for c in ob.bound_box]
    c = Vector((sum(v.x for v in bb) / 8.0, sum(v.y for v in bb) / 8.0, sum(v.z for v in bb) / 8.0))
    inv = ob.matrix_world.inverted()
    local_c = inv @ c
    for v in ob.data.vertices:
        v.co -= local_c
    ob.location = c
    ob.data.update()
    moved += 1
print("origin_to_geometry:", moved, "objects")

# ---------- 2. 集合分组 ----------
def bucket(name):
    for g, prefixes in GROUPS.items():
        for p in prefixes:
            if name.startswith(p):
                return g
    return None

root = bpy.context.scene.collection
cols = {}
for g in GROUPS:
    c = bpy.data.collections.get(g) or bpy.data.collections.new(g)
    if c.name not in root.children:
        root.children.link(c)
    cols[g] = c

regrouped = 0
for ob in list(bpy.data.objects):
    g = bucket(ob.name)
    if not g:
        continue
    # 从所有集合移除（保留在场景里）
    for c in list(ob.users_collection):
        c.objects.unlink(ob)
    cols[g].objects.link(ob)
    regrouped += 1
print("regrouped:", regrouped, "objects")

print("collections:", [c.name for c in bpy.data.collections if c.name.startswith("V5_")])

bpy.ops.wm.save_as_mainfile(filepath=BLEND)
print("SAVED:", BLEND)
