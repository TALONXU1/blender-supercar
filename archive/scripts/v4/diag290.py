import bpy, os
from mathutils import Vector
bpy.ops.wm.open_mainfile(filepath=r"D:\项目session\blender-supercar\pipeline\v4_stage_anim.blend")
sc = bpy.context.scene
sc.frame_set(290)
sc.render.use_motion_blur = False
sc.render.resolution_x = 900; sc.render.resolution_y = 560
sc.eevee.taa_render_samples = 12
out = r"D:\项目session\blender-supercar\renders_v4\test"
sc.render.filepath = os.path.join(out, "diag290_nomb.jpg")
bpy.ops.render.render(write_still=True)
# top view
cd = bpy.data.cameras.new("TOP"); cam = bpy.data.objects.new("TOP", cd)
sc.collection.objects.link(cam); sc.camera = cam
cd.type = 'ORTHO'; cd.ortho_scale = 12
rig = bpy.data.objects["RIG_F1_Race"]
p = rig.pose.bones["Bone_Root"].matrix.translation
cam.location = (p.x + 0.01, p.y, p.z + 20)
cam.rotation_euler = (0, 0, 0)
sc.render.filepath = os.path.join(out, "diag290_top.jpg")
bpy.ops.render.render(write_still=True)
print("OK")
