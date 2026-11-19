#!/bin/bash
# 把 After Hours 的高潮段落混到卡点动画上
FF=/c/Users/86052/scoop/shims/ffmpeg.exe
V="D:/项目session/blender-supercar/renders_v4/f1_merc_30s_nosound.mp4"
A="/d/CloudMusic/VipSongsDownload/The Weeknd - After Hours.mp3"
OUT="D:/项目session/blender-supercar/renders_v4/f1_merc_petronas_30s_beatcut.mp4"
START=240.814      # 8 拍 downbeat，与动画第 1 帧对齐
"$FF" -y -i "$V" -ss $START -t 30.0 -i "$A" \
  -filter_complex "[1:a]afade=t=out:st=29.0:d=1.0,volume=1.0[a]" \
  -map 0:v -map "[a]" -c:v copy -c:a aac -b:a 192k -shortest "$OUT" 2>&1 | tail -3
ls -la "$OUT"
