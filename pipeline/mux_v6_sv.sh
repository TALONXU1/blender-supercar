#!/bin/bash
# V6 Spider-Verse 3D Sky-Harbor Edition — Showcase Clips, Full Master & Split-Screen Muxer
# 100% V5 Isolation: reads renders_v5/* & audio/audio.wav read-only; writes ONLY to renders_v6/*.
#
# Usage:
#   bash pipeline/mux_v6_sv.sh --clips   # Auto-discover & mux 3x 4.0s showcase clips + 12.0s showcase reel
#   bash pipeline/mux_v6_sv.sh --full    # Build full 1281-frame 53.38s V6 Spider-Verse master MP4s
#   bash pipeline/mux_v6_sv.sh --split   # Build V5 vs V6 1080p split-screen comparison MP4
set -e

MODE="${1:---clips}"
FF=/c/Users/86052/scoop/shims/ffmpeg.exe
PY=$(command -v python || command -v python3)
PROJ="D:/项目session/blender-supercar"

OUT_DIR="$PROJ/renders_v6"
SV_WAV="$OUT_DIR/sfx_spiderverse_53s.wav"
SV_MIX="$OUT_DIR/audio_v6_sv_mix_53s.m4a"
mkdir -p "$OUT_DIR"

MANIFEST="$PROJ/v6_spiderverse/v6_shots_manifest.json"
if [ ! -f "$SV_WAV" ] || [ ! -f "$SV_MIX" ] || { [ -f "$MANIFEST" ] && [ "$MANIFEST" -nt "$SV_WAV" ]; }; then
  "$PY" "$PROJ/pipeline/synth_sfx_sv.py"
fi

if [ "$MODE" = "--clips" ]; then
  mapfile -t SPECS < <("$PY" "$PROJ/pipeline/synth_sfx_sv.py" --print-clips | tr -d '\r')
  if [ "${#SPECS[@]}" -lt 3 ]; then
    echo "Expected 3 clip specs from synth_sfx_sv.py --print-clips" >&2
    exit 1
  fi

  OUT_NAMES=(
    "$OUT_DIR/clip1_miles_1610.mp4"
    "$OUT_DIR/clip2_gwen_65.mp4"
    "$OUT_DIR/clip3_2099_impact.mp4"
  )
  DIRS=()
  FSTARTS=()
  NFRAMES=()

  for idx in 0 1 2; do
    IFS='|' read -r sd f0 nf ss dur <<< "${SPECS[$idx]}"
    cdir="$OUT_DIR/clips_frames/$sd"
    out_mp4="${OUT_NAMES[$idx]}"
    DIRS+=("$cdir")
    FSTARTS+=("$f0")
    NFRAMES+=("$nf")
    fade_st=$(awk "BEGIN {printf \"%.4f\", $dur - 0.045}")

    "$FF" -hide_banner -loglevel warning -y \
      -framerate 24 -start_number "$f0" -i "$cdir/f_%04d.jpg" \
      -ss "$ss" -t "$dur" -i "$SV_MIX" \
      -frames:v "$nf" \
      -af "afade=t=in:st=0:d=0.025,afade=t=out:st=${fade_st}:d=0.045,alimiter=limit=0.81:attack=4:release=45:level=disabled" \
      -map 0:v -map 1:a -c:v libx264 -preset slow -crf 17 -pix_fmt yuv420p \
      -c:a aac -b:a 256k -ar 48000 -ac 2 -movflags +faststart "$out_mp4"

    # Also write descriptive alias if subdir name differs (e.g. clip1_canyon_eau_rouge.mp4)
    alias_mp4="$OUT_DIR/${sd}.mp4"
    if [ "$alias_mp4" != "$out_mp4" ]; then
      cp -f "$out_mp4" "$alias_mp4"
    fi
  done

  REEL_MP4="$OUT_DIR/v6_spiderverse_showcase_12s.mp4"
  TMP_WAV="${TMPDIR:-/tmp}/v6_reel_12s_$$.wav"
  trap 'rm -f "$TMP_WAV"' EXIT
  "$PY" "$PROJ/pipeline/synth_sfx_sv.py" --reel-wav "$TMP_WAV"

  J1=$(( NFRAMES[0] - 1 ))
  J1B=$(( NFRAMES[0] ))
  J2=$(( NFRAMES[0] + NFRAMES[1] - 1 ))
  J2B=$(( NFRAMES[0] + NFRAMES[1] ))
  TOT_F=$(( NFRAMES[0] + NFRAMES[1] + NFRAMES[2] ))
  FADE_OUT_ST=$(awk "BEGIN {printf \"%.4f\", ($TOT_F / 24.0) - 0.25}")

  "$FF" -hide_banner -loglevel warning -y \
    -i "${OUT_NAMES[0]}" \
    -i "${OUT_NAMES[1]}" \
    -i "${OUT_NAMES[2]}" \
    -i "$TMP_WAV" \
    -filter_complex "[0:v][1:v][2:v]concat=n=3:v=1:a=0,rgbashift=rh=-12:bh=12:rv=4:bv=-4:enable='between(n,${J1},${J1B})+between(n,${J2},${J2B})',fade=t=out:st=${FADE_OUT_ST}:d=0.25[outv]" \
    -map "[outv]" -map 3:a \
    -c:v libx264 -preset slow -crf 17 -pix_fmt yuv420p \
    -c:a aac -b:a 256k -ar 48000 -ac 2 -movflags +faststart "$REEL_MP4"

  rm -f "$TMP_WAV"
  ls -la "${OUT_NAMES[@]}" "$REEL_MP4"

