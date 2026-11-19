# -*- coding: utf-8 -*-
import bpy, time

bpy.ops.wm.open_mainfile(filepath=r"D:\项目session\blender-supercar\LATEST\v5_stage_anim.blend")
sc = bpy.context.scene
sc.eevee.use_raytracing = False
sc.eevee.taa_render_samples = 16
sc.render.resolution_x = 1920
sc.render.resolution_y = 1080

vl = sc.view_layers[0]
vl.use_pass_normal = True
vl.use_pass_mist = True
vl.use_pass_z = True
vl.use_pass_emit = True
vl.use_pass_cryptomatte_object = True
sc.world.mist_settings.start = 12.0
sc.world.mist_settings.depth = 160.0

ng = bpy.data.node_groups.new("BenchComp53", 'CompositorNodeTree')
rl = ng.nodes.new("CompositorNodeRLayers")
flt = ng.nodes.new("CompositorNodeFilter")
kuw = ng.nodes.new("CompositorNodeKuwahara")
trn = ng.nodes.new("CompositorNodeTranslate")
scl = ng.nodes.new("CompositorNodeScale")
cry = ng.nodes.new("CompositorNodeCryptomatteV2")
mix = ng.nodes.new("ShaderNodeMix")
mix.data_type = 'RGBA'

for label, sock in [("Filter.Type", flt.inputs['Type']),
                    ("Kuwahara.Type", kuw.inputs['Type']),
                    ("Translate.ExtX", trn.inputs['Extension X']),
                    ("Scale.Type", scl.inputs['Type']),
                    ("Scale.FrameType", scl.inputs['Frame Type'])]:
    try:
        sock.default_value = "__INVALID__"
    except Exception as e:
        print(f"ENUM {label}: {e}")

print("Mix RGBA sockets:", [(idx, s.name, s.type, s.enabled) for idx, s in enumerate(mix.inputs)], "->", [(idx, s.name, s.type, s.enabled) for idx, s in enumerate(mix.outputs)])
print("Cryptomatte props: source=", cry.source, "layer_name=", cry.layer_name)

# Wire a realistic full test chain: RLayers -> Kuwahara(Size=5) + Filter(Kirsch) + Sep/Translate/Comb + Output
kuw.inputs['Size'].default_value = 5.0
flt.inputs['Type'].default_value = 'Kirsch'
trn.inputs['Extension X'].default_value = 'Extend'
trn.inputs['Extension Y'].default_value = 'Extend'
trn.inputs['X'].default_value = 5.0

sep = ng.nodes.new("CompositorNodeSeparateColor")
cmb = ng.nodes.new("CompositorNodeCombineColor")
ng.links.new(rl.outputs['Image'], kuw.inputs['Image'])
ng.links.new(kuw.outputs['Image'], sep.inputs['Image'])
ng.links.new(rl.outputs['Image'], trn.inputs['Image'])
sep2 = ng.nodes.new("CompositorNodeSeparateColor")
ng.links.new(trn.outputs['Image'], sep2.inputs['Image'])
ng.links.new(sep2.outputs['Red'], cmb.inputs['Red'])
ng.links.new(sep.outputs['Green'], cmb.inputs['Green'])
ng.links.new(sep.outputs['Blue'], cmb.inputs['Blue'])
ng.links.new(sep.outputs['Alpha'], cmb.inputs['Alpha'])

out = ng.nodes.new("NodeGroupOutput")
ng.interface.new_socket(name="Image", in_out='OUTPUT', socket_type='NodeSocketColor')
ng.links.new(cmb.outputs['Image'], out.inputs['Image'])
sc.compositing_node_group = ng
sc.use_nodes = True

sc.frame_set(350)
t0 = time.time()
sc.render.filepath = r"C:\Users\86052\.gemini\antigravity\brain\a98b6c71-b658-48ee-9b28-e9a1c116099c\scratch\bench_comp.jpg"
bpy.ops.render.render(write_still=True)
t1 = time.time()
sc.frame_set(700)
bpy.ops.render.render(write_still=True)
t2 = time.time()
print(f"BENCH cold={t1-t0:.2f}s warm={t2-t1:.2f}s")
