import bpy
from mathutils import Vector
bpy.ops.wm.open_mainfile(filepath=r"D:\项目session\blender-supercar\pipeline\v4_stage_model.blend")
for o in bpy.data.objects:
    if "Endplate" in o.name and o.type == 'MESH':
        pts=[o.matrix_world@Vector(c) for c in o.bound_box]
        mn=[round(min(p[i] for p in pts),2) for i in range(3)]
        mx=[round(max(p[i] for p in pts),2) for i in range(3)]
        print(o.name, "verts", len(o.data.vertices), "mats", [m.name for m in o.data.materials], "bb", mn, mx,
              "mods", [m.type for m in o.modifiers])
print("--- objects with decal materials ---")
for o in bpy.data.objects:
    if o.type=='MESH' and any(m and m.name.startswith("Mat_DEC") for m in o.data.materials):
        print(o.name, [m.name for m in o.data.materials], [round(v,2) for v in o.dimensions])
