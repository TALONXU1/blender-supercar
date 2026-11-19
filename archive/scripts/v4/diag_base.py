import bpy, math, os, sys
from mathutils import Vector

BLEND = r"D:\项目session\blender-supercar\pipeline\base_v4.blend"
OUTDIR = r"D:\项目session\blender-supercar\pipeline\diag"
bpy.ops.wm.open_mainfile(filepath=BLEND)
scene = bpy.context.scene
os.makedirs(OUTDIR, exist_ok=True)

def wbb(o):
    pts = [o.matrix_world @ Vector(c) for c in o.bound_box]
    mn = Vector((min(p[i] for p in pts) for i in range(3)))
    mx = Vector((max(p[i] for p in pts) for i in range(3)))
    return mn, mx

mn = Vector((1e9,)*3); mx = Vector((-1e9,)*3)
car = []
for o in bpy.data.objects:
    if o.type == 'MESH' and o.name.startswith(("GEO_F1_", "DEC_")):
        car.append(o)
        a, b = wbb(o)
        mn = Vector((min(mn[i], a[i]) for i in range(3)))
        mx = Vector((max(mx[i], b[i]) for i in range(3)))
print("CAR BBOX", [round(v,3) for v in mn], [round(v,3) for v in mx], "size", [round(mx[i]-mn[i],3) for i in range(3)])
for side in ("FL","FR","RL","RR"):
    o = bpy.data.objects.get(f"GEO_F1_Tire_{side}")
    if o:
        a,b = wbb(o)
        print("TIRE", side, "center", [round((a[i]+b[i])/2,3) for i in range(3)], "size", [round(b[i]-a[i],3) for i in range(3)], "rot", [round(math.degrees(v),1) for v in o.rotation_euler])

# lights / cameras / world
print("CAMERAS", [o.name for o in bpy.data.objects if o.type=='CAMERA'])
print("LIGHTS", [(o.name, o.data.type, round(o.data.energy,1)) for o in bpy.data.objects if o.type=='LIGHT'])
print("WORLD", scene.world.name if scene.world else None)

# setup a 3-point studio + neutral gradient for diagnostic
scene.render.engine = 'BLENDER_EEVEE'
scene.eevee.taa_render_samples = 16
scene.render.resolution_x = 1200
scene.render.resolution_y = 800
scene.view_settings.view_transform = 'AgX'
try: scene.view_settings.look = 'AgX - Punchy'
except Exception: pass
scene.view_settings.exposure = 1.0

w = scene.world
w.use_nodes = True
nt = w.node_tree
for n in list(nt.nodes):
    nt.nodes.remove(n)
bg = nt.nodes.new('ShaderNodeBackground')
bg.inputs[0].default_value = (0.35, 0.42, 0.55, 1)
bg.inputs[1].default_value = 0.9
out = nt.nodes.new('ShaderNodeOutputWorld')
nt.links.new(bg.outputs[0], out.inputs[0])

# key light
for o in list(bpy.data.objects):
    if o.type == 'LIGHT':
        bpy.data.objects.remove(o, do_unlink=True)
def add_area(name, loc, energy, size, color=(1,1,1)):
    d = bpy.data.lights.new(name, 'AREA')
    d.energy = energy; d.size = size; d.color = color
    o = bpy.data.objects.new(name, d); scene.collection.objects.link(o)
    o.location = loc
    direction = Vector((0,0,0.5)) - Vector(loc)
    o.rotation_euler = direction.to_track_quat('-Z','Y').to_euler()
    return o
add_area("KEY", (6, -5, 7), 4000, 6, (1.0, 0.97, 0.92))
add_area("FILL", (-7, -2, 3), 1200, 8, (0.7, 0.82, 1.0))
add_area("RIM", (-2, 8, 4), 2500, 4, (0.75, 0.85, 1.0))

# ground
if not bpy.data.objects.get("GEO_Studio_Floor"):
    bpy.ops.mesh.primitive_plane_add(size=60, location=(0,0,0))
    fl = bpy.context.object; fl.name = "GEO_Studio_Floor"
else:
    fl = bpy.data.objects["GEO_Studio_Floor"]
m = bpy.data.materials.new("Mat_DiagFloor"); m.use_nodes = True
bsdf = m.node_tree.nodes["Principled BSDF"]
bsdf.inputs['Base Color'].default_value = (0.05, 0.05, 0.055, 1)
bsdf.inputs['Roughness'].default_value = 0.35
fl.data.materials.clear(); fl.data.materials.append(m)

cam_d = bpy.data.cameras.new("DCAM"); cam = bpy.data.objects.new("DCAM", cam_d)
scene.collection.objects.link(cam); scene.camera = cam
cam_d.lens = 60

def shoot(name, loc, look, lens=60):
    cam.location = Vector(loc)
    cam.rotation_euler = (Vector(look) - Vector(loc)).to_track_quat('-Z','Y').to_euler()
    cam_d.lens = lens
    scene.render.filepath = os.path.join(OUTDIR, name)
    bpy.ops.render.render(write_still=True)
    print("SHOT", name)

shoot("base_hero.png", (4.2, -4.6, 1.5), (0, 0, 0.45), 55)
shoot("base_front.png", (0, -7.5, 0.9), (0, 0, 0.5), 70)
shoot("base_side.png", (7.5, 0.2, 1.0), (0, 0.2, 0.5), 60)
shoot("base_top.png", (0, -0.01, 9), (0, 0, 0.3), 50)
shoot("base_wheel.png", (2.4, 1.9, 0.55), (0.95, 1.4, 0.36), 85)
print("DONE")
