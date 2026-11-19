import bpy, json, math
from mathutils import Vector

bpy.ops.wm.open_mainfile(filepath=r"D:\项目session\blender-supercar\scifi_f1_2035.blend")
scene = bpy.context.scene
out = {}

def wbb(o):
    pts = [o.matrix_world @ Vector(c) for c in o.bound_box]
    mn = Vector((min(p[i] for p in pts) for i in range(3)))
    mx = Vector((max(p[i] for p in pts) for i in range(3)))
    return [round(v,3) for v in mn], [round(v,3) for v in mx]

# wheel geometry cross-section
for name in ["GEO_F1_Tire_FL", "GEO_F1_WheelCover_FL", "GEO_F1_BrakeDisc_FL", "GEO_F1_Wheel_CenterNut_FL"]:
    o = bpy.data.objects.get(name)
    if not o: continue
    mn, mx = wbb(o)
    o2 = {"bbox_min": mn, "bbox_max": mx, "loc": [round(v,3) for v in o.location],
          "rot": [round(math.degrees(v),2) for v in o.rotation_euler], "scale": [round(v,3) for v in o.scale],
          "matrix_world": [[round(v,4) for v in row] for row in o.matrix_world],
          "verts": len(o.data.vertices), "polys": len(o.data.polygons)}
    out[name] = o2

# tire vertex distribution -> radial profile
o = bpy.data.objects["GEO_F1_Tire_FL"]
mw = o.matrix_world
c = mw @ Vector((0,0,0))
pts = [mw @ v.co for v in o.data.vertices]
# local axes: wheel axis assumed X (car lateral). compute extents
xs = [p.x for p in pts]; ys=[p.y for p in pts]; zs=[p.z for p in pts]
out["tire_extents"] = [round(min(xs),3), round(max(xs),3), round(min(ys),3), round(max(ys),3), round(min(zs),3), round(max(zs),3)]
# profile: for each ring of x, max radius about the axis (x)
prof = {}
for p in pts:
    key = round(p.x - c.x, 3)
    r = math.hypot(p.y - c.y, p.z - c.z)
    prof[key] = round(max(prof.get(key, 0), r), 3)
out["tire_profile_x_radius"] = dict(sorted(prof.items()))

# body object world bboxes (non-wheel)
parts = []
for o in bpy.data.objects:
    if o.type != 'MESH': continue
    if o.name.startswith(("GEO_F1_Blade_", "GEO_F1_Tire_WearIndicator_", "GEO_F1_MagSpoke_")): continue
    mn, mx = wbb(o)
    parts.append({"name": o.name, "bb": [mn, mx], "verts": len(o.data.vertices)})
out["parts"] = parts

# materials detail (key ones)
mats = {}
for m in bpy.data.materials:
    if not m.node_tree: continue
    info = {"nodes": [], "blend": m.blend_method if hasattr(m, "blend_method") else None}
    for n in m.node_tree.nodes:
        d = {"name": n.name, "type": n.type}
        if n.type == 'BSDF_PRINCIPLED':
            vals = {}
            for k in ("Base Color","Metallic","Roughness","IOR","Alpha","Emission Color","Emission Strength",
                      "Coat Weight","Coat Roughness","Anisotropic","Anisotropic Rotation","Specular IOR Level"):
                if k in n.inputs:
                    v = n.inputs[k].default_value
                    try: vals[k] = [round(x,4) for x in v]
                    except TypeError: vals[k] = round(v,4)
            d["inputs"] = vals
        if n.type == 'TEX_IMAGE' and n.image:
            d["image"] = n.image.name
            d["extension"] = n.extension
        info["nodes"].append(d)
    mats[m.name] = info
out["materials"] = mats

# render / color mgmt / world
r = scene.render
out["render"] = {"engine": r.engine, "res": [r.resolution_x, r.resolution_y], "percent": r.resolution_percentage,
                 "fps": r.fps, "filepath": r.filepath, "format": r.image_settings.file_format,
                 "samples_eevee": getattr(scene.eevee, "taa_render_samples", None),
                 "use_bloom": getattr(scene.eevee, "use_bloom", None)}
out["view"] = {"transform": scene.view_settings.view_transform, "look": scene.view_settings.look,
               "exposure": scene.view_settings.exposure, "gamma": scene.view_settings.gamma}
w = scene.world
out["world"] = {"name": w.name, "color": list(w.color) if w else None}
if w and w.node_tree:
    bg = next((n for n in w.node_tree.nodes if n.type == 'BACKGROUND'), None)
    if bg:
        out["world"]["strength"] = bg.inputs['Strength'].default_value
        out["world"]["color"] = list(bg.inputs['Color'].default_value)
    for n in w.node_tree.nodes:
        if n.type == 'TEX_SKY':
            out["world"]["sky"] = {k: getattr(n, k, None) for k in ("sky_type", "sun_elevation", "sun_rotation", "sun_intensity", "turbidity", "altitude")}

out["markers"] = [(m.name, m.frame) for m in scene.timeline_markers]
out["sun"] = {}
for o in bpy.data.objects:
    if o.type == 'LIGHT':
        out["sun"][o.name] = {"energy": o.data.energy, "color": list(o.data.color), "angle": getattr(o.data,'angle',None),
                              "rot": [round(math.degrees(v),1) for v in o.rotation_euler], "loc": [round(v,2) for v in o.location],
                              "shadow": o.data.use_shadow}

out["collections"] = {c.name: [o.name for o in c.objects] for c in bpy.data.collections}

print("JSON_START")
print(json.dumps(out, ensure_ascii=False))
print("JSON_END")
