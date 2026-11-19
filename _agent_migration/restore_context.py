#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
blender-supercar Cross-Device Context & Path Restore Utility
============================================================
Supports Windows, macOS, and Linux (Python 3.8+, stdlib only).

Usage Examples:
  # 1) Inspect packaged conversations and check local Blender/ffmpeg paths:
  python _agent_migration/restore_context.py --status

  # 2) Restore all 16 Antigravity conversations, summaries, project config & 14 custom skills:
  python _agent_migration/restore_context.py --restore-antigravity

  # 3) Rewrite hardcoded project, Blender & ffmpeg paths for the new machine in 1 command:
  python _agent_migration/restore_context.py --rewrite-paths \
      --proj "E:/Projects/blender-supercar" \
      --blender "C:/Program Files/Blender Foundation/Blender 5.3/blender.exe" \
      --ffmpeg "C:/ffmpeg/bin/ffmpeg.exe"

  # 4) Do BOTH in one shot (auto-detecting --proj as the cloned repository root if omitted):
  python _agent_migration/restore_context.py --restore-antigravity --rewrite-paths \
      --blender "/Applications/Blender.app/Contents/MacOS/Blender" \
      --ffmpeg "/opt/homebrew/bin/ffmpeg"
"""

import argparse
import datetime
import json
import os
import platform
import re
import shutil
import sqlite3
import sys
from pathlib import Path

MIGRATION_DIR = Path(__file__).resolve().parent
DEFAULT_REPO_ROOT = MIGRATION_DIR.parent

CIDS = [
    "01e3331f-d103-4af9-90bc-a12f64086d33",
    "16b5f3cb-4bce-43d1-a09a-ebf98bd665b7",
    "1a8ac0b5-f848-4c0e-bc45-8abba2abb2e8",
    "46b51757-eef7-4958-943d-57de1b64a881",
    "4cc01d4d-c499-4f55-b213-878718617fe0",
    "62527b59-0213-41b2-b3ab-ff115c915c3b",
    "6e1acc3f-eaac-4bed-95a2-c4f90863575e",
    "71c1ec74-2a73-43c2-80c2-96dffd9739a3",
    "7ac4a8d6-66bf-47ac-b14f-dc6a6fd3deb0",
    "80a8f1d5-652e-4a53-9931-da555b39f579",
    "8717e77d-a125-4b01-893b-0669d971d4d8",
    "a98b6c71-b658-48ee-9b28-e9a1c116099c",
    "b13776a0-7d9f-4f63-9e67-c8ecc5f11412",
    "d4f056b1-8bc5-4458-b96b-9d0293a59d65",
    "f5adc3c6-00d5-45e7-919a-267af295b5d1",
    "f904dce7-b62b-4bab-b561-90c92d39c8a3",
]

PIPELINE_PY_PROJ_FILES = [
    "pipeline/gen_textures.py",
    "pipeline/render_clay.py",
    "pipeline/render_v5.py",
    "pipeline/render_v6_sv.py",
    "pipeline/synth_sfx.py",
    "pipeline/synth_sfx_sv.py",
    "pipeline/v5_anim.py",
    "pipeline/v5_clay.py",
    "pipeline/v5_env.py",
    "pipeline/v5_preview.py",
    "pipeline/v5_stills.py",
    "pipeline/v6_sv_build.py",
    "pipeline/v6_sv_comp.py",
    "pipeline/v6_sv_env.py",
    "pipeline/v6_sv_stills.py",
    "pipeline/v6_sv_textures.py",
]

PIPELINE_SH_FILES = [
    "pipeline/mux_clay.sh",
    "pipeline/mux_v5.sh",
    "pipeline/mux_v6_sv.sh",
]

DOC_BLENDER_FILES = [
    "README.md",
    "docs/README_V4.md",
    "docs/README_V5.md",
    "docs/README_V6_SPIDERVERSE.md",
]


def to_bash_path(raw_path: str, for_exec: bool = False) -> str:
    """Convert a Windows or POSIX path into a Git-Bash / POSIX-friendly path."""
    p = raw_path.strip().strip('"').strip("'")
    # Already MSYS / POSIX style like /c/Users/... or /usr/bin/...
    if p.startswith("/"):
        return p
    # Windows drive letter like C:\foo\bar or D:/foo/bar
    m = re.match(r"^([A-Za-z]):[\\/](.*)$", p)
    if m:
        drive = m.group(1)
        rest = m.group(2).replace("\\", "/")
        if for_exec:
            return f"/{drive.lower()}/{rest}"
        return f"{drive.upper()}:/{rest}"
    return p.replace("\\", "/")


def to_native_path_str(raw_path: str) -> str:
    """Convert MSYS (/d/foo) or standard path string into native OS path string."""
    p = raw_path.strip().strip('"').strip("'")
    if platform.system() == "Windows":
        m = re.match(r"^/([A-Za-z])/(.*)$", p)
        if m:
            drive = m.group(1).upper()
            rest = m.group(2).replace("/", "\\")
            return f"{drive}:\\{rest}"
        return str(Path(p))
    return p


def backup_existing(target: Path, backup_root: Path, home_base: Path, dry_run: bool) -> None:
    if not target.exists():
        return
    try:
        rel = target.resolve().relative_to(home_base.resolve())
    except ValueError:
        rel = Path(target.name)
    b_dst = backup_root / rel
    if dry_run:
        print(f"  [dry-run] Would back up existing {target} -> {b_dst}")
        return
    b_dst.parent.mkdir(parents=True, exist_ok=True)
    if target.is_dir():
        if b_dst.exists():
            shutil.rmtree(b_dst)
        shutil.copytree(target, b_dst)
    else:
        shutil.copy2(target, b_dst)


def merge_summaries_db(
    subset_db: Path,
    target_db: Path,
    new_proj_uri: str,
    new_ag_dir: Path,
    backup_root: Path,
    home_base: Path,
    dry_run: bool,
) -> int:
    if not subset_db.exists():
        print(f"  WARN: {subset_db} not found; skipping summary DB merge.")
        return 0

    if dry_run:
        print(f"  [dry-run] Would merge 16 conversation summaries from {subset_db} -> {target_db}")
        return len(CIDS)

    target_db.parent.mkdir(parents=True, exist_ok=True)
    if target_db.exists():
        backup_existing(target_db, backup_root, home_base, dry_run=False)
    else:
        shutil.copy2(subset_db, target_db)

    src_conn = sqlite3.connect(f"file:{subset_db.as_posix()}?mode=ro", uri=True)
    src_conn.row_factory = sqlite3.Row
    scur = src_conn.cursor()
    sum_rows = scur.execute("SELECT * FROM conversation_summaries").fetchall()

    fts_rows = []
    has_src_fts = (
        scur.execute("SELECT count(*) FROM sqlite_master WHERE type='table' AND name='conversations_fts'").fetchone()[0]
        > 0
    )
    if has_src_fts:
        fts_rows = scur.execute("SELECT * FROM conversations_fts").fetchall()

    dst_conn = sqlite3.connect(str(target_db), timeout=30.0)
    dcur = dst_conn.cursor()

    # Ensure tables exist in target DB
    has_dst_sum = (
        dcur.execute(
            "SELECT count(*) FROM sqlite_master WHERE type='table' AND name='conversation_summaries'"
        ).fetchone()[0]
        > 0
    )
    if not has_dst_sum:
        sum_sql = scur.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='conversation_summaries'"
        ).fetchone()[0]
        dcur.execute(sum_sql)

    dst_cols = {r[1] for r in dcur.execute("PRAGMA table_info(conversation_summaries)").fetchall()}
    merged = 0
    for row in sum_rows:
        row_dict = dict(row)
        # Update workspace_uris and app_data_dir to match the new device!
        if "workspace_uris" in row_dict and row_dict["workspace_uris"]:
            try:
                uris = json.loads(row_dict["workspace_uris"])
                if isinstance(uris, list):
                    row_dict["workspace_uris"] = json.dumps(
                        [new_proj_uri if "blender-supercar" in u or "%E9%A1%B9%E7%9B%AEsession" in u else u for u in uris]
                    )
                else:
                    row_dict["workspace_uris"] = json.dumps([new_proj_uri])
            except Exception:
                row_dict["workspace_uris"] = json.dumps([new_proj_uri])
        if "app_data_dir" in row_dict:
            row_dict["app_data_dir"] = str(new_ag_dir)

        use_cols = [c for c in row_dict.keys() if c in dst_cols]
        col_sql = ",".join(f"`{c}`" for c in use_cols)
        val_sql = ",".join("?" for _ in use_cols)
        dcur.execute(
            f"INSERT OR REPLACE INTO conversation_summaries ({col_sql}) VALUES ({val_sql})",
            tuple(row_dict[c] for c in use_cols),
        )
        merged += 1

    has_dst_fts = (
        dcur.execute("SELECT count(*) FROM sqlite_master WHERE type='table' AND name='conversations_fts'").fetchone()[0]
        > 0
    )
    if has_dst_fts and fts_rows:
        ph = ",".join("?" for _ in CIDS)
        dcur.execute(f"DELETE FROM conversations_fts WHERE conversation_id IN ({ph})", CIDS)
        dst_fcols = [r[1] for r in dcur.execute("PRAGMA table_info(conversations_fts)").fetchall()]
        use_fcols = [c for c in fts_rows[0].keys() if c in dst_fcols]
        fcol_sql = ",".join(f"`{c}`" for c in use_fcols)
        fval_sql = ",".join("?" for _ in use_fcols)
        for r in fts_rows:
            rd = dict(r)
            if "workspace" in rd and rd["workspace"]:
                rd["workspace"] = str(Path(new_proj_uri.replace("file:///", "")) if new_proj_uri.startswith("file:") else new_proj_uri)
            dcur.execute(
                f"INSERT INTO conversations_fts ({fcol_sql}) VALUES ({fval_sql})",
                tuple(rd[c] for c in use_fcols),
            )

    dst_conn.commit()
    dst_conn.close()
    src_conn.close()
    return merged


def do_restore_antigravity(proj_root: Path, gemini_dir: Path, claude_dir: Path, dry_run: bool) -> None:
    print("=== [Restore Antigravity Context, Conversations & Custom Skills] ===")
    print("NOTE: Close Antigravity IDE before running --restore-antigravity so SQLite DBs are unlocked.")
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_root = gemini_dir / f"_backup_before_blender_supercar_{ts}"
    ag_dst = gemini_dir / "antigravity"
    proj_uri = proj_root.resolve().as_uri()

    # 1. Restore 16 brain/<cid> directories
    src_brain = MIGRATION_DIR / "antigravity" / "brain"
    dst_brain = ag_dst / "brain"
    brain_restored = 0
    if src_brain.is_dir():
        for cid in CIDS:
            s = src_brain / cid
            d = dst_brain / cid
            if not s.is_dir():
                continue
            backup_existing(d, backup_root, Path.home(), dry_run)
            if dry_run:
                print(f"  [dry-run] Would copy brain/{cid} -> {d}")
            else:
                if d.exists():
                    shutil.rmtree(d)
                shutil.copytree(s, d)
            brain_restored += 1
    print(f"  -> Restored {brain_restored}/16 brain/<cid>/ directories into {dst_brain}")

    # 2. Restore 16 conversations/<cid>.db files
    src_conv = MIGRATION_DIR / "antigravity" / "conversations"
    dst_conv = ag_dst / "conversations"
    conv_restored = 0
    if src_conv.is_dir():
        if not dry_run:
            dst_conv.mkdir(parents=True, exist_ok=True)
        for cid in CIDS:
            s = src_conv / f"{cid}.db"
            d = dst_conv / f"{cid}.db"
            if not s.is_file():
                continue
            backup_existing(d, backup_root, Path.home(), dry_run)
            if dry_run:
                print(f"  [dry-run] Would copy conversations/{cid}.db -> {d}")
            else:
                for suf in ("-wal", "-shm"):
                    wal_f = Path(str(d) + suf)
                    if wal_f.exists():
                        wal_f.unlink()
                shutil.copy2(s, d)
            conv_restored += 1
    print(f"  -> Restored {conv_restored}/16 conversations/<cid>.db files into {dst_conv}")

    # 3. Merge conversation_summaries_subset.db
    subset_db = MIGRATION_DIR / "antigravity" / "conversation_summaries_subset.db"
    target_sum_db = ag_dst / "conversation_summaries.db"
    merged_rows = merge_summaries_db(
        subset_db=subset_db,
        target_db=target_sum_db,
        new_proj_uri=proj_uri,
        new_ag_dir=ag_dst,
        backup_root=backup_root,
        home_base=Path.home(),
        dry_run=dry_run,
    )
    print(f"  -> Merged {merged_rows} summary rows into {target_sum_db} (workspace URI -> {proj_uri})")

    # 4. Restore project config JSON with updated folderUri
    src_proj_json = MIGRATION_DIR / "memory_and_skills" / "projects" / "b8f1cf42-d4c5-4e16-b789-f04062d11bb5.json"
    dst_proj_json = gemini_dir / "config" / "projects" / "b8f1cf42-d4c5-4e16-b789-f04062d11bb5.json"
    if src_proj_json.is_file():
        backup_existing(dst_proj_json, backup_root, Path.home(), dry_run)
        pdata = json.loads(src_proj_json.read_text(encoding="utf-8"))
        pdata["projectResources"] = {"resources": [{"folderUri": proj_uri}]}
        if dry_run:
            print(f"  [dry-run] Would write project config {dst_proj_json} with folderUri={proj_uri}")
        else:
            dst_proj_json.parent.mkdir(parents=True, exist_ok=True)
            dst_proj_json.write_text(json.dumps(pdata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"  -> Installed project config {dst_proj_json}")

    # 5. Restore 14 custom skills
    src_skills = MIGRATION_DIR / "memory_and_skills" / "skills"
    dst_skills = gemini_dir / "skills"
    skill_count = 0
    if src_skills.is_dir():
        for sk_dir in sorted(src_skills.iterdir()):
            if not sk_dir.is_dir():
                continue
            target_sk = dst_skills / sk_dir.name
            backup_existing(target_sk, backup_root, Path.home(), dry_run)
            if dry_run:
                print(f"  [dry-run] Would install skill {sk_dir.name} -> {target_sk}")
            else:
                if target_sk.exists():
                    shutil.rmtree(target_sk)
                shutil.copytree(sk_dir, target_sk)
            skill_count += 1
    print(f"  -> Installed {skill_count} custom skills into {dst_skills}")

    # 6. Restore GEMINI.md & CLAUDE.md (with automatic backup of any existing file)
    src_gemini_md = MIGRATION_DIR / "memory_and_skills" / "GEMINI.md"
    dst_gemini_md = gemini_dir / "GEMINI.md"
    if src_gemini_md.is_file():
        backup_existing(dst_gemini_md, backup_root, Path.home(), dry_run)
        if dry_run:
            print(f"  [dry-run] Would install {dst_gemini_md}")
        else:
            dst_gemini_md.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src_gemini_md, dst_gemini_md)
        print(f"  -> Installed {dst_gemini_md}")

    src_claude_md = MIGRATION_DIR / "memory_and_skills" / "CLAUDE.md"
    dst_claude_md = claude_dir / "CLAUDE.md"
    if src_claude_md.is_file():
        backup_existing(dst_claude_md, backup_root, Path.home(), dry_run)
        if dry_run:
            print(f"  [dry-run] Would install {dst_claude_md}")
        else:
            dst_claude_md.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src_claude_md, dst_claude_md)
        print(f"  -> Installed {dst_claude_md}")

    if backup_root.exists():
        print(f"  -> Pre-existing files safely backed up at: {backup_root}")


def do_rewrite_paths(
    repo_root: Path,
    new_proj: str,
    new_blender: str,
    new_ffmpeg: str,
    dry_run: bool,
) -> None:
    print("=== [Rewrite Hardcoded Project / Blender / FFmpeg Paths] ===")
    proj_native = to_native_path_str(new_proj) if new_proj else str(repo_root.resolve())
    proj_bash = to_bash_path(proj_native, for_exec=False)

    updated_files = 0

    # 1. Update PROJ = r"..." in pipeline/*.py
    proj_py_re = re.compile(r'^PROJ\s*=\s*r?["\'][^"\']+["\']', re.MULTILINE)
    for rel in PIPELINE_PY_PROJ_FILES:
        fp = repo_root / rel
        if not fp.is_file():
            continue
        orig = fp.read_text(encoding="utf-8")
        repl_line = f'PROJ = r"{proj_native}"'
        updated = proj_py_re.sub(lambda _: repl_line, orig, count=1)

        # Also update FFMPEG = r"..." in pipeline/synth_sfx_sv.py if --ffmpeg is given
        if rel == "pipeline/synth_sfx_sv.py" and new_ffmpeg:
            ff_native = to_native_path_str(new_ffmpeg)
            ff_py_re = re.compile(r'^FFMPEG\s*=\s*r?["\'][^"\']+["\']', re.MULTILINE)
            updated = ff_py_re.sub(lambda _: f'FFMPEG = r"{ff_native}"', updated, count=1)

        if updated != orig:
            if dry_run:
                print(f"  [dry-run] Would update {rel}")
            else:
                fp.write_text(updated, encoding="utf-8", newline="\n")
                print(f"  Updated {rel}")
            updated_files += 1

    # 2. Update PROJ="..." and FF=... in pipeline/mux_*.sh
    proj_sh_re = re.compile(r'^PROJ=["\']?[^"\'\r\n]+["\']?', re.MULTILINE)
    ff_sh_re = re.compile(r'^FF=[^\r\n]+', re.MULTILINE)
    for rel in PIPELINE_SH_FILES:
        fp = repo_root / rel
        if not fp.is_file():
            continue
        orig = fp.read_text(encoding="utf-8")
        updated = proj_sh_re.sub(lambda _: f'PROJ="{proj_bash}"', orig, count=1)
        if new_ffmpeg:
            ff_bash = to_bash_path(new_ffmpeg, for_exec=True)
            quote_ff = f'"{ff_bash}"' if " " in ff_bash else ff_bash
            updated = ff_sh_re.sub(lambda _: f"FF={quote_ff}", updated, count=1)
        if updated != orig:
            if dry_run:
                print(f"  [dry-run] Would update {rel}")
            else:
                fp.write_text(updated, encoding="utf-8", newline="\n")
                print(f"  Updated {rel}")
            updated_files += 1

    # 3. Update B="..." Blender CLI snippets in README.md and docs/*.md if --blender is given
    if new_blender:
        bl_bash = to_bash_path(new_blender, for_exec=True)
        bl_doc_re = re.compile(r'^B=["\'][^"\']+["\']', re.MULTILINE)
        for rel in DOC_BLENDER_FILES:
            fp = repo_root / rel
            if not fp.is_file():
                continue
            orig = fp.read_text(encoding="utf-8")
            updated = bl_doc_re.sub(lambda _: f'B="{bl_bash}"', orig)
            if updated != orig:
                if dry_run:
                    print(f"  [dry-run] Would update Blender path in {rel}")
                else:
                    fp.write_text(updated, encoding="utf-8", newline="\n")
                    print(f"  Updated Blender path in {rel} -> B=\"{bl_bash}\"")
                updated_files += 1

    print(f"  -> Path rewrite complete ({updated_files} file(s) modified).")


def do_status(repo_root: Path, gemini_dir: Path) -> None:
    print("=== [blender-supercar Migration Package Status] ===")
    print(f"  Repo root       : {repo_root}")
    print(f"  Migration dir   : {MIGRATION_DIR}")
    print(f"  Target ~/.gemini: {gemini_dir}")

    brain_dirs = [c for c in CIDS if (MIGRATION_DIR / "antigravity" / "brain" / c).is_dir()]
    conv_dbs = [c for c in CIDS if (MIGRATION_DIR / "antigravity" / "conversations" / f"{c}.db").is_file()]
    skills_dir = MIGRATION_DIR / "memory_and_skills" / "skills"
    skills = sorted(p.name for p in skills_dir.iterdir() if p.is_dir()) if skills_dir.is_dir() else []

    print(f"  Packaged brains : {len(brain_dirs)}/16")
    print(f"  Packaged convDBs: {len(conv_dbs)}/16")
    print(f"  Packaged skills : {len(skills)} ({', '.join(skills)})")

    print("\n=== [Local Tool Discovery on This Machine] ===")
    for tool in ("python", "blender", "ffmpeg", "ffprobe", "bash", "gh"):
        found = shutil.which(tool)
        print(f"  {tool:10s}: {found or '(not on PATH — pass explicit path to --rewrite-paths if needed)'}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Restore Antigravity 16-agent swarm conversations/skills and rewrite hardcoded paths on a new device."
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Inspect packaged migration artifacts and check local tool availability.",
    )
    parser.add_argument(
        "--restore-antigravity",
        action="store_true",
        help="Restore 16 brain/<cid> dirs, conversations/<cid>.db, summaries, project config & 14 skills into ~/.gemini.",
    )
    parser.add_argument(
        "--rewrite-paths",
        action="store_true",
        help="Rewrite hardcoded PROJ, Blender, and FFmpeg paths across pipeline/*.py, pipeline/mux_*.sh, and docs.",
    )
    parser.add_argument(
        "--proj",
        type=str,
        default="",
        help="New project root path (defaults to the cloned repository root directory).",
    )
    parser.add_argument(
        "--blender",
        type=str,
        default="",
        help="Path to Blender 5.x executable on the new device.",
    )
    parser.add_argument(
        "--ffmpeg",
        type=str,
        default="",
        help="Path to ffmpeg executable on the new device.",
    )
    parser.add_argument(
        "--gemini-dir",
        type=str,
        default=str(Path.home() / ".gemini"),
        help="Override target ~/.gemini directory (default: ~/.gemini).",
    )
    parser.add_argument(
        "--claude-dir",
        type=str,
        default=str(Path.home() / ".claude"),
        help="Override target ~/.claude directory (default: ~/.claude).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview all changes without modifying any files.",
    )

    args = parser.parse_args()
    candidate_proj = Path(to_native_path_str(args.proj)) if args.proj else DEFAULT_REPO_ROOT
    repo_root = candidate_proj.resolve() if (args.proj and (candidate_proj / "pipeline").is_dir()) else DEFAULT_REPO_ROOT
    target_proj_str = to_native_path_str(args.proj) if args.proj else str(repo_root)
    gemini_dir = Path(args.gemini_dir).expanduser()
    claude_dir = Path(args.claude_dir).expanduser()

    if not (args.status or args.restore_antigravity or args.rewrite_paths):
        parser.print_help()
        print("\nRunning --status by default:\n")
        do_status(repo_root, gemini_dir)
        return

    if args.status:
        do_status(repo_root, gemini_dir)

    if args.rewrite_paths:
        do_rewrite_paths(
            repo_root=repo_root,
            new_proj=target_proj_str,
            new_blender=args.blender,
            new_ffmpeg=args.ffmpeg,
            dry_run=args.dry_run,
        )

    if args.restore_antigravity:
        do_restore_antigravity(
            proj_root=Path(target_proj_str),
            gemini_dir=gemini_dir,
            claude_dir=claude_dir,
            dry_run=args.dry_run,
        )


if __name__ == "__main__":
    main()