elif [ "$MODE" = "--full" ]; then
  FR_DIR="$OUT_DIR/frames"
  SILENT_MP4="$OUT_DIR/f1_silverstone_spiderverse_silent.mp4"
  FULL_MP4="$OUT_DIR/f1_silverstone_spiderverse_1080p.mp4"
  SKY_MP4="$OUT_DIR/v6_skyharbor_spiderverse_1080p.mp4"

  "$FF" -hide_banner -loglevel warning -stats -y -framerate 24 -i "$FR_DIR/f_%04d.jpg" \
    -c:v libx264 -preset slow -crf 17 -pix_fmt yuv420p \
    -movflags +faststart "$SILENT_MP4"

  "$FF" -hide_banner -loglevel warning -y -i "$SILENT_MP4" -i "$SV_MIX" \
    -map 0:v -map 1:a -c:v copy -c:a copy -shortest \
    -movflags +faststart "$FULL_MP4"

  cp -f "$FULL_MP4" "$SKY_MP4"
  ls -la "$SILENT_MP4" "$FULL_MP4" "$SKY_MP4"

elif [ "$MODE" = "--split" ]; then
  V5_SILENT="$PROJ/renders_v5/f1_silverstone_lap_silent.mp4"
  V6_SILENT="$OUT_DIR/f1_silverstone_spiderverse_silent.mp4"
  SPLIT_MP4="$OUT_DIR/f1_silverstone_v5_vs_v6_split_1080p.mp4"

  "$FF" -hide_banner -loglevel warning -stats -y \
    -t 53.375 -i "$V5_SILENT" -i "$V6_SILENT" -i "$SV_MIX" \
    -filter_complex "[0:v]crop=960:1080:480:0[left];[1:v]crop=960:1080:480:0[right];[left][right]hstack=inputs=2,drawbox=x=958:y=0:w=4:h=1080:color=white@0.92:t=fill[outv]" \
    -map "[outv]" -map 2:a \
    -c:v libx264 -preset slow -crf 17 -pix_fmt yuv420p \
    -c:a copy -shortest -movflags +faststart "$SPLIT_MP4"

  ls -la "$SPLIT_MP4"
else
  echo "Unknown mode: $MODE (expected --clips, --full, or --split)" >&2
  exit 1
fi
