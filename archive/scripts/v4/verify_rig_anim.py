import bpy, math
bpy.ops.wm.open_mainfile(filepath=r"D:\项目session\blender-supercar\pipeline\v4_stage_anim.blend")
sc = bpy.context.scene
rig = bpy.data.objects["RIG_F1_Race"]
for f in (1, 60, 120, 160, 200, 240, 280):
    sc.frame_set(f)
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    ev = rig.evaluated_get(dg)
    hub = ev.pose.bones["Bone_Hub_FL"]
    whl = ev.pose.bones["Bone_Wheel_FL"]
    drs = ev.pose.bones["Bone_DRS"]
    body = ev.pose.bones["Bone_Body"]
    print(f"f{f:3d} steer={math.degrees(hub.rotation_euler.z):7.2f}°  wheel_spin={math.degrees(whl.rotation_euler.x):9.1f}°  "
          f"drs={math.degrees(drs.rotation_euler.x):6.2f}°  pitch={math.degrees(body.rotation_euler.x):5.2f}°  "
          f"roll={math.degrees(body.rotation_euler.y):5.2f}°  props steer={rig['steer']:.1f} drs={rig['drs']:.2f} heat={rig['brake_heat']:.2f}")
# glow check
m = bpy.data.materials.get("Mat_Brake_HeatGlow")
em = next(n for n in m.node_tree.nodes if n.type=='EMISSION')
sc.frame_set(160); bpy.context.view_layer.update()
dg = bpy.context.evaluated_depsgraph_get()
print("glow at 160 (evaluated mat not accessible) raw", em.inputs['Strength'].default_value)
