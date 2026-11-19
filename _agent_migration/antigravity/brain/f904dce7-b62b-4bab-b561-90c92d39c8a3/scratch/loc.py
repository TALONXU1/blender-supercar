import bpy
for n in ("V5_Track", "V5_Ground", "V5_Verge_L", "V5_PitLane", "V5_Ad_0", "V5_Stand_Main_0", "V5_Stand_Main_Back", "V5_Flag_V5_Stand_Main_0", "V5_Stand_Main_Truss0"):
    ob = bpy.data.objects.get(n)
    if ob:
        print("LOC", n, tuple(round(x, 2) for x in ob.location), "v0", tuple(round(x, 2) for x in ob.data.vertices[0].co))
print("NOBJ", len(bpy.data.objects))
for m in ("V5_Flag_0", "V5_Flag_1"):
    mm = bpy.data.materials.get(m)
    if mm:
        b = [n for n in mm.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'][0]
        print("MAT", m, tuple(b.inputs['Base Color'].default_value))
