import bpy
from mathutils import Vector
for p in [r"D:\项目session\blender-supercar\LATEST\v5_stage_env.blend1", r"D:\项目session\blender-supercar\LATEST\v5_stage_env.blend", r"D:\项目session\blender-supercar\LATEST\v5_stage_anim.blend1", r"D:\项目session\blender-supercar\_unrelated\新建文件夹\v5_stage_env.blend"]:
    bpy.ops.wm.open_mainfile(filepath=p)
    n = 0; tot = 0
    for ob in bpy.data.objects:
        if ob.type == 'MESH' and ob.name.startswith("V5_"):
            tot += 1
            bb = [ob.matrix_world @ Vector(c) for c in ob.bound_box]
            c = sum(bb, Vector()) / 8
            if c.length < 1.0: n += 1
    print("PILE", p, n, "/", tot, "objs", len(bpy.data.objects))
