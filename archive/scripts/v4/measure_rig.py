import bpy, math
from mathutils import Vector
bpy.ops.wm.open_mainfile(filepath=r"D:\项目session\blender-supercar\pipeline\v4_stage_model.blend")
def bb(n):
    o=bpy.data.objects.get(n)
    if not o: return None
    pts=[o.matrix_world@Vector(c) for c in o.bound_box]
    return [round(min(p[i] for p in pts),3) for i in range(3)],[round(max(p[i] for p in pts),3) for i in range(3)]
for n in ["GEO_F1_Cockpit_SteeringWheel","GEO_F1_Steering_LCDScreen","GEO_F1_ShiftLED_00","GEO_F1_ShiftLED_14",
          "GEO_F1_RearWing_DRSFlap","GEO_F1_RearWing_DRS_Actuator","GEO_F1_RearWing_DRS_Piston",
          "GEO_F1_RearWing_Top_Bybit_PATCH","GEO_F1_Halo_Hoop","GEO_F1_AntiRollBar",
          "GEO_F1_Front_UpperArmFwd_L","GEO_F1_Rear_UpperArmFwd_L"]:
    print(n, bb(n))
# steering wheel normal
o=bpy.data.objects["GEO_F1_Cockpit_SteeringWheel"]
me=o.data; mw=o.matrix_world
n=Vector((0,0,0))
for p in me.polygons:
    n += (mw.to_3x3() @ p.normal) * p.area
n.normalize()
print("STEER WHEEL normal", [round(v,3) for v in n], "center", [round(v,3) for v in (sum((mw@Vector(c) for c in o.bound_box), Vector())/8)])
# list of all mesh objects count by prefix
from collections import Counter
print(Counter([o.name.split('_')[1] if '_' in o.name else o.name for o in bpy.data.objects if o.type=='MESH']).most_common(10))
print("total objects", len(bpy.data.objects))
