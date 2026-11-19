import bpy, math
bpy.ops.wm.open_mainfile(filepath=r"D:\项目session\blender-supercar\pipeline\v4_stage_rig.blend")
rig = bpy.data.objects["RIG_F1_Race"]
tire = bpy.data.objects["GEO_F1_Tire_FL"]
def snap(tag):
    dg = bpy.context.evaluated_depsgraph_get()
    dg.update()
    pb = rig.pose.bones["Bone_Hub_FL"]
    print(tag, "hub rot", [round(math.degrees(v),2) for v in pb.rotation_euler],
          "tire world loc", [round(v,3) for v in tire.matrix_world.translation])
    print("   tire matrix rows", [[round(v,3) for v in tire.matrix_world[i]] for i in range(3)])
snap("rest")
rig["steer"] = 30.0
bpy.context.view_layer.update()
snap("steer30")
# check driver state
for pb in rig.pose.bones:
    ad = pb.animation_data
    if ad and ad.drivers:
        for d in ad.drivers:
            print("driver", pb.name, d.data_path, d.array_index, "valid", d.driver.is_valid, "expr", d.driver.expression, "simple", d.driver.is_simple_expression)
            for v in d.driver.variables:
                print("    var", v.name, v.targets[0].data_path, "value", v.targets[0].id.get(v.targets[0].data_path.strip('[]"')) if hasattr(v.targets[0].id,'get') else '?')
# depsgraph cycle warnings
print("depsgraph", bpy.context.evaluated_depsgraph_get())
