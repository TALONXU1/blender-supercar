import bpy
bpy.ops.wm.open_mainfile(filepath=r"D:\项目session\blender-supercar\pipeline\base_v4.blend")
for c in bpy.data.collections:
    print(f"[{c.name}] {len(c.objects)}")
    for o in sorted(c.objects, key=lambda x: x.name):
        print("   ", o.name, o.type, "mats=", [m.name for m in o.data.materials] if o.type=='MESH' else '')
