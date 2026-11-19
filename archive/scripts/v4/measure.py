import bpy
from mathutils import Vector
bpy.ops.wm.open_mainfile(filepath=r"D:\项目session\blender-supercar\pipeline\v4_stage_model.blend")
def bb(n):
    o=bpy.data.objects.get(n)
    if not o: return None
    pts=[o.matrix_world@Vector(c) for c in o.bound_box]
    mn=[round(min(p[i] for p in pts),3) for i in range(3)]
    mx=[round(max(p[i] for p in pts),3) for i in range(3)]
    return mn,mx,len(o.data.vertices)
for n in ["GEO_F1_RearWing_Endplate_L","GEO_F1_RearWing_Endplate_R","GEO_F1_RearWing_Mainplane","GEO_F1_RearWing_DRSFlap",
          "GEO_F1_BeamWing_Lower","GEO_F1_Diffuser_Strake_0.14","GEO_F1_Diffuser_Strake_-0.58",
          "GEO_F1_FrontWing_Mainplane","GEO_F1_FrontWing_Endplate_L","GEO_F1_Nosecone","GEO_F1_EngineCowl_Body",
          "GEO_F1_Underbody_Floor","GEO_F1_Sidepod_IntakeLip_L","GEO_F1_Airbox_Scoop","GEO_F1_Halo_Hoop"]:
    print(n, bb(n))
print("DECALS:")
for o in bpy.data.objects:
    if o.name.startswith("DEC_") and not o.name.startswith("DEC_Tire"):
        print("  ", o.name, "dim", [round(v,3) for v in o.dimensions], "loc", [round(v,2) for v in o.matrix_world.translation], "verts", len(o.data.vertices))
