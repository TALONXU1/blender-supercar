#!/bin/bash
# 白模成片合成：clay_frames -> 1080p H.264（无声版 / 纯配乐版 / F1 V6 遥测引擎混音版）
# 用法:
#   bash pipeline/mux_clay.sh            # 完整生成无声版 + 纯配乐版 + 引擎混音版
#   bash pipeline/mux_clay.sh --sfx-only # 复用已有无声版，仅重制 *_clay_sfx_1080p.mp4
set -e

FF=/c/Users/86052/scoop/shims/ffmpeg.exe
PY=$(command -v python || command -v python3)
PROJ="D:/项目session/blender-supercar"
FR="$PROJ/renders_v5/clay_frames"
AUD="$PROJ/renders_v5/audio_v5_90s.m4a"
SFX_WAV="$PROJ/renders_v5/sfx_engine_90s.wav"
SFX_MIX="$PROJ/renders_v5/audio_v5_sfx_mix_90s.m4a"
SILENT="$PROJ/renders_v5/f1_silverstone_clay_silent.mp4"
OUT="$PROJ/renders_v5/f1_silverstone_clay_1080p.mp4"
OUT_SFX="$PROJ/renders_v5/f1_silverstone_clay_sfx_1080p.mp4"

if [ "${1:-}" != "--sfx-only" ]; then
  # 1) 白模无声版
  "$FF" -hide_banner -loglevel warning -stats -y -framerate 24 -i "$FR/f_%04d.jpg" \
    -c:v libx264 -preset slow -crf 18 -pix_fmt yuv420p \
    -movflags +faststart "$SILENT"

  # 2) 白模纯配乐版（After Hours / 108 BPM）
  "$FF" -hide_banner -loglevel warning -y -i "$SILENT" -i "$AUD" \
    -map 0:v -map 1:a -c:v copy -c:a aac -ar 48000 -ac 2 -b:a 192k -shortest \
    -movflags +faststart "$OUT"
fi

# 3) 确保 F1 V6 引擎音轨与混音母带存在
if [ ! -f "$SFX_WAV" ]; then
  "$PY" "$PROJ/pipeline/synth_sfx.py"
fi

if [ ! -f "$SFX_MIX" ] || [ "$SFX_WAV" -nt "$SFX_MIX" ]; then
  "$FF" -hide_banner -loglevel warning -y -i "$AUD" -i "$SFX_WAV" \
    -filter_complex "[0:a]aresample=48000,pan=stereo|c0=c0|c1=c0,atrim=0:90.041667,asetpts=PTS-STARTPTS,volume=-3.8dB,equalizer=f=600:t=q:w=1.3:g=-2.2,equalizer=f=2200:t=q:w=1.5:g=-1.6[mus];[1:a]highpass=f=68:poles=2,volume=-3.2dB,asplit=2[sfx_sc][sfx_mix];[mus][sfx_sc]sidechaincompress=threshold=0.14:ratio=2.6:attack=12:release=190:makeup=1[mus_duck];[mus_duck][sfx_mix]amix=inputs=2:normalize=0,afade=t=in:st=0:d=0.08,afade=t=out:st=88.541667:d=1.5:curve=qsin,alimiter=limit=0.81:attack=4:release=45:level=disabled[outa]" \
    -map "[outa]" -c:a aac -b:a 256k -ar 48000 -ac 2 \
    -movflags +faststart "$SFX_MIX"
fi

# 4) 白模 + F1 引擎音效混音版
"$FF" -hide_banner -loglevel warning -y -i "$SILENT" -i "$SFX_MIX" \
  -map 0:v -map 1:a -c:v copy -c:a copy -shortest \
  -movflags +faststart "$OUT_SFX"

ls -la "$SILENT" "$OUT" "$SFX_MIX" "$OUT_SFX"
