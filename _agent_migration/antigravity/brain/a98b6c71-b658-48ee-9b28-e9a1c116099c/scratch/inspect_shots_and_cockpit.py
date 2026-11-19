# -*- coding: utf-8 -*-
import bpy
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view

scene = bpy.context.scene
rig = bpy.data.objects["RIG_F1_Race"]
deps = bpy.context.evaluated_depsgraph_get()

markers = sorted(scene.timeline_markers, key=lambda m: m.frame)
shots = []
for i, m in enumerate(markers):
    f0 = m.frame
    f1 = markers[i + 1].frame - 1 if i + 1 < len(markers) else scene.frame_end
    shots.append((m.name, f0, f1, m.camera))

car_objs = {o.name for o in bpy.data.objects if o.type in ('MESH', 'CURVE') and not o.name.startswith("V5_") and not o.name.startswith("GEO_Race")}

print("=== MULTI-POINT RAYCAST & FRAMING AUDIT (ALL 2161 FRAMES) ===")
for sname, f0, f1, cam in shots:
    occ_frames = []
    out_of_frame = []
    min_z = 999.0
    steers = []
    for f in range(f0, f1 + 1):
        scene.frame_set(f)
        deps.update()
        cam_eval = cam.evaluated_get(deps)
        rig_eval = rig.evaluated_get(deps)
        cpos = cam_eval.matrix_world.translation.copy()
        min_z = min(min_z, cpos.z)
        steers.append(float(rig_eval.get("steer", 0.0)))
        pb_head = rig_eval.pose.bones["Bone_Heading"]
        m_car = rig_eval.matrix_world @ pb_head.matrix
        # 3 sample points on car: center cockpit, front nose, rear wing
        pts = [
            m_car @ Vector((0.0, 0.0, 0.48)),
            m_car @ Vector((0.0, 1.5, 0.35)),
            m_car @ Vector((0.0, -1.5, 0.65)),
        ]
        if "Onboard" not in sname:
            uv = world_to_camera_view(scene, cam_eval, pts[0])
            if uv.z < 0.5 or uv.x < 0.02 or uv.x > 0.98 or uv.y < 0.02 or uv.y > 0.98:
                out_of_frame.append((f, round(uv.x, 2), round(uv.y, 2), round(uv.z, 2)))
            # Raycast to center
            vec = pts[0] - cpos
            dist = vec.length
            if dist > 0.8:
                d_unit = vec.normalized()
                cur = cpos + d_unit * 0.5
                rem = dist - 1.1
                while rem > 0.05:
                    hit, loc, norm, idx, hob, _ = scene.ray_cast(deps, cur, d_unit, distance=rem)
                    if not hit or hob is None:
                        break
                    if hob.name in car_objs or hob.name == "V5_SkyDome":
                        step = (loc - cur).length + 0.05
                        cur = loc + d_unit * 0.05
                        rem -= step
                        continue
                    occ_frames.append((f, hob.name, round((loc - cpos).length, 1), round(dist, 1)))
                    break
    print(f"{sname:25s} f={f0:4d}..{f1:4d} min_cam_z={min_z:5.2f} steer=[{min(steers):+5.1f}..{max(steers):+5.1f}] occ={len(occ_frames)} oof={len(out_of_frame)}")
    if occ_frames:
        by_ob = {}
        for f, obn, d1, d2 in occ_frames:
            by_ob.setdefault(obn, []).append((f, d1, d2))
        for obn, lst in by_ob.items():
            print(f"    OCC by {obn:24s}: {len(lst)} frames ({lst[0][0]}..{lst[-1][0]}) e.g. {lst[:3]}")
    if out_of_frame:
        print(f"    OOF: {len(out_of_frame)} frames ({out_of_frame[0]} .. {out_of_frame[-1]})")

# Verify steering wheel rotation direction
scene.frame_set(350)  # hairpin corner
deps.update()
rig_eval = rig.evaluated_get(deps)
sw_ob = bpy.data.objects["GEO_F1_ShiftLED_07"].evaluated_get(deps) # center top LED (x=0 in rest)
pb_body = rig_eval.pose.bones["Bone_Body"]
m_body_inv = (rig_eval.matrix_world @ pb_body.matrix).inverted()
led_in_body = m_body_inv @ sw_ob.matrix_world.translation
print(f"\nSteering check @ f=350: steer={rig_eval['steer']:.2f} deg, top center LED in body coords = {tuple(round(x,4) for x in led_in_body)} (if steer>0=left turn, x<0 means wheel turned left!)")
