import bpy, os
from mathutils import Vector

p = r"D:\项目session\blender-supercar\LATEST\v5_stage_anim.blend"
bpy.ops.wm.open_mainfile(filepath=p)
deps = bpy.context.evaluated_depsgraph_get()

total_base_verts = 0
total_eval_verts = 0
heavy_eval = []
degenerate = []
by_loc = {}

for ob in bpy.data.objects:
    if ob.type == 'MESH' and ob.data:
        bv = len(ob.data.vertices)
        bf = len(ob.data.polygons)
        total_base_verts += bv
        eob = ob.evaluated_get(deps)
        eme = eob.to_mesh()
        ev = len(eme.vertices)
        ef = len(eme.polygons)
        eob.to_mesh_clear()
        total_eval_verts += ev
        if ev >= 2000:
            heavy_eval.append((ev, ef, bv, bf, ob.name, [m.type for m in ob.modifiers]))
        if bf == 0 or bv == 0:
            degenerate.append((ob.name, bv, bf))
        # check loose verts
        used_v = set()
        for poly in ob.data.polygons:
            used_v.update(poly.vertices)
        loose = bv - len(used_v)
        if loose > 0:
            degenerate.append((ob.name + f" (loose_verts={loose})", bv, bf))
        # check exact duplicate world bbox centers
        bb = [ob.matrix_world @ Vector(c) for c in ob.bound_box]
        center = tuple(round(sum(v[i] for v in bb)/8.0, 3) for i in range(3))
        dims = tuple(round(max(v[i] for v in bb) - min(v[i] for v in bb), 3) for i in range(3))
        key = (center, dims)
        by_loc.setdefault(key, []).append(ob.name)

print(f"Total base verts: {total_base_verts:,} | Total evaluated verts: {total_eval_verts:,}")
print("\nTop heavy evaluated meshes (>=2000 verts):")
for ev, ef, bv, bf, nm, mods in sorted(heavy_eval, reverse=True):
    print(f"  {nm:38s} base={bv:6d}v/{bf:5d}f -> eval={ev:7d}v/{ef:6d}f  mods={mods}")

print("\nDegenerate / loose-vert meshes:")
for item in degenerate:
    print(" ", item)

print("\nExact overlapping bbox (center + dims) groups:")
for k, names in by_loc.items():
    if len(names) > 1:
        print(f"  loc={k[0]} dims={k[1]} -> {names}")

print("\nRig bones & custom props:")
rig = bpy.data.objects.get("RIG_F1_Race")
if rig:
    print("  Bones:", [b.name for b in rig.data.bones])
    print("  Custom props:", {k: rig[k] for k in rig.keys() if not k.startswith("_")})
    if rig.animation_data and rig.animation_data.drivers:
        print("  Rig drivers:", len(rig.animation_data.drivers))

# Check drivers across all objects and materials
drv_count = 0
for datablock_coll_name in ("objects", "meshes", "materials", "lights", "cameras", "armatures"):
    for db in getattr(bpy.data, datablock_coll_name):
        ad = getattr(db, "animation_data", None)
        if ad and ad.drivers:
            drv_count += len(ad.drivers)
print("Total drivers in file:", drv_count)

# Check materials and images
unused_mats = [m.name for m in bpy.data.materials if m.users == 0]
print("Unused materials:", unused_mats)
print("Images:")
for img in bpy.data.images:
    print(f"  {img.name:30s} users={img.users} filepath={img.filepath} exists={os.path.exists(bpy.path.abspath(img.filepath)) if img.filepath else 'N/A'}")

# Check DEC_ and GEO_MERC materials/visibility
print("\nCar livery objects (DEC_* and GEO_MERC_*):")
for ob in sorted(bpy.data.objects, key=lambda x: x.name):
    if ob.name.startswith(("DEC_", "GEO_MERC_")):
        mats = [m.name if m else None for m in ob.data.materials]
        print(f"  {ob.name:34s} verts={len(ob.data.vertices):6d} mats={mats}")
