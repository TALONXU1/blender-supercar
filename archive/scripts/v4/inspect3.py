import bpy, json, math
from mathutils import Vector, Euler

bpy.ops.wm.open_mainfile(filepath=r"D:\项目session\blender-supercar\scifi_f1_2035.blend")
scene = bpy.context.scene
rig = bpy.data.objects["RIG_F1_Chassis"]
if rig.animation_data:
    rig.animation_data_clear()
for pb in rig.pose.bones:
    pb.location = (0, 0, 0)
    pb.rotation_mode = 'XYZ'
    pb.rotation_euler = (0, 0, 0)
    pb.scale = (1, 1, 1)
for o in bpy.data.objects:
    if o.animation_data:
        o.animation_data_clear()
bpy.context.view_layer.update()

def wbb(o):
    pts = [o.matrix_world @ Vector(c) for c in o.bound_box]
    mn = Vector((min(p[i] for p in pts) for i in range(3)))
    mx = Vector((max(p[i] for p in pts) for i in range(3)))
    return mn, mx

report = []
car_objs = [o for o in bpy.data.objects if o.type == 'MESH' and not o.name.startswith(("GEO_Track_", "GEO_F1_Ground", "GEO_F1_Drift", "LGT_", "Cam_"))]
mn = Vector((1e9,)*3); mx = Vector((-1e9,)*3)
for o in car_objs:
    a, b = wbb(o)
    mn = Vector((min(mn[i], a[i]) for i in range(3)))
    mx = Vector((max(mx[i], b[i]) for i in range(3)))
print("REST CAR BBOX", [round(v,3) for v in mn], [round(v,3) for v in mx], "size", [round(mx[i]-mn[i],3) for i in range(3)])

for side in ("FL","FR","RL","RR"):
    for nm in (f"GEO_F1_Tire_{side}", f"GEO_F1_WheelCover_{side}", f"GEO_F1_BrakeDisc_{side}", f"GEO_F1_Wheel_CenterNut_{side}"):
        o = bpy.data.objects.get(nm)
        if not o: continue
        a, b = wbb(o)
        print(f"{nm}: bbox {[round(v,3) for v in a]} {[round(v,3) for v in b]} loc {[round(v,3) for v in o.location]} rot {[round(math.degrees(v),1) for v in o.rotation_euler]} scl {[round(v,3) for v in o.scale]}")
        if nm.startswith("GEO_F1_Tire"):
            print("   mw", [[round(v,3) for v in r] for r in o.matrix_world])
            # analyze in wheel-local: convert vertices to bone rest space
            bname = f"Bone_Wheel_{side}"
            bone = rig.data.bones[bname]
            M = rig.matrix_world @ bone.matrix_local @ (o.parent.matrix_world.inverted() @ o.matrix_world) if False else None
            # object-space analysis: find principal axis by bbox extents
            xs=[v.co.x for v in o.data.vertices]; ys=[v.co.y for v in o.data.vertices]; zs=[v.co.z for v in o.data.vertices]
            print("   local extents x", round(min(xs),3), round(max(xs),3), "y", round(min(ys),3), round(max(ys),3), "z", round(min(zs),3), round(max(zs),3))
            # radius vs x in local space
            cy=(min(ys)+max(ys))/2; cz=(min(zs)+max(zs))/2
            import collections
            prof=collections.defaultdict(list)
            for v in o.data.vertices:
                prof[round(v.co.x,3)].append(math.hypot(v.co.y-cy, v.co.z-cz))
            ks=sorted(prof)
            print("   local profile (x: minr,maxr):", [(k, round(min(prof[k]),3), round(max(prof[k]),3)) for k in ks[::max(1,len(ks)//25)]])

print("--- track/ground objects ---")
for o in bpy.data.objects:
    if o.type == 'MESH' and o.name.startswith(("GEO_Track_", "GEO_F1_Ground", "GEO_F1_Drift")):
        a, b = wbb(o)
        print(o.name, [round(v,3) for v in a], [round(v,3) for v in b], "mat", [m.name for m in o.data.materials])

print("--- car parts rest bbox (biggest 30) ---")
parts = []
for o in car_objs:
    a, b = wbb(o)
    parts.append((o.name, a, b, len(o.data.vertices)))
for n, a, b, vc in sorted(parts, key=lambda x: -(x[2].x-x[1].x))[:30]:
    print(f"  {n}: {[round(v,2) for v in a]} {[round(v,2) for v in b]} v={vc}")

# aero/body scan: all objects z-range to find ground contact
print("--- lowest z objects ---")
for n,a,b,vc in sorted(parts, key=lambda x: x[1].z)[:10]:
    print("  ", n, round(a.z,3), round(b.z,3))

# object count by collection membership & unparented meshes
print("--- unparented meshes ---")
for o in bpy.data.objects:
    if o.type in ('MESH','CURVE') and o.parent is None:
        print("  ", o.name, "type", o.type)
