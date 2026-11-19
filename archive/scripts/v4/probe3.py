import bpy
sc = bpy.context.scene
for vt in ("Standard","AgX","Filmic","Khronos PBR Neutral","False Color","Raw"):
    try:
        sc.view_settings.view_transform = vt
        print("OK", vt, "->", sc.view_settings.view_transform)
    except Exception as e:
        print("FAIL", vt, e)
try:
    sc.view_settings.look = "AgX - Punchy"
    print("look ok", sc.view_settings.look)
except Exception as e:
    print("look fail", e)
print("display device", sc.display_settings.display_device)
