# Usage: blender -b --factory-startup -P v_dump.py -- <in.blend> <out.json> [frames]
import bpy, sys, json, hashlib
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:]
src, out = argv[0], argv[1]
frames = [int(x) for x in argv[2].split(",")] if len(argv) > 2 else [1, 40, 700, 1500, 2161]
bpy.ops.wm.open_mainfile(filepath=src)
sc = bpy.context.scene
sc.frame_set(sc.frame_start)
bpy.context.view_layer.update()

def r(v, n=4):
    return [round(float(x), n) for x in v]

def mesh_info(me):
    nv, nf = len(me.vertices), len(me.polygons)
    used = set()
    zero = 0
    dupf = 0
    seen = set()
    coords = [v.co.copy() for v in me.vertices]
    for p in me.polygons:
        used.update(p.vertices)
        if p.area < 1e-9:
            zero += 1
        key = tuple(sorted(tuple(round(c, 4) for c in coords[i]) for i in p.vertices))
        if key in seen:
            dupf += 1
        else:
            seen.add(key)
    h = hashlib.md5()
    for c in coords:
        h.update(("%.4f,%.4f,%.4f;" % tuple(c)).encode())
    for p in me.polygons:
        h.update((",".join(map(str, p.vertices)) + ";").encode())
    return dict(nv=nv, nf=nf, loose=nv - len(used), zero=zero, dupf=dupf, hash=h.hexdigest())

objs = {}
for ob in bpy.data.objects:
    d = dict(type=ob.type, parent=ob.parent.name if ob.parent else None,
             cols=[c.name for c in ob.users_collection],
             loc=r(ob.location), mw_t=r(ob.matrix_world.translation),
             mw=[r(row, 5) for row in ob.matrix_world],
             hide=(ob.hide_viewport, ob.hide_render, ob.hide_get() if ob.name in bpy.context.view_layer.objects else None),
             mods=[m.type for m in ob.modifiers])
    bb = [ob.matrix_world @ Vector(c) for c in ob.bound_box]
    mn = [min(v[i] for v in bb) for i in range(3)]
    mx = [max(v[i] for v in bb) for i in range(3)]
    d["bmin"], d["bmax"] = r(mn), r(mx)
    d["c"] = r([(mn[i] + mx[i]) / 2 for i in range(3)])
    if ob.type == 'MESH' and ob.data:
        d.update(mesh_info(ob.data))
        d["mats"] = [m.name if m else None for m in ob.data.materials]
        d["mesh"] = ob.data.name
    if ob.type == 'CAMERA':
        cd = ob.data
        d["cam"] = dict(lens=round(cd.lens, 4), sensor=round(cd.sensor_width, 4), clip=(round(cd.clip_start, 4), round(cd.clip_end, 2)),
                        dof=cd.dof.use_dof, fstop=round(cd.dof.aperture_fstop, 3))
    if ob.animation_data:
        ad = ob.animation_data
        d["action"] = ad.action.name if ad.action else None
        d["ndrivers"] = len(ad.drivers)
    objs[ob.name] = d

# animated world matrices at frames for cameras, armatures, car meshes
anim = {}
track = [o for o in bpy.data.objects if o.type in ('CAMERA', 'ARMATURE', 'LIGHT') or o.name.startswith(("GEO_", "DEC_", "RIG_", "CAR", "F1"))]
for f in frames:
    sc.frame_set(f)
    bpy.context.view_layer.update()
    fr = {}
    for o in track:
        fr[o.name] = [r(row, 4) for row in o.matrix_world]
    if sc.camera:
        fr["__active_cam"] = sc.camera.name
    for o in bpy.data.objects:
        if o.type == 'ARMATURE' and o.pose:
            for pb in o.pose.bones:
                fr["%s:%s" % (o.name, pb.name)] = [r(row, 4) for row in (o.matrix_world @ pb.matrix)]
    anim[f] = fr
sc.frame_set(sc.frame_start)

mats = {}
for m in bpy.data.materials:
    md = dict(users=m.users)
    if m.node_tree:
        nodes = []
        for n in sorted(m.node_tree.nodes, key=lambda n: n.name):
            ins = []
            for i in n.inputs:
                if hasattr(i, "default_value") and not i.is_linked:
                    v = i.default_value
                    try:
                        v = r(v, 4)
                    except TypeError:
                        v = round(float(v), 4) if isinstance(v, (int, float)) else str(v)
                    ins.append((i.identifier, v))
            nodes.append((n.bl_idname, n.name, ins))
        md["nodes"] = nodes
        md["links"] = sorted("%s.%s>%s.%s" % (l.from_node.name, l.from_socket.identifier, l.to_node.name, l.to_socket.identifier) for l in m.node_tree.links)
    mats[m.name] = md

def col_tree(c):
    return dict(name=c.name, n=len(c.objects), objs=sorted(o.name for o in c.objects),
                children=[col_tree(ch) for ch in c.children], hide_render=getattr(c, "hide_render", False))

world = None
if sc.world and sc.world.node_tree:
    world = sorted("%s" % n.bl_idname for n in sc.world.node_tree.nodes)

data = dict(file=src, nobj=len(bpy.data.objects), objects=objs, anim=anim, materials=mats,
            collections=col_tree(sc.collection), all_cols=sorted(c.name for c in bpy.data.collections),
            scene=dict(fs=sc.frame_start, fe=sc.frame_end, fps=sc.render.fps, engine=sc.render.engine,
                       res=(sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage),
                       camera=sc.camera.name if sc.camera else None,
                       markers=sorted([(m.frame, m.name, m.camera.name if m.camera else None) for m in sc.timeline_markers]),
                       view=sc.view_settings.view_transform, look=sc.view_settings.look,
                       exposure=round(sc.view_settings.exposure, 4), world=world),
            images=sorted(i.name for i in bpy.data.images))
with open(out, "w", encoding="utf-8") as fh:
    json.dump(data, fh)
print("DUMP OK", src, "->", out, "objects", len(objs))
