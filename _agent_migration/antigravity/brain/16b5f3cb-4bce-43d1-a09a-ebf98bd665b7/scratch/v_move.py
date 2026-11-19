# blender -b --factory-startup -P v_move.py -- <file.blend>
import bpy, sys
from mathutils import Vector, Matrix
src = sys.argv[sys.argv.index("--") + 1]
bpy.ops.wm.open_mainfile(filepath=src)
vl = bpy.context.view_layer
vl.update()
D = Vector((13.0, -7.0, 2.0))
fails, n_ok = [], 0
emps = [o for o in bpy.data.objects if o.type == 'EMPTY' and o.name.startswith("V5_")]
for e in emps:
    desc = list(e.children_recursive)
    if not desc:
        fails.append((e.name, "no children")); continue
    before = {o.name: o.matrix_world.copy() for o in desc}
    bb_before = {o.name: sum(((o.matrix_world @ Vector(c)) for c in o.bound_box), Vector()) / 8 for o in desc if o.type == 'MESH'}
    loc0 = e.location.copy()
    e.location = loc0 + D
    vl.update()
    bad = []
    for o in desc:
        dt = o.matrix_world.translation - before[o.name].translation
        if (dt - D).length > 1e-3:
            bad.append((o.name, tuple(round(x, 3) for x in dt)))
        if o.type == 'MESH':
            c = sum(((o.matrix_world @ Vector(cc)) for cc in o.bound_box), Vector()) / 8
            if ((c - bb_before[o.name]) - D).length > 1e-3:
                bad.append((o.name + " bbox", tuple(round(x, 3) for x in (c - bb_before[o.name]))))
    # rotation test: rotate 90deg about Z around the empty; child distance to empty must be preserved
    e.location = loc0
    vl.update()
    rot0 = e.rotation_euler.copy()
    e.rotation_euler.z += 1.5707963
    vl.update()
    ep = e.matrix_world.translation
    for o in desc:
        d0 = (before[o.name].translation - ep).length
        d1 = (o.matrix_world.translation - ep).length
        if abs(d0 - d1) > 1e-2:
            bad.append((o.name + " rot", round(d0, 3), round(d1, 3)))
    e.rotation_euler = rot0
    vl.update()
    # restored?
    for o in desc:
        if (o.matrix_world.translation - before[o.name].translation).length > 1e-3:
            bad.append((o.name + " not restored",))
    # constraints / drivers on children that could fight the parent
    for o in desc:
        if o.constraints:
            bad.append((o.name + " has constraints", [c.type for c in o.constraints]))
        if o.animation_data and (o.animation_data.action or o.animation_data.drivers):
            bad.append((o.name + " animated",))
    if bad:
        fails.append((e.name, len(desc), bad[:5]))
    else:
        n_ok += 1
    print("EMPTY %-28s children=%3d %s" % (e.name, len(desc), "OK" if not bad else "FAIL %s" % bad[:3]))
# meshes whose parent is not an empty
odd = [(o.name, o.parent.name, o.parent.type) for o in bpy.data.objects if o.name.startswith("V5_") and o.parent and o.parent.type != 'EMPTY']
print("V5 objects parented to non-empties:", odd[:20])
print("MOVE TEST: %d empties OK, %d FAIL" % (n_ok, len(fails)))
for f in fails:
    print("  FAIL", f)
