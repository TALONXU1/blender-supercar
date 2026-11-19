import bpy, os, sys

SRC = r"D:\项目session\blender-supercar\build_scifi_f1.py"
OUT = r"D:\项目session\blender-supercar\pipeline\base_v4.blend"

src = open(SRC, encoding="utf-8").read()
marker = "    # 18. 渲染输出"
idx = src.index(marker)
src = src[:idx] + "    return bpy.context.scene\n"
ns = {"__name__": "base_builder"}
exec(compile(src, SRC, "exec"), ns)
scene = ns["build_scifi_f1_detailed"]()

bpy.ops.wm.save_as_mainfile(filepath=OUT)
print("BASE SAVED", OUT)
print("OBJECTS", len(bpy.data.objects))
