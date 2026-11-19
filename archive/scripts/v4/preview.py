# -*- coding: utf-8 -*-
"""通用预览渲染：给定 blend，搭建临时棚拍灯光并输出多机位静帧"""
import bpy, sys, os
from mathutils import Vector

argv = sys.argv
blend = argv[argv.index("--blend") + 1] if "--blend" in argv else r"D:\项目session\blender-supercar\pipeline\v4_stage_model.blend"
outdir = argv[argv.index("--outdir") + 1] if "--outdir" in argv else r"D:\项目session\blender-supercar\pipeline\preview"
tag = argv[argv.index("--tag") + 1] if "--tag" in argv else "p"
res = int(argv[argv.index("--res") + 1]) if "--res" in argv else 1200

bpy.ops.wm.open_mainfile(filepath=blend)
scene = bpy.context.scene
os.makedirs(outdir, exist_ok=True)

# 清掉旧摄影机/灯光（保留车）
for o in list(bpy.data.objects):
    if o.type in ('CAMERA',) or o.name.startswith("LGT_PREV"):
        bpy.data.objects.remove(o, do_unlink=True)
for o in list(bpy.data.objects):
    if o.type == 'LIGHT':
        bpy.data.objects.remove(o, do_unlink=True)

scene.render.engine = 'BLENDER_EEVEE'
scene.eevee.taa_render_samples = 48
scene.render.resolution_x = res
scene.render.resolution_y = int(res * 0.667)
scene.render.film_transparent = False
scene.view_settings.view_transform = 'AgX'
try:
    scene.view_settings.look = 'High Contrast'
except Exception:
    pass
scene.view_settings.exposure = 0.2

# 世界：渐变天空
w = scene.world or bpy.data.worlds.new("World_Prev")
scene.world = w
w.use_nodes = True
nt = w.node_tree
nt.nodes.clear()
bg = nt.nodes.new('ShaderNodeBackground')
grad = nt.nodes.new('ShaderNodeTexGradient')
grad.gradient_type = 'EASING'
mapping = nt.nodes.new('ShaderNodeMapping')
texco = nt.nodes.new('ShaderNodeTexCoord')
mapping.inputs['Rotation'].default_value = (1.5708, 0, 0)
nt.links.new(texco.outputs['Generated'], mapping.inputs['Vector'])
nt.links.new(mapping.outputs['Vector'], grad.inputs['Vector'])
ramp = nt.nodes.new('ShaderNodeValToRGB')
ramp.color_ramp.elements[0].color = (0.015, 0.020, 0.030, 1)
ramp.color_ramp.elements[1].color = (0.35, 0.45, 0.62, 1)
nt.links.new(grad.outputs['Fac'], ramp.inputs['Fac'])
nt.links.new(ramp.outputs['Color'], bg.inputs['Color'])
bg.inputs['Strength'].default_value = 0.9
out = nt.nodes.new('ShaderNodeOutputWorld')
nt.links.new(bg.outputs[0], out.inputs[0])

# 地面
fl = bpy.data.objects.get("GEO_Studio_Floor")
if fl is None:
    bpy.ops.mesh.primitive_plane_add(size=40, location=(0, 0, 0))
    fl = bpy.context.object
    fl.name = "GEO_Studio_Floor"
m = bpy.data.materials.get("Mat_PrevFloor") or bpy.data.materials.new("Mat_PrevFloor")
m.use_nodes = True
b = m.node_tree.nodes.get("Principled BSDF")
b.inputs['Base Color'].default_value = (0.045, 0.048, 0.055, 1)
b.inputs['Roughness'].default_value = 0.28
b.inputs['Metallic'].default_value = 0.2
fl.data.materials.clear()
fl.data.materials.append(m)
fl.location.z = 0.0

def area(name, loc, energy, size, color):
    d = bpy.data.lights.new(name, 'AREA')
    d.energy = energy
    d.size = size
    d.color = color
    o = bpy.data.objects.new(name, d)
    scene.collection.objects.link(o)
    o.location = loc
    o.rotation_euler = (Vector((0, 0, 0.55)) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    return o

area("LGT_PREV_Key", (5.0, 3.5, 6.0), 2600, 5.0, (1.0, 0.96, 0.90))
area("LGT_PREV_Fill", (-6.0, -1.0, 3.2), 900, 7.0, (0.62, 0.76, 1.0))
area("LGT_PREV_Rim", (-1.5, -6.5, 3.8), 2200, 4.0, (0.70, 0.85, 1.0))
area("LGT_PREV_Top", (0.0, 0.5, 7.5), 1600, 6.0, (1.0, 1.0, 1.0))

cam_d = bpy.data.cameras.new("PREV_CAM")
cam = bpy.data.objects.new("PREV_CAM", cam_d)
scene.collection.objects.link(cam)
scene.camera = cam
cam_d.clip_start = 0.02
cam_d.clip_end = 300

def shot(name, loc, look, lens=60, fstop=None):
    cam.location = Vector(loc)
    cam.rotation_euler = (Vector(look) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    cam_d.lens = lens
    if fstop:
        cam_d.dof.use_dof = True
        cam_d.dof.focus_distance = (Vector(look) - Vector(loc)).length
        cam_d.dof.aperture_fstop = fstop
    else:
        cam_d.dof.use_dof = False
    scene.render.filepath = os.path.join(outdir, f"{tag}_{name}.png")
    bpy.ops.render.render(write_still=True)
    print("SHOT", name)

shot("hero34", (3.9, -4.4, 1.55), (0.0, 0.05, 0.45), 55)
shot("front", (0.05, 6.6, 0.85), (0.0, 0.6, 0.50), 65)
shot("side", (6.8, 0.15, 1.05), (0.0, 0.15, 0.50), 60)
shot("rear34", (-3.7, -4.8, 1.5), (0.0, -0.2, 0.50), 55)
shot("top", (0.0, 0.0, 8.5), (0.0, 0.02, 0.3), 50)
shot("wheel", (2.15, 2.55, 0.62), (0.90, 1.45, 0.36), 90, 2.8)
shot("wheel2", (-2.4, 2.6, 0.5), (-0.90, 1.45, 0.36), 90, 2.8)
shot("detail_rear", (-1.5, -3.3, 0.75), (-0.5, -2.1, 0.55), 85, 4.0)
print("PREVIEW DONE")
