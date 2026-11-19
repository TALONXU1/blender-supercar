import bpy
bpy.ops.wm.open_mainfile(filepath=r"D:\项目session\blender-supercar\LATEST\v5_stage_env.blend")
for nm in ("V5_Stand_Main_Trusses","V5_Brake_0_Poles"):
    me = bpy.data.objects[nm].data
    print(nm)
    for v in me.vertices[:8]: print("  v", v.index, tuple(round(c,3) for c in v.co))
    for p in me.polygons[:6]: print("  f", tuple(p.vertices), round(p.area,4), tuple(round(c,2) for c in p.normal))
