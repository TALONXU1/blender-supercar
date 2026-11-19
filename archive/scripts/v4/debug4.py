import bpy
bpy.ops.wm.open_mainfile(filepath=r"D:\项目session\blender-supercar\pipeline\v4_stage_rig.blend")
rig = bpy.data.objects["RIG_F1_Race"]
# 清除所有驱动器后重建一个测试
for d in list(rig.animation_data.drivers):
    rig.animation_data.drivers.remove(d)
pb = rig.pose.bones["Bone_Hub_FL"]
fc = pb.driver_add("rotation_euler", 2)
drv = fc.driver
drv.type = 'SCRIPTED'
drv.expression = "steer*0.0174532925"
v = drv.variables.new(); v.name = "steer"; v.type = 'SINGLE_PROP'
v.targets[0].id_type = 'OBJECT'; v.targets[0].id = rig; v.targets[0].data_path = '["steer"]'
rig["steer"] = 30.0
bpy.context.view_layer.update()
print("orig", pb.rotation_euler[2], "valid", drv.is_valid, "simple", drv.is_simple_expression)
dg = bpy.context.evaluated_depsgraph_get()
print("eval", rig.evaluated_get(dg).pose.bones["Bone_Hub_FL"].rotation_euler[2])
print("prop", rig["steer"])
print("mute", fc.mute, "is_valid", fc.driver.is_valid)
print("has action", rig.animation_data.action)
print("drivers count", len(rig.animation_data.drivers))
