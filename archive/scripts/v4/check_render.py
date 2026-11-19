# -*- coding: utf-8 -*-
"""轻量侧视/前视验证渲染"""
import bpy, os, sys
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
blend = argv[0] if argv else r"D:\项目session\blender-supercar\pipeline\v4_stage_model.blend"
outdir = argv[1] if len(argv) > 1 else r"D:\项目session\blender-supercar\pipeline\preview"
tag = argv[2] if len(argv) > 2 else "chk"

bpy.ops.wm.open_mainfile(filepath=blend)
sc = bpy.context.scene
os.makedirs(outdir, exist_ok=True)

for o in list(bpy.data.objects):
    if o.type in ('CAMERA', 'LIGHT'):
        bpy.data.objects.remove(o, do_unlink=True)

sc.render.engine = 'BLENDER_EEVEE'
sc.eevee.taa_render_samples = 16
sc.render.resolution_x = 1100
sc.render.resolution_y = 620
sc.view_settings.view_transform = 'AgX'
try:
    sc.view_settings.look = 'High Contrast'
except Exception:
    pass
sc.view_settings.exposure = 0.1

w = sc.world or bpy.data.worlds.new("W")
sc.world = w
w.use_nodes = True
nt = w.node_tree
nt.nodes.clear()
bg = nt.nodes.new('ShaderNodeBackground')
bg.inputs[0].default_value = (0.42, 0.48, 0.58, 1)
bg.inputs[1].default_value = 0.85
ow = nt.nodes.new('ShaderNodeOutputWorld')
nt.links.new(bg.outputs[0], ow.inputs[0])

bpy.ops.mesh.primitive_plane_add(size=40, location=(0, 0, 0))
fl = bpy.context.object
mm = bpy.data.materials.new("FloorChk"); mm.use_nodes = True
bb = mm.node_tree.nodes["Principled BSDF"]
bb.inputs['Base Color'].default_value = (0.07, 0.07, 0.075, 1)
bb.inputs['Roughness'].default_value = 0.32
fl.data.materials.append(mm)

def area(loc, e, s, col=(1, 1, 1)):
    d = bpy.data.lights.new("L", 'AREA'); d.energy = e; d.size = s; d.color = col
    o = bpy.data.objects.new("L", d); sc.collection.objects.link(o)
    o.location = loc
    o.rotation_euler = (Vector((0, 0, 0.5)) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
area((4, 5, 5), 2600, 6)
area((-5, -1, 3), 1100, 7, (0.66, 0.78, 1))
area((-2, -7, 4), 2000, 4, (0.7, 0.85, 1))

cd = bpy.data.cameras.new("C"); cam = bpy.data.objects.new("C", cd)
sc.collection.objects.link(cam); sc.camera = cam

def shot(name, loc, look, lens):
    cam.location = Vector(loc)
    cam.rotation_euler = (Vector(look) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    cd.lens = lens
    sc.render.filepath = os.path.join(outdir, f"{tag}_{name}.jpg")
    bpy.ops.render.render(write_still=True)
    print("SHOT", name)

shot("side", (7.4, 0.1, 0.95), (0, 0.1, 0.48), 62)
shot("hero", (4.2, -4.6, 1.55), (0, 0.0, 0.45), 55)
shot("rear34", (-3.9, -5.0, 1.5), (0, -0.3, 0.5), 55)
print("DONE")