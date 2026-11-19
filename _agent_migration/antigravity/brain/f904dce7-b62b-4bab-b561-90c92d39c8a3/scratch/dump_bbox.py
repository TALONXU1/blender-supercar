import bpy, json, sys
from mathutils import Vector
OUT = sys.argv[sys.argv.index("--") + 1]
bpy.context.view_layer.update()
res = {}
for ob in bpy.data.objects:
    if ob.type != 'MESH' or not ob.name.startswith("V5_"):
        continue
    bb = [ob.matrix_world @ Vector(c) for c in ob.bound_box]
    mn = [min(v[i] for v in bb) for i in range(3)]
    mx = [max(v[i] for v in bb) for i in range(3)]
    me = ob.data
    used = set(i for p in me.polygons for i in p.vertices)
    keys = set()
    dup = 0
    for p in me.polygons:
        k = tuple(sorted(p.vertices))
        if k in keys:
            dup += 1
        keys.add(k)
    zero = sum(1 for p in me.polygons if p.area < 1e-8)
    res[ob.name] = dict(mn=mn, mx=mx, loose=len(me.vertices) - len(used), dup=dup, zero=zero,
                        nf=len(me.polygons), parent=ob.parent.name if ob.parent else None,
                        origin=list(ob.matrix_world.translation),
                        mats=[m.name if m else None for m in me.materials])
json.dump(res, open(OUT, "w"), indent=0)
print("DUMPED", len(res))
