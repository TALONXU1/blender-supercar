import bpy
bpy.ops.wm.open_mainfile(filepath=r"D:\项目session\blender-supercar\pipeline\base_v4.blend")
for name in ["DEC_Sidepod_Oracle_L","DEC_Nose_Livery","DEC_Engine_RedBull_L","DEC_RearWing_Back_RedBull","DEC_Endplate_Front_L","DEC_Halo_Top_Oracle"]:
    o=bpy.data.objects[name]; me=o.data
    print(name, "uvlayers", [l.name for l in me.uv_layers], "mats", [m.name for m in me.materials])
    for poly in me.polygons:
        for li in poly.loop_indices:
            vi=me.loops[li].vertex_index
            print("   v", vi, [round(v,3) for v in me.vertices[vi].co], "uv", [round(v,3) for v in me.uv_layers[0].data[li].uv])
    print("   smooth", [p.use_smooth for p in me.polygons])
