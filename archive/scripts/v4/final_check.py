import bpy
bpy.ops.wm.open_mainfile(filepath=r"D:\项目session\blender-supercar\scifi_f1_2035_v4_racing.blend")
sc = bpy.context.scene
rig = bpy.data.objects.get("RIG_F1_Race")
print("FRAMES", sc.frame_start, sc.frame_end, "FPS", sc.render.fps, "RES", sc.render.resolution_x, sc.render.resolution_y)
print("CAMERA", sc.camera.name if sc.camera else None)
print("MARKERS", [(m.name, m.frame, m.camera.name if m.camera else None) for m in sc.timeline_markers])
print("RIG bones", len(rig.data.bones), "props", [k for k in rig.keys() if not k.startswith('_')])
print("OBJECTS", len(bpy.data.objects))
print("DRIVERS", len(rig.animation_data.drivers) if rig.animation_data else 0)
