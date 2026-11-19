import bpy
bpy.ops.wm.open_mainfile(filepath=r"D:\项目session\blender-supercar\pipeline\v4_stage_rig.blend")
rig = bpy.data.objects["RIG_F1_Race"]
ad = rig.animation_data
print("anim data", ad)
if ad:
    print("drivers", len(ad.drivers))
    for d in ad.drivers:
        print(" ", d.data_path, d.array_index, "valid", d.driver.is_valid, "simple", d.driver.is_simple_expression, "expr", d.driver.expression,
              "mute", d.mute, "vars", [(v.name, v.targets[0].data_path) for v in d.driver.variables])
print("PoseBone rotation_euler after frame_set")
rig["steer"] = 30.0
bpy.context.scene.frame_set(1)
bpy.context.view_layer.update()
for n in ("Bone_Hub_FL","Bone_Wheel_FL","Bone_DRS","Bone_Steering_Wheel"):
    pb = rig.pose.bones[n]
    print(n, [round(v,4) for v in pb.rotation_euler])
print("depsgraph update done")
