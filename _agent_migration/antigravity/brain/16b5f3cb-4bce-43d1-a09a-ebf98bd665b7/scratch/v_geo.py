import bpy
bpy.ops.wm.open_mainfile(filepath=r"D:\项目session\blender-supercar\LATEST\v5_stage_env.blend")
from collections import Counter
for nm in ("V5_FencePosts", "V5_FieldMasts", "V5_Stand_Main_Trusses", "V5_Brake_0_Poles", "V5_PitBoxLines", "V5_Stand_Main_Flags"):
    ob = bpy.data.objects.get(nm)
    if not ob:
        print(nm, "MISSING"); continue
    me = ob.data
    ws, hs = Counter(), Counter()
    for p in me.polygons[:2000]:
        vs = [me.vertices[i].co for i in p.vertices]
        xs = [v.x for v in vs]; ys = [v.y for v in vs]; zs = [v.z for v in vs]
        w = round(((max(xs) - min(xs)) ** 2 + (max(ys) - min(ys)) ** 2) ** 0.5, 2)
        ws[w] += 1; hs[round(max(zs) - min(zs), 2)] += 1
    print(nm, "faces", len(me.polygons), "verts", len(me.vertices), "mats", [m.name for m in me.materials], "parent", ob.parent.name if ob.parent else None)
    print("   width hist", ws.most_common(5), " height hist", hs.most_common(5))
