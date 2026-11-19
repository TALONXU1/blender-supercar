import bpy, sys
from collections import Counter
print("=== FILE", bpy.data.filepath)
print("objects", len(bpy.data.objects))
def walk(c, d=0):
    print("  " * d + "COLL", c.name, "objs", len(c.objects), "children", len(c.children))
    for ch in c.children:
        walk(ch, d + 1)
walk(bpy.context.scene.collection)
for ob in bpy.data.objects:
    if not ob.name.startswith("V5_"):
        print("OB", ob.name, ob.type, "parent", ob.parent.name if ob.parent else None, ob.parent_type,
              ob.parent_bone, "loc", tuple(round(x, 3) for x in ob.location),
              "mods", [m.type for m in getattr(ob, 'modifiers', [])])
c = Counter(ob.type for ob in bpy.data.objects)
print(c)
