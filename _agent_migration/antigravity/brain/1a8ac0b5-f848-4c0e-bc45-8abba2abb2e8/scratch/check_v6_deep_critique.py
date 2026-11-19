# -*- coding: utf-8 -*-
"""
Exact 3D Tire-to-TrackDeck Contact Check + Deep Art-Director Critique for V6 Sky-Harbor Iteration 1
"""
import bpy, os, json
from mathutils import Vector

PROJ = r"D:\项目session\blender-supercar"
SCRATCH = r"C:\Users\86052\.gemini\antigravity\brain\1a8ac0b5-f848-4c0e-bc45-8abba2abb2e8\scratch"
bpy.ops.wm.open_mainfile(filepath=os.path.join(PROJ, "v6_spiderverse", "v6_stage_anim_sv.blend"))
sc = bpy.context.scene
rig = bpy.data.objects["RIG_F1_Race"]
deck = bpy.data.objects.get("V6_TrackDeck")

print("Bone_Root rest matrix_local:\n", rig.data.bones["Bone_Root"].matrix_local)
print("Bone_Heading rest matrix_local:\n", rig.data.bones["Bone_Heading"].matrix_local)

# Check actual world vertices of GEO_F1_Tire_FL..RR vs closest point on V6_TrackDeck!
for f, label in [(1, "StartFlat"), (309, "Raidillon+13.5deg"), (635, "Bowl+17.4degBank"), (830, "Corkscrew-13.9deg"), (960, "Tunnel341kmh"), (1121, "HairpinMacro")]:
    sc.frame_set(f)
    dg = bpy.context.evaluated_depsgraph_get()
    deck_e = deck.evaluated_get(dg)
    rig_e = rig.evaluated_get(dg)
    errs = {}
    for wn in ("FL", "FR", "RL", "RR"):
        tob = bpy.data.objects[f"GEO_F1_Tire_{wn}"].evaluated_get(dg)
        mw = tob.matrix_world
        # Find vertex of tire closest to V6_TrackDeck surface!
        # Sample tire vertices in world space, project onto deck_e.closest_point_on_mesh
        min_signed_d = 999.0
        for v in list(tob.data.vertices)[::6]:
            pw = mw @ v.co
            ok, cp, norm, _ = deck_e.closest_point_on_mesh(deck_e.matrix_world.inverted() @ pw)
            if ok:
                cp_w = deck_e.matrix_world @ cp
                nw = (deck_e.matrix_world.to_3x3() @ norm).normalized()
                sd = (pw - cp_w).dot(nw)
                if sd < min_signed_d:
                    min_signed_d = sd
        errs[wn] = round(min_signed_d * 1000.0, 1)  # in millimeters! (+ = floating above deck, - = penetrating deck)
    pb_h = rig_e.pose.bones["Bone_Heading"]
    hm = rig_e.matrix_world @ pb_h.matrix
    print(f"Frame {f:>4} ({label:<18}): tire bottom signed clearance (mm) = {errs} | Heading Z-axis={[round(x,3) for x in hm.col[2][:3]]}")

# Also check Solidify outline thickness & ComicFX visibility at key still frames
for f in (81, 295, 401, 635, 1021, 1068, 1121):
    sc.frame_set(f)
    dg = bpy.context.evaluated_depsgraph_get()
    active_fx = []
    for o in bpy.data.collections["V6_09_ComicFX"].all_objects:
        oe = o.evaluated_get(dg)
        if oe.scale.length > 0.05 and not oe.hide_render:
            active_fx.append(f"{o.name}(s={round(oe.scale.x,2)})")
    print(f"Frame {f:>4} active ComicFX ({len(active_fx)}): {active_fx}")
