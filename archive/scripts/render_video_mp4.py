import bpy
import os
import shutil

def export_animation_video():
    blend_path = r"D:\项目session\blender-supercar\scifi_f1_2035.blend"
    bpy.ops.wm.open_mainfile(filepath=blend_path)
    scene = bpy.context.scene

    out_dir = r"D:\项目session\blender-supercar\final_renders"
    os.makedirs(out_dir, exist_ok=True)
    artifact_dir = r"C:\Users\86052\.gemini\antigravity\brain\fe45f8e6-8741-486f-93a1-a197a7712d30"

    cam_drift = bpy.data.objects.get("Cam_F1_Drift_Action")
    if cam_drift:
        scene.camera = cam_drift

    # 设置 EEVEE 引擎进行超流畅 1080P 30fps 视频导出
    scene.render.engine = 'BLENDER_EEVEE'
    scene.render.resolution_x = 1920
    scene.render.resolution_y = 1080
    scene.render.resolution_percentage = 100

    scene.render.image_settings.file_format = 'FFMPEG'
    scene.render.ffmpeg.format = 'MPEG4'
    scene.render.ffmpeg.codec = 'H264'
    scene.render.ffmpeg.constant_rate_factor = 'MEDIUM'
    scene.render.ffmpeg.ffmpeg_preset = 'GOOD'
    scene.render.fps = 30
    scene.frame_start = 1
    scene.frame_end = 150

    video_path = os.path.join(out_dir, "f1_drift_cinematic_1080p.mp4")
    scene.render.filepath = video_path

    print(f">>> Rendering 150-frame animation to {video_path}...")
    bpy.ops.render.render(animation=True)
    print("Video Render Finished!")

    # 拷贝到 Artifacts
    dst_video = os.path.join(artifact_dir, "f1_drift_cinematic_1080p.mp4")
    shutil.copy2(video_path, dst_video)
    print(f"Synced Video to Artifacts: {dst_video}")

if __name__ == '__main__':
    export_animation_video()
