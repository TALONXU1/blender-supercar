import bpy
bpy.ops.wm.open_mainfile(filepath=r"D:\项目session\blender-supercar\pipeline\v4_stage_rig.blend")
rig = bpy.data.objects["RIG_F1_Race"]
for d in rig.animation_data.drivers:
    t = d.driver.variables[0].targets[0]
    print(d.data_path, d.array_index, "id=", t.id, "id_type=", t.id_type, "path=", t.data_path)
