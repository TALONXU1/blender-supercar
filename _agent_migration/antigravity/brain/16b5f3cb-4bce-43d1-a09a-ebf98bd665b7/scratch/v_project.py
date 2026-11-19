import bpy, sys
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector
bpy.ops.wm.open_mainfile(filepath=r"D:\项目session\blender-supercar\LATEST\v5_stage_anim.blend")
sc = bpy.context.scene
for f in (700, 1500):
    sc.frame_set(f)
    cam = sc.camera
    cp = cam.matrix_world.translation
    print("FRAME", f, cam.name, "lens", round(cam.data.lens, 1), "dof", cam.data.dof.use_dof, cam.data.dof.aperture_fstop, "focus", cam.data.dof.focus_object.name if cam.data.dof.focus_object else cam.data.dof.focus_distance)
    hits = []
    for ob in bpy.data.objects:
        if ob.type != 'MESH' or not ob.name.startswith("V5_") or not ob.visible_get():
            continue
        me = ob.data
        mw = ob.matrix_world
        # check each vertex cluster: tall thin things. sample verts
        for i, v in enumerate(me.vertices):
            w = mw @ v.co
            p = world_to_camera_view(sc, cam, w)
            if 0 <= p.x <= 1 and 0.5 <= p.y <= 1 and p.z > 0 and w.z > 3.0:
                hits.append((ob.name, round(p.x * 1600), round((1 - p.y) * 900), round((w - cp).length, 1), round(w.z, 1)))
    seen = {}
    for h in hits:
        k = (h[0], h[1] // 40)
        if k not in seen or h[2] < seen[k][2]:
            seen[k] = h
    for h in sorted(seen.values(), key=lambda x: x[1]):
        print("  ", h)
