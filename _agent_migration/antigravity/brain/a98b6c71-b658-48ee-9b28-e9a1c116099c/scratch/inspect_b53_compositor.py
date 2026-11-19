# -*- coding: utf-8 -*-
import bpy, time

sc = bpy.context.scene
sc.render.engine = 'BLENDER_EEVEE'
sc.eevee.use_raytracing = False
sc.render.resolution_x = 1920
sc.render.resolution_y = 1080

vl = sc.view_layers[0]
for attr in ("use_pass_normal", "use_pass_mist", "use_pass_z", "use_pass_emit", "use_pass_cryptomatte_object"):
    print(f"ViewLayer.{attr} exists={hasattr(vl, attr)}")
    if hasattr(vl, attr):
        setattr(vl, attr, True)

print("World mist_settings:", [a for a in dir(sc.world.mist_settings) if not a.startswith("_")])

ng = bpy.data.node_groups.new("TestComp53", 'CompositorNodeTree')
candidates = [
    "CompositorNodeRLayers",
    "CompositorNodeKuwahara",
    "CompositorNodeFilter",
    "CompositorNodeSeparateColor",
    "CompositorNodeCombineColor",
    "CompositorNodeTranslate",
    "CompositorNodeScale",
    "CompositorNodeImage",
    "CompositorNodeGlare",
    "CompositorNodeCryptomatteV2",
    "CompositorNodeLensdist",
    "CompositorNodePixelate",
    "CompositorNodePosterize",
    "CompositorNodeRGBToBW",
    "CompositorNodeValToRGB",
    "ShaderNodeValToRGB",
    "CompositorNodeMath",
    "ShaderNodeMath",
    "CompositorNodeMixRGB",
    "ShaderNodeMix",
    "CompositorNodeValue",
    "ShaderNodeValue",
    "ShaderNodeTexCoord",
    "CompositorNodeTexture",
    "ShaderNodeVectorMath",
]

for cname in candidates:
    try:
        n = ng.nodes.new(cname)
        inps = [(i.name, i.type, getattr(i, "default_value", None)) for i in n.inputs]
        outs = [(o.name, o.type) for o in n.outputs]
        props = [p.identifier for p in n.bl_rna.properties if p.identifier not in bpy.types.Node.bl_rna.properties]
        print(f"OK {cname:30s}")
        print(f"   inputs : {[(a,b) for a,b,_ in inps]}")
        print(f"   outputs: {outs}")
        print(f"   props  : {props}")
        if cname in ("CompositorNodeKuwahara", "CompositorNodeFilter", "CompositorNodeSeparateColor", "CompositorNodeTranslate"):
            for i in n.inputs:
                if i.type == 'MENU' or hasattr(i, "default_value"):
                    try:
                        print(f"      input '{i.name}' ({i.type}) default={i.default_value!r}")
                    except Exception as e:
                        print(f"      input '{i.name}' err={e}")
    except Exception as e:
        print(f"NO {cname:30s} -> {e}")
