import bpy
from mathutils import Vector
bpy.ops.wm.open_mainfile(filepath=r"D:\项目session\blender-supercar\pipeline\v4_stage_anim.blend")
sc = bpy.context.scene
sc.frame_set(20)
cam = sc.camera
print("cam", cam.name, [round(v,2) for v in cam.matrix_world.translation], "lens", cam.data.lens)
dg = bpy.context.evaluated_depsgraph_get()
rig = bpy.data.objects["RIG_F1_Race"]
print("car pos", [round(v,2) for v in rig.pose.bones["Bone_Root"].matrix.translation], "heading", round(rig.pose.bones["Bone_Heading"].rotation_euler.z,2))
res=[]
for o in bpy.data.objects:
    if o.type != 'MESH': continue
    if not (o.name.startswith("GEO_F1_") or o.name.startswith("DEC_")): continue
    ev = o.evaluated_get(dg)
    mw = ev.matrix_world
    pts=[mw @ Vector(c) for c in ev.bound_box]
    mn=Vector((min(p[i] for p in pts) for i in range(3)))
    mx=Vector((max(p[i] for p in pts) for i in range(3)))
    # 距离相机 2-5m 且尺寸>0.5
    d = (mn+mx)/2
    if (d - cam.matrix_world.translation).length < 6.0 and (mx-mn).length > 0.45:
        res.append((o.name, [round(v,2) for v in mn], [round(v,2) for v in mx], [m.name for m in o.data.materials]))
for r in sorted(res, key=lambda x: x[0]):
    print(r)
