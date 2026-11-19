# -*- coding: utf-8 -*-
"""骨架姿态验证：转向 / 滚转 / DRS / 悬挂"""
import bpy, sys, os
from mathutils import Vector

OUTDIR = r"D:\项目session\blender-supercar\pipeline\preview"
bpy.ops.wm.open_mainfile(filepath=r"D:\项目session\blender-supercar\pipeline\v4_stage_rig.blend")
scene = bpy.context.scene
os.makedirs(OUTDIR, exist_ok=True)
rig = bpy.data.objects["RIG_F1_Race"]

scene.render.engine = 'BLENDER_EEVEE'
scene.eevee.taa_render_samples = 24
scene.render.resolution_x = 1000
scene.render.resolution_y = 700
scene.view_settings.view_transform = 'AgX'
try:
    scene.view_settings.look = 'High Contrast'
except Exception:
    pass

# 简易三点光 + 地面
w = scene.world or bpy.data.worlds.new("W")
scene.world = w
w.use_nodes = True
nt = w.node_tree
nt.nodes.clear()
bg = nt.nodes.new('ShaderNodeBackground')
bg.inputs[0].default_value = (0.30, 0.36, 0.46, 1)
bg.inputs[1].default_value = 0.8
ow = nt.nodes.new('ShaderNodeOutputWorld')
nt.links.new(bg.outputs[0], ow.inputs[0])

bpy.ops.mesh.primitive_plane_add(size=30, location=(0, 0, 0))
fl = bpy.context.object
m = bpy.data.materials.new("Floor"); m.use_nodes = True
bs = m.node_tree.nodes["Principled BSDF"]
bs.inputs['Base Color'].default_value = (0.06, 0.06, 0.065, 1)
bs.inputs['Roughness'].default_value = 0.3
fl.data.materials.append(m)

def area(loc, e, s):
    d = bpy.data.lights.new("L", 'AREA'); d.energy = e; d.size = s
    o = bpy.data.objects.new("L", d); scene.collection.objects.link(o)
    o.location = loc
    o.rotation_euler = (Vector((0, 0, 0.5)) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
area((4, 4, 5), 2200, 5)
area((-5, -2, 3), 800, 6)
area((-2, -6, 4), 1500, 4)

cd = bpy.data.cameras.new("C"); cam = bpy.data.objects.new("C", cd)
scene.collection.objects.link(cam); scene.camera = cam
cd.lens = 65

def shoot(name, loc, look, lens=65):
    cam.location = Vector(loc)
    cam.rotation_euler = (Vector(look) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    cd.lens = lens
    scene.render.filepath = os.path.join(OUTDIR, name)
    bpy.ops.render.render(write_still=True)
    print("SHOT", name)

# 1) 静态基准
rig["steer"] = 0.0
rig["wheel_spin"] = 0.0
rig["drs"] = 0.0
bpy.context.view_layer.update()
shoot("rig_neutral.png", (3.6, 4.2, 1.5), (0, 0.2, 0.5), 55)

# 2) 大角度打方向 + DRS 打开 + 车轮滚动
rig["steer"] = 30.0
rig["wheel_spin"] = 1.2
rig["drs"] = 1.0
rig["brake_heat"] = 1.0
bpy.context.view_layer.update()
shoot("rig_steer30.png", (-2.6, 2.6, 0.55), (-0.85, 1.45, 0.36), 80)
shoot("rig_rear_drs.png", (-2.4, -3.9, 1.15), (0, -2.2, 0.95), 70)
shoot("rig_top_steer.png", (0.0, 3.0, 6.5), (0, 0.6, 0.4), 45)
print("RIG VALIDATION DONE")
