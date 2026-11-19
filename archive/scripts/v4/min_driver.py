import bpy
bpy.ops.wm.read_factory_settings(use_empty=True)
cube = bpy.data.objects.new("Cube", bpy.data.meshes.new("m"))
bpy.context.scene.collection.objects.link(cube)
cube["steer"] = 0.0
cube.driver_add("rotation_euler", 2).driver.expression = "steer*0.5"
v = cube.animation_data.drivers[0].driver.variables.new()
v.name = "steer"; v.type='SINGLE_PROP'; v.targets[0].id = cube; v.targets[0].data_path = '["steer"]'
cube["steer"] = 2.0
bpy.context.view_layer.update()
print("obj rot z", cube.rotation_euler[2])
dg = bpy.context.evaluated_depsgraph_get()
print("obj eval rot z", cube.evaluated_get(dg).rotation_euler[2])

arm = bpy.data.armatures.new("A"); rig = bpy.data.objects.new("Rig", arm)
bpy.context.scene.collection.objects.link(rig)
bpy.context.view_layer.objects.active = rig
bpy.ops.object.mode_set(mode='EDIT')
b = arm.edit_bones.new("B"); b.head=(0,0,0); b.tail=(0,1,0)
bpy.ops.object.mode_set(mode='OBJECT')
rig["steer"] = 0.0
pb = rig.pose.bones["B"]
pb.rotation_mode='XYZ'
fc = pb.driver_add("rotation_euler", 2)
fc.driver.expression = "steer*0.5"
v = fc.driver.variables.new(); v.name="steer"; v.type='SINGLE_PROP'
v.targets[0].id = rig; v.targets[0].data_path='["steer"]'
rig["steer"] = 2.0
bpy.context.view_layer.update()
dg = bpy.context.evaluated_depsgraph_get()
print("bone rot z orig", rig.pose.bones["B"].rotation_euler[2])
print("bone rot z eval", rig.evaluated_get(dg).pose.bones["B"].rotation_euler[2])
print("use_scripts", bpy.context.preferences.filepaths.use_scripts_auto_execute)
