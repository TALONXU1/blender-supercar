import bpy
import os
import shutil

def render_drift_showcase():
    print("=== RENDERING DRIFT SHOWCASE: CYCLES HERO STILLS & MP4 ANIMATION ===")
    blend_path = r"D:\项目session\blender-supercar\scifi_f1_2035.blend"
    bpy.ops.wm.open_mainfile(filepath=blend_path)
    scene = bpy.context.scene

    out_dir = r"D:\项目session\blender-supercar\final_renders"
    os.makedirs(out_dir, exist_ok=True)
    artifact_dir = r"C:\Users\86052\.gemini\antigravity\brain\fe45f8e6-8741-486f-93a1-a197a7712d30"

    # 设置主机位为漂移追踪相机
    cam_drift = bpy.data.objects.get("Cam_F1_Drift_Action")
    if cam_drift:
        scene.camera = cam_drift

    # 1. 渲染 3 张全质感 Cycles OptiX 高光帧
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'GPU'
    scene.cycles.samples = 96
    scene.cycles.use_adaptive_sampling = True
    scene.cycles.adaptive_threshold = 0.02
    scene.cycles.use_denoising = True
    scene.render.resolution_x = 1920
    scene.render.resolution_y = 1080
    scene.render.resolution_percentage = 100

    scene.view_settings.view_transform = 'AgX'
    try:
        scene.view_settings.look = 'AgX - High Contrast'
    except Exception:
        scene.view_settings.look = 'High Contrast'
    scene.view_settings.exposure = -4.2

    cprefs = bpy.context.preferences.addons['cycles'].preferences
    cprefs.get_devices()
    for d in cprefs.devices:
        if d.type in ['OPTIX', 'CUDA']:
            d.use = True
        else:
            d.use = False

    hero_frames = [
        (35, "f1_drift_f035_entry_braking.png"),
        (85, "f1_drift_f085_apex_countersteer.png"),
        (130, "f1_drift_f130_exit_acceleration.png"),
    ]

    for frame_num, fname in hero_frames:
        scene.frame_set(frame_num)
        fpath = os.path.join(out_dir, fname)
        scene.render.filepath = fpath
        print(f">>> [CYCLES] Rendering Drift Frame {frame_num} -> {fpath}...")
        bpy.ops.render.render(write_still=True)
        # 同步至 Artifacts
        dst = os.path.join(artifact_dir, fname)
        shutil.copy2(fpath, dst)
        print(f"Synced Artifact: {dst}")

    # 2. 渲染 150 帧完整漂移动画视频 (H.264 MP4, 30fps)
    print(">>> Rendering 150-frame Drift MP4 Animation Video via BLENDER_EEVEE_NEXT...")
    scene.render.engine = 'BLENDER_EEVEE_NEXT' if 'BLENDER_EEVEE_NEXT' in bpy.types.RenderEngine.bl_rna.properties['name'].enum_items else 'BLENDER_EEVEE'
    scene.render.image_settings.file_format = 'FFMPEG'
    scene.render.ffmpeg.format = 'MPEG4'
    scene.render.ffmpeg.codec = 'H264'
    scene.render.ffmpeg.constant_rate_factor = 'MEDIUM'
    scene.render.ffmpeg.ffmpeg_preset = 'REALTIME'
    scene.render.fps = 30
    scene.frame_start = 1
    scene.frame_end = 150

    video_fpath = os.path.join(out_dir, "f1_drift_cinematic_1080p.mp4")
    scene.render.filepath = video_fpath
    bpy.ops.render.render(animation=True)
    print(f"Drift Video Saved: {video_fpath}")

    # 复制视频至 Artifacts
    dst_video = os.path.join(artifact_dir, "f1_drift_cinematic_1080p.mp4")
    if os.path.exists(video_fpath):
        shutil.copy2(video_fpath, dst_video)
        print(f"Synced Video Artifact: {dst_video}")

    print("=== ALL DRIFT SHOWCASE OUTPUTS COMPLETED ===")

if __name__ == '__main__':
    render_drift_showcase()
