import bpy, os
for f in sorted(os.listdir(r"D:\项目session\blender-supercar\textures")):
    p = os.path.join(r"D:\项目session\blender-supercar\textures", f)
    if not f.lower().endswith(('.png','.jpg','.jpeg')): continue
    img = bpy.data.images.load(p, check_existing=True)
    px = list(img.pixels[:16])
    print(f, "size", img.size[:], "channels", img.channels, "depth", img.depth, "alpha_mode", img.alpha_mode)
    print("   first px", [round(v,3) for v in px[:8]], "alpha", round(px[3],3))
