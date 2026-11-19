import bpy
from mathutils import Vector

bpy.ops.wm.open_mainfile(filepath=r"D:\项目session\blender-supercar\LATEST\v5_stage_anim.blend")
at_origin = []
track = bpy.data.objects["V5_Track"]
print("V5_Track location:", tuple(round(x, 1) for x in track.location))

for ob in bpy.data.objects:
    if ob.type == 'MESH' and ob.name.startswith("V5_"):
        bb = [ob.matrix_world @ Vector(c) for c in ob.bound_box]
        c = Vector((sum(v.x for v in bb)/8, sum(v.y for v in bb)/8, sum(v.z for v in bb)/8))
        if c.length < 1.0:
            at_origin.append(ob.name)

print(f"V5_ objects piled at (0,0,0): {len(at_origin)} out of {sum(1 for o in bpy.data.objects if o.type=='MESH' and o.name.startswith('V5_'))}")
print("Sample of objects piled at (0,0,0):", sorted(at_origin)[:40])
