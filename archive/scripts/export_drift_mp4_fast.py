import bpy
import os
import subprocess
import shutil

def export_drift_video():
    print("=== EXPORTING 150-FRAME DRIFT VIDEO VIA EEVEE + FFMPEG ===")
    blend_path = r"D:\项目session\blender-supercar\scifi_f1_2035.blend"
    bpy.ops.wm.open_mainfile(filepath=blend_path)
    scene = bpy.context.scene

    out_frames_dir = r"D:\项目session\blender-supercar\drift_frames"
    os.makedirs(out_frames_dir, exist_ok=True)
    out_dir = r"D:\项目session\blender-supercar\final_renders"
    os.makedirs(out_dir, exist_ok=True)
    artifact_dir = r"C:\Users\86052\.gemini\antigravity\brain\fe45f8e6-8741-486f-93a1-a197a7712d30"

    cam_drift = bpy.data.objects.get("Cam_F1_Drift_Action")
    if cam_drift:
        scene.camera = cam_drift

    # 快速高质量渲染
    scene.render.engine = 'BLENDER_EEVEE'
    scene.render.resolution_x = 1920
    scene.render.resolution_y = 1080
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'JPEG'
    scene.render.image_settings.quality = 95
    scene.render.fps = 30
    scene.frame_start = 1
    scene.frame_end = 150

    scene.render.filepath = os.path.join(out_frames_dir, "frame_")

    print(">>> Rendering 150 frames...")
    bpy.ops.render.render(animation=True)
    print("Frames rendered!")

    # 用 ffmpeg 压制为高质量 H.264 MP4
    mp4_path = os.path.join(out_dir, "f1_drift_cinematic_1080p.mp4")
    if os.path.exists(mp4_path):
        os.remove(mp4_path)

    cmd = [
        r"C:\Users\86052\scoop\shims\ffmpeg.exe",
        "-y",
        "-framerate", "30",
        "-i", os.path.join(out_frames_dir, "frame_%04d.jpg"),
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-crf", "18",
        "-preset", "fast",
        mp4_path
    ]
    print(">>> Encoding MP4 video via ffmpeg...")
    subprocess.run(cmd, check=True)
    print(f"Video Encoded Successfully: {mp4_path}")

    # 同步至 Artifacts 目录
    dst_mp4 = os.path.join(artifact_dir, "f1_drift_cinematic_1080p.mp4")
    shutil.copy2(mp4_path, dst_mp4)
    print(f"Synced MP4 to Artifacts: {dst_mp4}")

if __name__ == '__main__':
    export_drift_video()
