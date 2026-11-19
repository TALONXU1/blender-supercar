# -*- coding: utf-8 -*-
import bpy, os
import numpy as np

PROJ = r"D:\项目session\blender-supercar"
SCRATCH = r"C:\Users\86052\.gemini\antigravity\brain\1a8ac0b5-f848-4c0e-bc45-8abba2abb2e8\scratch"
bpy.ops.wm.open_mainfile(filepath=os.path.join(PROJ, "v6_spiderverse", "v6_stage_anim_sv.blend"))
sc = bpy.context.scene

# 1. Check tunnel vault shadow setting & sun shadow
for nm in ("V6_StrobeTunnel_Vault", "V6_StrobeTunnel_Ribs", "V6_FauxVolumetric_GodRays"):
    ob = bpy.data.objects.get(nm)
    if ob:
        print(f"OBJ {nm}: visible_shadow={getattr(ob, 'visible_shadow', None)} mats={[m.name for m in ob.data.materials if m]}")

# 2. Render frame 635 (Act II where Kuwahara size=8.4, mix=0.92!) routing car_matte directly to Composite output -> scratch PNG!
ng = sc.compositing_node_group
cry = [n for n in ng.nodes if n.type == 'CRYPTOMATTE_V2'][0]
print("CryptomatteV2 node: source=", cry.source, "layer_name=", cry.layer_name, "matte_id len=", len(cry.matte_id), "sample=", cry.matte_id[:120])
print("Cryptomatte entries count:", len(cry.entries))

out_node = [n for n in ng.nodes if n.type in ('COMPOSITE', 'GROUP_OUTPUT')][0]
# Save original link, temporarily wire cry.outputs['Matte'] -> out_node.inputs['Image'] at 640x360 to test if car_matte is ZERO or WORKING!
sc.camera = bpy.data.objects["Cam_S12_BankedWallRailCam"]
sc.frame_set(635)
sc.render.resolution_x = 640
sc.render.resolution_y = 360
sc.eevee.taa_render_samples = 4
ng.links.new(cry.outputs['Matte'], out_node.inputs['Image'])
matte_path = os.path.join(SCRATCH, "test_car_matte_635.png")
sc.render.image_settings.file_format = 'PNG'
sc.render.filepath = matte_path
bpy.ops.render.render(write_still=True)

im = bpy.data.images.load(matte_path)
px = list(im.pixels)[0::4]  # R channel of Matte
nz = sum(1 for v in px if v > 0.05)
mx = max(px) if px else 0.0
print(f"CAR_MATTE TEST AT f=635: max={mx:.4f}, pixels>0.05 = {nz}/{len(px)} ({100.0*nz/max(1,len(px)):.2f}%)")
