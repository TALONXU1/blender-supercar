# -*- coding: utf-8 -*-
import bpy, json
from mathutils import Vector

data = json.load(open(r"D:\项目session\blender-supercar\track_data\silverstone_track.json", encoding="utf-8"))
pts = [Vector((p["xy"][0], p["xy"][1], 0.0)) for p in data["points"]]
cx = sum(p.x for p in pts) / len(pts)
cy = sum(p.y for p in pts) / len(pts)
max_r = max(((p.x - cx)**2 + (p.y - cy)**2)**0.5 for p in pts)
print(f"Track center=({cx:.1f}, {cy:.1f}), max track radius from center={max_r:.1f} m")

# Check V5_HedgeRing min radius in current blend
hr = bpy.data.objects.get("V5_HedgeRing")
if hr:
    mw = hr.matrix_world
    rs = [(((mw @ v.co).x - cx)**2 + ((mw @ v.co).y - cy)**2)**0.5 for v in hr.data.vertices]
    print(f"V5_HedgeRing radius range from track center: {min(rs):.1f} .. {max(rs):.1f} m")

# Check V5_Stand_Complex_Rail closest distance to track centerline
sr = bpy.data.objects.get("V5_Stand_Complex_Rail")
if sr:
    mw = sr.matrix_world
    vs = [mw @ v.co for v in sr.data.vertices]
    print("V5_Stand_Complex_Rail world verts:", [(round(v.x,1), round(v.y,1), round(v.z,2)) for v in vs])
