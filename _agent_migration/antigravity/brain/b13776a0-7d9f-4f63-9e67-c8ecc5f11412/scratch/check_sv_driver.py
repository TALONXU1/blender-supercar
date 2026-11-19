import bpy
sc = bpy.context.scene
sc["sv_dimension"] = 1.0
sc.keyframe_insert('["sv_dimension"]', frame=10)
sc["sv_dimension"] = 2.0
sc.keyframe_insert('["sv_dimension"]', frame=20)
deps = bpy.context.evaluated_depsgraph_get()
for f in (10, 20):
    sc.frame_set(f)
    deps.update()
    sky_m = bpy.data.materials["V5_SkyDome"].evaluated_get(deps)
    car_m = bpy.data.materials["Mat_RedBull_MatteNavy"].evaluated_get(deps)
    sun_ev = bpy.data.objects["LGT_V5Sun"].evaluated_get(deps)
    print(
        f"f={f} sc_dim={sc['sv_dimension']} "
        f"sky_val={sky_m.node_tree.nodes['SV_Dimension_Input'].outputs[0].default_value} "
        f"car_val={car_m.node_tree.nodes['SV_Dimension_Input'].outputs[0].default_value} "
        f"sun_col={tuple(round(x,3) for x in sun_ev.data.color)} sun_E={round(sun_ev.data.energy,2)}"
    )
