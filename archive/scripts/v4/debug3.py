import bpy
from mathutils import Vector
bpy.ops.wm.open_mainfile(filepath=r"D:\项目session\blender-supercar\pipeline\v4_stage_rig.blend")
rig = bpy.data.objects["RIG_F1_Race"]
rig["steer"] = 30.0
rig["wheel_spin"] = 1.0
rig["drs"] = 1.0
rig["brake_heat"] = 1.0
bpy.context.scene.frame_set(1)
bpy.context.view_layer.update()
dg = bpy.context.evaluated_depsgraph_get()
rev = rig.evaluated_get(dg)
for n in ("Bone_Hub_FL","Bone_Wheel_FL","Bone_DRS"):
    print("EVAL", n, [round(v,4) for v in rev.pose.bones[n].rotation_euler])
tire = bpy.data.objects["GEO_F1_Tire_FL"].evaluated_get(dg)
print("EVAL tire matrix", [[round(v,3) for v in tire.matrix_world[i]] for i in range(3)])
glow = bpy.data.materials["Mat_Brake_HeatGlow"].node_tree.nodes.get("Emission")
print("glow strength", glow.inputs['Strength'].default_value if glow else None)
