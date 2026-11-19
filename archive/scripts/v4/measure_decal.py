import bpy
from mathutils import Vector
bpy.ops.wm.open_mainfile(filepath=r"D:\项目session\blender-supercar\pipeline\base_v4.blend")
for o in bpy.data.objects:
    if o.name.startswith("DEC_") and not o.name.startswith("DEC_Tire"):
        mw=o.matrix_world
        print(o.name, "dim",[round(v,3) for v in o.dimensions], "loc",[round(v,3) for v in mw.translation],
              "axes", [tuple(round(v,2) for v in mw.col[i].to_3d()) for i in range(3)],
              "verts",len(o.data.vertices), "mats",[m.name for m in o.data.materials])
