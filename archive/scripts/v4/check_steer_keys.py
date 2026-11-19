import bpy
bpy.ops.wm.open_mainfile(filepath=r"D:\项目session\blender-supercar\pipeline\v4_stage_anim.blend")
rig = bpy.data.objects["RIG_F1_Race"]
ad = rig.animation_data
act = ad.action
# Blender 5: fcurves via slots/layers
def iter_fcurves(action):
    try:
        for fc in action.fcurves:
            yield fc
    except Exception:
        for layer in action.layers:
            for strip in layer.strips:
                for bag in strip.channelbags:
                    for fc in bag.fcurves:
                        yield fc
for fc in iter_fcurves(act):
    if 'steer' in fc.data_path and 'ratio' not in fc.data_path:
        print("FC", fc.data_path)
        pts = [(round(k.co[0]), round(k.co[1],2)) for k in fc.keyframe_points if 228 <= k.co[0] <= 252]
        print(pts)
