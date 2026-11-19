import bpy
from mathutils import Vector
bpy.ops.wm.open_mainfile(filepath=r"D:\项目session\blender-supercar\pipeline\v4_stage_model.blend")
def bb(n):
    o=bpy.data.objects.get(n)
    if not o: return None
    pts=[o.matrix_world@Vector(c) for c in o.bound_box]
    return [round(min(p[i] for p in pts),3) for i in range(3)],[round(max(p[i] for p in pts),3) for i in range(3)]
for n in ["GEO_F1_RearWing_Endplate_Light_L","GEO_F1_RearWing_Endplate_Light_R","GEO_F1_FrontWing_Endplate_Light_L",
          "GEO_F1_Airbox_NeonRing","GEO_F1_FIA_RainLight","GEO_F1_Exhaust_InnerGlow","GEO_F1_Nose_NeonStripe",
          "GEO_F1_FloorEdge_Neon_L","GEO_F1_Overhead_TCam","GEO_F1_Halo_CenterPylon"]:
    print(n, bb(n))
# list patch objects
print([o.name for o in bpy.data.objects if o.name.endswith("_PATCH")])
