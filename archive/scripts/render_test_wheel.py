import bpy

blend_path = r"D:\项目session\blender-supercar\scifi_f1_2035.blend"
bpy.ops.wm.open_mainfile(filepath=blend_path)

scene = bpy.context.scene
cam = bpy.data.objects.get("Cam_F1_Aero_Wheel_Macro")
if cam:
    scene.camera = cam

scene.render.engine = 'CYCLES'
scene.cycles.device = 'GPU'
scene.cycles.samples = 128
scene.cycles.use_adaptive_sampling = True
scene.cycles.adaptive_threshold = 0.02
scene.cycles.use_denoising = True
scene.render.resolution_x = 1920
scene.render.resolution_y = 1080
scene.render.filepath = r"D:\项目session\blender-supercar\test_wheel_fixed.png"

# 启用 GPU OptiX / CUDA
cprefs = bpy.context.preferences.addons['cycles'].preferences
cprefs.get_devices()
for d in cprefs.devices:
    d.use = True
    print(f"Device: {d.name}, type: {d.type}, use: {d.use}")

bpy.ops.render.render(write_still=True)
print("TEST WHEEL RENDER DONE")
