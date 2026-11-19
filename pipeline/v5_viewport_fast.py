# -*- coding: utf-8 -*-
"""
视口加速开关：把重物件在视口里降级，渲染完全不受影响。

用法:
  blender -b LATEST/v5_stage_anim.blend -P pipeline/v5_viewport_fast.py -- fast
  blender -b LATEST/v5_stage_anim.blend -P pipeline/v5_viewport_fast.py -- normal

fast   : 看台/道具/地形集合视口隐藏 + 重网格只显示包围盒（BOUNDS）
normal : 恢复实体贴图显示（TEXTURED）

注意：改的是 hide_viewport / display_type（仅对 MESH 生效，跳过 EMPTY 组件父物体），
渲染（F12 / 命令行动画渲染）不受任何影响。默认写回当前打开的 .blend（传 --no-save 可跳过保存）。
"""
import bpy
import sys

ARGV = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
MODE = (ARGV[0] if ARGV and not ARGV[0].startswith("--") else "fast").lower()
NO_SAVE = "--no-save" in ARGV

HEAVY_COLLS = ("V5_04_Stands", "V5_06_Props", "V5_02_Terrain")
HEAVY_OBJ_PREFIX = (
    "V5_Stand_", "V5_Ad_", "V5_Brake_", "V5_Marshal_",
    "V5_Screen_", "V5_Bridge_", "V5_Hangar_", "V5_Gantry",
    "V5_Pit", "V5_Barrier", "V5_FencePosts", "V5_DRS",
    "V5_Apex", "V5_Bollard", "V5_Sausage", "EM_",
)

fast = MODE.startswith("fast")

# 1) 集合视口显隐
for c in bpy.data.collections:
    if c.name in HEAVY_COLLS:
        c.hide_viewport = fast

# 2) 重网格显示模式（仅对 MESH 设置 display_type，兼容 EM_* / V5_* Empty 组件父子层级）
changed = 0
empties_checked = 0
for ob in bpy.data.objects:
    if ob.type == 'EMPTY' and ob.name.startswith(("V5_", "EM_")):
        empties_checked += 1
        continue
    if ob.type != 'MESH':
        continue
    in_heavy_parent = (ob.parent is not None and ob.parent.type == 'EMPTY'
                       and ob.parent.name.startswith(("V5_", "EM_")))
    if not (ob.name.startswith(HEAVY_OBJ_PREFIX) or in_heavy_parent):
        continue
    ob.display_type = 'BOUNDS' if fast else 'TEXTURED'
    changed += 1

# 3) 视口采样（只影响交互视口，不影响最终渲染）
sc = bpy.context.scene
try:
    sc.eevee.taa_samples = 8 if fast else 16
except Exception:
    pass

hidden_colls = [c.name for c in bpy.data.collections
                if c.name in HEAVY_COLLS and c.hide_viewport]
print("viewport mode = %s | mesh display_type changed = %d | empties preserved = %d | collections hidden = %s"
      % ("fast" if fast else "normal", changed, empties_checked, hidden_colls))

if bpy.data.filepath and not NO_SAVE:
    bpy.ops.wm.save_mainfile()
    print("SAVED:", bpy.data.filepath)
