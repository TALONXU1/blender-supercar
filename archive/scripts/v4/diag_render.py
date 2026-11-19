import bpy, math, os, sys
from mathutils import Vector

bpy.ops.wm.open_mainfile(filepath=r"D:\项目session\blender-supercar\scifi_f1_2035.blend")
scene = bpy.context.scene
rig = bpy.data.objects["RIG_F1_Chassis"]
if rig.animation_data:
    rig.animation_data_clear()
for pb in rig.pose.bones:
    pb.location = (0, 0, 0); pb.rotation_mode = 'XYZ'; pb.rotation_euler = (0, 0, 0); pb.scale = (1,1,1)
for o in bpy.data.objects:
    if o.animation_data:
        o.animation_data_clear()
bpy.context.view_layer.update()

def wbb(o):
    pts = [o.matrix_world @ Vector(c) for c in o.bound_box]
    mn = Vector((min(p[i] for p in pts) for i in range(3)))
    mx = Vector((max(p[i] for p in pts) for i in range(3)))
    return mn, mx

# hide ground for geometry check? keep
mn = Vector((1e9,)*3); mx = Vector((-1e9,)*3)
for o in bpy.data.objects:
    if o.type == 'MESH' and not o.name.startswith(("GEO_F1_Ground", "GEO_F1_Drift")):
        a, b = wbb(o)
        mn = Vector((min(mn[i], a[i]) for i in range(3)))
        mx = Vector((max(mx[i], b[i]) for i in range(3)))
ctr = (mn + mx) / 2
size = mx - mn
print("BBOX", mn, mx, "center", ctr, "size", size)

scene.render.engine = 'BLENDER_EEVEE'
scene.eevee.taa_render_samples = 8
scene.render.resolution_x = 900
scene.render.resolution_y = 700
scene.render.film_transparent = False
scene.view_settings.view_transform = 'Standard'
scene.view_settings.look = 'None'
scene.view_settings.exposure = 0
try:
    scene.view_settings.look = 'None'
except Exception as e:
    print(e)

cam_data = bpy.data.cameras.new("DIAG_CAM")
cam = bpy.data.objects.new("DIAG_CAM", cam_data)
scene.collection.objects.link(cam)
scene.camera = cam
cam_data.type = 'ORTHO'

outdir = r"D:\项目session\blender-supercar\pipeline\diag"
os.makedirs(outdir, exist_ok=True)

views = {
    "top":   (Vector((0, 0, 1)), 1.0),
    "front": (Vector((0, 1, 0)), 1.0),
    "side":  (Vector((1, 0, 0)), 1.0),
    "iso":   (Vector((1, 1, 0.8)).normalized(), 1.0),
}
for name, (dirv, pad) in views.items():
    dist = max(size) * 2.2
    cam.location = ctr + dirv * dist
    look = (ctr - cam.location).to_track_quat('-Z', 'Y')
    cam.rotation_euler = look.to_euler()
    cam_data.ortho_scale = max(size) * 1.25
    if name == "front":
        cam_data.ortho_scale = max(size.x, size.z) * 1.25
    scene.render.filepath = os.path.join(outdir, f"diag_{name}.png")
    bpy.ops.render.render(write_still=True)
    print("rendered", name)
print("DIAG DONE")
