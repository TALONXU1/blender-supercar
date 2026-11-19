# -*- coding: utf-8 -*-
import json

J = json.load(open(r"C:\Users\86052\.gemini\antigravity\brain\1a8ac0b5-f848-4c0e-bc45-8abba2abb2e8\scratch\audit_round1_report.json", encoding="utf-8"))

print("=== 1. ENV BLEND ===")
eb = J["env_blend"]
print("total_objects:", eb["total_objects"], "total_meshes:", eb["total_meshes"])
print("orphan_meshes:", eb["orphan_meshes"])
print("orphan_materials:", eb["orphan_materials"])
print("root_scene_collection_objects:", eb["root_scene_collection_objects"])
print("empties count:", len(eb["empties"]))
for e in eb["empties"]:
    if not e["collections"] or "Scene Collection" in e["collections"]:
        print("  STRANDED EMPTY:", e)

print("\n=== 2. ANIM BLEND HYGIENE & MATERIALS ===")
ab = J["anim_blend"]
print("total_objects:", ab["total_objects"])
print("root_scene_collection_objects:", ab["root_scene_collection_objects"])
print("unlinked collections:", [k for k, v in ab["collections"].items() if not v["in_scene_tree"]])
print("orphan_meshes:", ab["orphan_meshes"])
print("orphan_materials:", ab["orphan_materials"])
print("missing_images:", ab["missing_images"])
print("all_images:", ab["images"])
print("broken_mat_slots:", ab["broken_mat_slots"])
print("overbright_mats:", ab["overbright_mats"])
print("road_spec_violations:", ab["road_spec_violations"])
print("car_light_receivers count:", len(ab["car_light_receivers"]), "items:", ab["car_light_receivers"])

print("\n=== 3. RIG BONES & DRIVERS ===")
rig = ab["rig"]
print("custom_props:", rig["custom_props"])
print("bones count:", len(rig["bones"]))
for b in rig["bones"]:
    print(f"  Bone {b['name']:<24} parent={str(b['parent']):<20} head={b['head_rest']} rot={b['rotation_mode']}")
print("rig drivers count:", len(rig["drivers"]))
for d in rig["drivers"]:
    print(f"  DRV {d['data_path']}[{d['array_index']}] = {d['expression']} | vars={d['vars']}")
print("other drivers count:", len(ab["other_drivers"]))
for d in ab["other_drivers"][:30]:
    print("  OTHER_DRV:", d)

print("\n=== 4. CAR MESHES & MATERIALS SUMMARY ===")
print("car_meshes count:", len(ab["car_meshes"]))
# Group by material name!
mat_to_meshes = {}
for cm in ab["car_meshes"]:
    mnames = [m["name"] for m in cm["materials"]]
    for m in cm["materials"]:
        mn = m["name"]
        if mn not in mat_to_meshes:
            mat_to_meshes[mn] = {"meshes": [], "nodes": m.get("nodes", [])}
        mat_to_meshes[mn]["meshes"].append(f"{cm['name']}(p={cm['parent']}:{cm['parent_bone']})")
for mn, info in sorted(mat_to_meshes.items(), key=lambda x: str(x[0])):
    print(f"  MAT {mn} ({len(info['meshes'])} meshes): sample={info['meshes'][:5]}")
    for nd in info["nodes"]:
        if nd["type"] in ("BSDF_PRINCIPLED", "EMISSION", "TEX_IMAGE"):
            print(f"      node {nd}")

# Key car parts check (brake, steering, rainlight, tire, body, halo, decal)
print("\nKey car parts detail:")
for cm in ab["car_meshes"]:
    if any(k in cm["name"] for k in ("Brake", "Caliper", "Steering", "RainLight", "Exhaust", "Tire", "Nosecone", "EngineCowl", "Halo", "FrontWing_Main", "RearWing", "DRS", "DEC_", "MERC_")):
        print(f"  {cm['name']:<38} parent={cm['parent']}:{cm['parent_bone']} mods={cm['modifiers']} mats={[m['name'] for m in cm['materials']]}")

print("\n=== 5. CAMERA 26-SHOT AUDIT ===")
for s in ab["shot_audit"]:
    flags = []
    if s["occlusion_count"]:
        flags.append(f"OCCLUDED={s['occlusion_count']}")
    if s["low_cam_frames"]:
        flags.append(f"LOW_Z={s['low_cam_frames'][:3]}")
    if s["out_of_frustum_count"]:
        flags.append(f"OUT_FRUSTUM={s['out_of_frustum_count']}")
    if s["near_clip_hits"]:
        flags.append(f"NEAR_CLIP={len(s['near_clip_hits'])}")
    status = " | ".join(flags) if flags else "CLEAR"
    print(f"  {s['shot']:<25} f={s['f0']:>4}..{s['f1']:<4} minZ={s['min_cam_z']:>6.2f} fstop={s['fstop']:<4} maxFocusErr={s['max_focus_err_m']:>5.2f}m -> {status}")
    for occ in s["occlusions"][:8]:
        print(f"      OCC f={occ['frame']}: blocker={occ['blocker']} at {occ['blocker_dist']}m (car at {occ['car_dist']}m) cam={occ['cam_pos']}")
    for oof in s["out_of_frustum"][:5]:
        print(f"      OOF f={oof['frame']}: ndc={oof['ndc']}")
    for nc in s["near_clip_hits"][:5]:
        print(f"      NEAR_CLIP f={nc['frame']}: obj={nc['obj']} dist={nc['dist']}m")

print("\n=== 6. CLAY BLEND AUDIT ===")
cb = J["clay_blend"]
print("clay_car_count:", cb["clay_car_count"], "clay_env_count:", cb["clay_env_count"])
print("clay_non_v5_marked_as_env:", cb["clay_non_v5_marked_as_env"])
print("clay_v5_marked_as_car:", cb["clay_v5_marked_as_car"])
print("clay_other_objs:", cb["clay_other_objs"])
print("exposure_at_f100:", cb["exposure_at_f100"], "(v5_clay.py tried to set 0.20!)")
print("view_transform:", cb["view_transform"], "use_motion_blur:", cb["use_motion_blur"], "scene_has_anim_data:", cb["scene_has_anim_data"])
