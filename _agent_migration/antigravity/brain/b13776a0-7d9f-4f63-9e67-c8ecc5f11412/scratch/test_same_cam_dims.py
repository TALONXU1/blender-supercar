import bpy, os
import numpy as np

sc = bpy.context.scene
sc.use_nodes = False
out = r"C:\Users\86052\.gemini\antigravity\brain\b13776a0-7d9f-4f63-9e67-c8ecc5f11412\scratch"
sc.render.resolution_x = 640
sc.render.resolution_y = 360
for i, d in enumerate((0.0, 1.0, 2.0)):
    f = 68 + i
    sc["sv_dimension"] = d
    sc.keyframe_insert('["sv_dimension"]', frame=f)
for i, d in enumerate((0.0, 1.0, 2.0)):
    f = 68 + i
    sc.frame_set(f)
    fp = os.path.join(out, f"dim_test_{i}.jpg")
    sc.render.filepath = fp
    bpy.ops.render.render(write_still=True)
    im = bpy.data.images.load(fp)
    arr = np.array(im.pixels[:], dtype=np.float32).reshape((360, 640, 4))[:, :, :3]
    # Note: Blender image pixels row 0 is BOTTOM, row 359 is TOP
    print(f"SAME CAM f={f} dim={d}: topSkyRGB={arr[260:].mean(axis=(0,1)).round(3)} botFgRGB={arr[:220].mean(axis=(0,1)).round(3)}")
