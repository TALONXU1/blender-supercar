# -*- coding: utf-8 -*-
import bpy, numpy as np

bpy.ops.wm.open_mainfile(filepath=r"D:\项目session\blender-supercar\LATEST\v5_stage_anim.blend")
sc = bpy.context.scene
sc.eevee.use_raytracing = False
sc.eevee.taa_render_samples = 8
sc.render.resolution_x = 640
sc.render.resolution_y = 360

vl = sc.view_layers[0]
vl.use_pass_cryptomatte_object = True

rig = bpy.data.objects["RIG_F1_Race"]
car_names = [o.name for o in bpy.data.objects if o.type in ('MESH', 'CURVE') and (o.parent == rig or o.name.startswith(("GEO_F1_", "GEO_MERC_", "DEC_")))]

ng = bpy.data.node_groups.new("TestCrypto", 'CompositorNodeTree')
cry = ng.nodes.new("CompositorNodeCryptomatteV2")
cry.source = 'RENDER'
cry.scene = sc
cry.layer_name = f"{vl.name}.CryptoObject"
cry.matte_id = ",".join(car_names)

out = ng.nodes.new("NodeGroupOutput")
ng.interface.new_socket(name="Image", in_out='OUTPUT', socket_type='NodeSocketColor')
# Output Matte as grayscale image to verify coverage
cmb = ng.nodes.new("CompositorNodeCombineColor")
ng.links.new(cry.outputs['Matte'], cmb.inputs['Red'])
ng.links.new(cry.outputs['Matte'], cmb.inputs['Green'])
ng.links.new(cry.outputs['Matte'], cmb.inputs['Blue'])
cmb.inputs['Alpha'].default_value = 1.0
ng.links.new(cmb.outputs['Image'], out.inputs['Image'])

sc.compositing_node_group = ng
sc.use_nodes = True
sc.view_settings.view_transform = 'Standard'
sc.view_settings.exposure = 0.0

mks = sorted(sc.timeline_markers, key=lambda m: m.frame)
sc.camera = [m.camera for m in mks if m.frame <= 520][-1]
sc.frame_set(520)
out_p = r"C:\Users\86052\.gemini\antigravity\brain\a98b6c71-b658-48ee-9b28-e9a1c116099c\scratch\crypto_matte_test.png"
sc.render.image_settings.file_format = 'PNG'
sc.render.filepath = out_p
bpy.ops.render.render(write_still=True)

im = bpy.data.images.load(out_p)
px = np.array(im.pixels[:]).reshape((360, 640, 4))[..., 0]
print(f"Crypto matte @ f=520: min={px.min():.3f} max={px.max():.3f} car_area_pct={(px > 0.5).mean()*100:.2f}% str_len={len(cry.matte_id)}")
