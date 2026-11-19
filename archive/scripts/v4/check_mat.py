import bpy
bpy.ops.wm.open_mainfile(filepath=r"D:\项目session\blender-supercar\pipeline\v4_stage_anim.blend")
for name in ("Mat_DEC_Endplate_Mobil1","Mat_DEC_Engine_RedBull","Mat_DEC_RearWing_Front","Mat_PZero_Pirelli_Sidewall"):
    m = bpy.data.materials.get(name)
    print("==", name, "method", m.surface_render_method, "blend", m.blend_method, "transp_shadow", m.use_transparent_shadow, "backface", m.show_transparent_back)
    b = next((n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED'), None)
    if b:
        print("   alpha", b.inputs['Alpha'].default_value, "linked", b.inputs['Alpha'].is_linked,
              "emission", b.inputs['Emission Strength'].default_value)
    for l in m.node_tree.links:
        print("   link", l.from_node.name, l.from_socket.name, "->", l.to_node.name, l.to_socket.name)
