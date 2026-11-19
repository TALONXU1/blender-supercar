import bpy
from mathutils import Vector
vl = bpy.context.view_layer
vl.update()
empties = [o for o in bpy.data.objects if o.type == 'EMPTY']
print("EMPTIES", len(empties), sorted(o.name for o in empties))
bad = []
for em in empties:
    kids = list(em.children)
    before = {k.name: k.matrix_world.translation.copy() for k in kids}
    em.location += Vector((10.0, -5.0, 2.0))
    vl.update()
    for k in kids:
        d = k.matrix_world.translation - before[k.name]
        if (d - Vector((10.0, -5.0, 2.0))).length > 1e-4:
            bad.append((em.name, k.name, tuple(d)))
    em.location -= Vector((10.0, -5.0, 2.0))
    vl.update()
    # center check: empty vs children's bbox center (xy)
    pts = [k.matrix_world @ Vector(c) for k in kids for c in k.bound_box]
    cx = (min(p.x for p in pts) + max(p.x for p in pts)) / 2
    cy = (min(p.y for p in pts) + max(p.y for p in pts)) / 2
    print("EMCTR %-20s kids=%2d dxy=%.2f" % (em.name, len(kids), ((em.location.x - cx) ** 2 + (em.location.y - cy) ** 2) ** 0.5))
print("MOVE BAD", bad)
print("COLLS", [c.name for c in bpy.data.collections])
for c in bpy.data.collections:
    if c.name.startswith("V5_0"):
        print("COLL", c.name, len(c.objects))
