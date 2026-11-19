$S = "C:\Users\86052\.gemini\antigravity\brain\16b5f3cb-4bce-43d1-a09a-ebf98bd665b7\scratch"
$R = "$S\ref"
$B = "D:\APPs\steam\steamapps\common\Blender\blender.exe"
$L = "d:\项目session\blender-supercar\LATEST"
$tag = $args[0]
$O = "$S\run_$tag"
New-Item -ItemType Directory -Force $O | Out-Null
foreach ($n in @("v5_stage_env", "v5_stage_anim", "v5_stage_anim_clay")) {
  & $B -b --factory-startup -P "$S\v_dump.py" -- "$L\$n.blend" "$O\$n.json" 2>&1 | Select-String "DUMP|Error|Traceback"
}
& $B -b --factory-startup -P "$S\v_move.py" -- "$L\v5_stage_env.blend" 2>&1 | Select-String "EMPTY|MOVE TEST|FAIL|non-empties|Error|Traceback" | Out-File -Encoding utf8 "$O\move_env.txt"
& $B -b --factory-startup -P "$S\v_move.py" -- "$L\v5_stage_anim.blend" 2>&1 | Select-String "MOVE TEST|FAIL|non-empties|Error|Traceback" | Out-File -Encoding utf8 "$O\move_anim.txt"
python "$S\v_check.py" "$R\ref_env_1114.json" "$O\v5_stage_env.json" "$R\old_anim_1117.json" "$O\v5_stage_anim.json" "$R\old_clay_1117.json" "$O\v5_stage_anim_clay.json" | Out-File -Encoding utf8 "$O\check.txt"
"done $O"
