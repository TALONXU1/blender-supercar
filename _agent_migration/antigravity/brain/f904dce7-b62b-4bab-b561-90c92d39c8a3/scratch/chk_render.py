import bpy, os
from mathutils import Vector
sc = bpy.context.scene
OUTD = r"C:\Users\86052\.gemini\antigravity\brain\f904dce7-b62b-4bab-b561-90c92d39c8a3\scratch"
bpy.context.view_layer.update()
cd = bpy.data.cameras.new("CHK")
cd.lens = 24
cd.clip_start = 0.5
cd.clip_end = 9000
cam = bpy.data.objects.new("CHK", cd)
sc.collection.objects.link(cam)
sc.camera = cam
sc.timeline_markers.clear()
sc.render.resolution_x = 1280
sc.render.resolution_y = 720
sc.eevee.taa_render_samples = 16
sc.render.use_motion_blur = False
for name, off in (("V5_Stand_Main", Vector((-45, -35, 14))), ("V5_Bridge_A", Vector((30, 25, 9))),
                  ("V5_Gantry", Vector((-25, 12, 6))), ("V5_Brake_0", Vector((25, -50, 12)))):
    em = bpy.data.objects[name]
    tgt = em.matrix_world.translation + Vector((0, 0, 4 if "Stand" in name else 2))
    # place camera in empty's local frame (x along track) so it's on the open side
    loc = em.matrix_world @ off
    cam.location = loc
    cam.rotation_euler = (tgt - loc).to_track_quat('-Z', 'Y').to_euler()
    sc.frame_set(40)
    sc.render.filepath = os.path.join(OUTD, f"chk_{name}.jpg")
    bpy.ops.render.render(write_still=True)
    print("CHK", name)
