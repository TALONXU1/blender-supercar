import bpy
bpy.ops.wm.open_mainfile(filepath=r"D:\项目session\blender-supercar\pipeline\v4_stage_rig.blend")
rig = bpy.data.objects["RIG_F1_Race"]
rig["steer"] = 30.0
rig["wheel_spin"] = 1.0
print("before", rig.pose.bones["Bone_Hub_FL"].rotation_euler[2])
for tag in ("update", "frame2", "tag"):
    if tag == "update":
        bpy.context.view_layer.update()
    elif tag == "frame2":
        bpy.context.scene.frame_set(5)
    else:
        rig.update_tag(); bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    print(tag, "eval hub", round(rig.evaluated_get(dg).pose.bones["Bone_Hub_FL"].rotation_euler[2],4),
          "eval wheel", round(rig.evaluated_get(dg).pose.bones["Bone_Wheel_FL"].rotation_euler[0],4))
# 强制重建依赖图
bpy.context.scene.frame_set(1)
bpy.context.view_layer.update()
# 逐个 driver 重新触发
for d in rig.animation_data.drivers:
    d.driver.is_valid  # touch
print("after touch", round(rig.evaluated_get(bpy.context.evaluated_depsgraph_get()).pose.bones["Bone_Hub_FL"].rotation_euler[2],4))
