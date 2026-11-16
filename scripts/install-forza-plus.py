#!/usr/bin/env python3
import argparse
import hashlib
import os
import shutil
import sys
import uuid
import zipfile
from pathlib import Path


def safe_path(root: Path, relative: str) -> Path:
    # Check illegal characters / directory traversal
    if any(p in ("", ".", "..") for p in relative.replace("\\", "/").split("/")):
        raise ValueError(f"Unsafe archive path: {relative}")
    resolved_root = root.resolve()
    target = (resolved_root / relative).resolve()
    try:
        target.relative_to(resolved_root)
    except ValueError:
        raise ValueError(f"Path escapes destination: {relative}")
    # Check for symlinks along the path
    probe = target
    while probe != resolved_root and probe != probe.parent:
        if probe.is_symlink():
            raise ValueError(f"Linked destination: {probe}")
        probe = probe.parent
    return target


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest().lower()


def main():
    parser = argparse.ArgumentParser(description="Install Project Forza Plus 4")
    parser.add_argument("-BaseZip", "--base-zip", required=True, dest="base_zip")
    parser.add_argument("-UpdateZip", "--update-zip", default="", dest="update_zip")
    parser.add_argument("-GameDir", "--game-dir", required=True, dest="game_dir")
    parser.add_argument("-UserDir", "--user-dir", required=True, dest="user_dir")
    parser.add_argument(
        "-Mode",
        "--mode",
        default="Normal",
        choices=["Normal", "Hard", "Sandbox", "Vanilla"],
        dest="mode",
    )
    args, _ = parser.parse_known_args()

    game_dir = Path(args.game_dir).resolve()
    user_dir = Path(args.user_dir).resolve()
    base_zip_path = Path(args.base_zip).resolve()
    update_zip_path = Path(args.update_zip).resolve() if args.update_zip else None
    mode = args.mode

    if not (game_dir / "default.xex").exists():
        sys.exit("Install Disc 1 first.")

    target = game_dir / ".fm4-plus"
    content_target = user_dir / ".fm4-plus"
    preserved = (content_target / ".fm4-plus-preserved").exists() and not (
        content_target / ".fm4-plus-ready"
    ).exists()

    if target.exists() or (content_target.exists() and not preserved):
        sys.exit(
            "Forza Plus destination already exists. Select the existing installation, or uninstall it before retrying."
        )

    stage_id = ".pfp-" + uuid.uuid4().hex[:8]
    stage_target = game_dir / stage_id
    stage_content_target = user_dir / stage_id

    try:
        base_zip = zipfile.ZipFile(base_zip_path, "r")
    except Exception as e:
        sys.exit(f"Cannot open base zip: {e}")

    update_zip = None
    if update_zip_path and update_zip_path.exists():
        try:
            update_zip = zipfile.ZipFile(update_zip_path, "r")
        except Exception as e:
            sys.exit(f"Cannot open update zip: {e}")

    try:
        prefix = "Project Forza Plus 4/"
        # Check required files in base zip
        names = base_zip.namelist()
        if (
            prefix + "Main Game Changes/Media/db/gamedb.slt" not in names
            or prefix + "Main Game Changes/default.xex" not in names
        ):
            sys.exit("Select the full Project Forza Plus 4 ZIP, not the update.")

        plan = {}  # key -> dict(entry, root, relative, kind)
        skipped = set()

        def add_entry(zip_info, kind, relative, root_dir):
            if kind == "content":
                parts = relative.split("/")
                if len(parts) > 3:
                    pkg = parts[3]
                    header = (
                        user_dir
                        / "0000000000000000/4D530910/Headers/00000002"
                        / f"{pkg}.header"
                    )
                    if not header.exists():
                        skipped.add(pkg)
                        return
            safe_path(root_dir, relative)
            plan[f"{kind}/{relative}"] = {
                "info": zip_info,
                "root": root_dir,
                "relative": relative,
                "kind": kind,
                "zip": zip_obj,
            }

        # Process base zip
        zip_obj = base_zip
        for info in base_zip.infolist():
            if info.is_dir():
                continue
            name = info.filename
            media_prefix = prefix + "Main Game Changes/Media/"
            if name.startswith(media_prefix):
                rel = name[len(media_prefix) :]
                if not rel.startswith("RenderScenarios/"):
                    add_entry(info, "game", f"Media/{rel}", stage_target)

            dlc_prefix = prefix + "Disc 2 and DLCs/00000002/"
            if name.startswith(dlc_prefix):
                rel = name[len(dlc_prefix) :]
                add_entry(
                    info,
                    "content",
                    f"0000000000000000/4D530910/00000002/{rel}",
                    stage_content_target,
                )

        # Career mode DB
        mode_db_name = f"{prefix}Game Mode DBs/{mode} Mode/gamedb.slt"
        if mode_db_name not in names:
            mode_db_name = (
                f"{prefix}Game Mode DBs/{mode} Mode/Main Game DB/gamedb.slt"
            )
        if mode_db_name not in names:
            sys.exit(f"Missing career mode: {mode}")
        add_entry(
            base_zip.getinfo(mode_db_name),
            "game",
            "Media/db/gamedb.slt",
            stage_target,
        )

        mode_dlc_prefix = f"{prefix}Game Mode DBs/{mode} Mode/DLC DBs/"
        for info in base_zip.infolist():
            if not info.is_dir() and info.filename.startswith(mode_dlc_prefix):
                rel = info.filename[len(mode_dlc_prefix) :]
                add_entry(
                    info,
                    "content",
                    f"0000000000000000/4D530910/00000002/{rel}",
                    stage_content_target,
                )

        # Process update zip
        if update_zip:
            zip_obj = update_zip
            update_names = update_zip.namelist()
            up_prefix = "Project Forza Plus 4 Update/Update Files/"
            if (
                up_prefix + "Game Mode DBs/Normal Mode/gamedb.slt"
                not in update_names
            ):
                sys.exit("Unrecognized Project Forza Plus 4 update ZIP.")
            for info in update_zip.infolist():
                if info.is_dir():
                    continue
                name = info.filename
                if name.startswith(up_prefix + "audio/") or name.startswith(
                    up_prefix + "physics/"
                ):
                    rel = name[len(up_prefix) :]
                    add_entry(info, "game", f"Media/{rel}", stage_target)

            up_mode_db = f"{up_prefix}Game Mode DBs/{mode} Mode/gamedb.slt"
            if up_mode_db in update_names:
                add_entry(
                    update_zip.getinfo(up_mode_db),
                    "game",
                    "Media/db/gamedb.slt",
                    stage_target,
                )

            up_dlc_prefix = f"{up_prefix}Game Mode DBs/{mode} Mode/DLC DBs/"
            for info in update_zip.infolist():
                if not info.is_dir() and info.filename.startswith(
                    up_dlc_prefix
                ):
                    rel = info.filename[len(up_dlc_prefix) :]
                    add_entry(
                        info,
                        "content",
                        f"0000000000000000/4D530910/00000002/{rel}",
                        stage_content_target,
                    )

        print("Copying Disc 1 to a separate Forza Plus installation...")
        stage_target.mkdir(parents=True, exist_ok=True)
        stage_content_target.mkdir(parents=True, exist_ok=True)

        # Copy original Disc 1 files
        for root, dirs, files in os.walk(game_dir):
            rel_dir = os.path.relpath(root, game_dir)
            if rel_dir.startswith(".fm4-plus") or rel_dir.startswith(".pfp-"):
                continue
            for file in files:
                if file.startswith(".fm4-plus") or file == ".fm4-verified":
                    continue
                src_file = Path(root) / file
                rel_file = os.path.relpath(src_file, game_dir).replace("\\", "/")
                dst_file = safe_path(stage_target, rel_file)
                dst_file.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src_file, dst_file)

        # Copy existing user content packages
        title_content = user_dir / "0000000000000000/4D530910"
        for sub in ("00000002", "Headers/00000002"):
            src_sub = title_content / sub
            if src_sub.exists():
                for root, _, files in os.walk(src_sub):
                    for file in files:
                        src_file = Path(root) / file
                        rel_file = os.path.relpath(src_file, user_dir).replace(
                            "\\", "/"
                        )
                        dst_file = safe_path(stage_content_target, rel_file)
                        dst_file.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(src_file, dst_file)

        # Extract mod files over staging
        manifest = []
        content_manifest = []
        count = 0
        total = len(plan)
        for item in plan.values():
            dest = safe_path(item["root"], item["relative"])
            dest.parent.mkdir(parents=True, exist_ok=True)
            with item["zip"].open(item["info"]) as src, open(dest, "wb") as dst:
                shutil.copyfileobj(src, dst)
            h = file_sha256(dest)
            entry_line = f"{h} {item['info'].file_size} {item['relative']}"
            if item["kind"] == "game":
                manifest.append(entry_line)
            else:
                content_manifest.append(entry_line)
            count += 1
            if count % 40 == 0 or count == total:
                print(f"Forza Plus: {count} / {total}")

        with open(stage_target / ".fm4-plus.sha256", "w") as f:
            f.write("\n".join(manifest) + "\n")
        with open(stage_content_target / ".fm4-plus.sha256", "w") as f:
            f.write("\n".join(content_manifest) + "\n")

        with open(stage_content_target / ".fm4-plus-ready", "w") as f:
            f.write("1\n")
        with open(stage_target / ".fm4-plus-ready", "w") as f:
            f.write(f"{mode}; update={bool(update_zip)}\n")

        if preserved:
            shared = content_target / "0000000000000000"
            shared.mkdir(parents=True, exist_ok=True)
            staged_title = stage_content_target / "0000000000000000/4D530910"
            if staged_title.exists():
                dest_title = shared / "4D530910"
                if dest_title.exists():
                    shutil.rmtree(dest_title)
                shutil.copytree(staged_title, dest_title)
            shutil.copy2(
                stage_content_target / ".fm4-plus.sha256", content_target
            )
            shutil.copy2(stage_content_target / ".fm4-plus-ready", content_target)
            if (content_target / ".fm4-plus-preserved").exists():
                (content_target / ".fm4-plus-preserved").unlink()
            shutil.rmtree(stage_content_target)
        else:
            stage_content_target.rename(content_target)

        stage_target.rename(target)
        print(
            f"Forza Plus installed ({mode}). Original files and saves preserved. {len(skipped)} DLC packages omitted because they are not installed with headers."
        )

    except Exception as e:
        print(f"Forza Plus: {e}")
        # Clean up staging folders on error
        if stage_target.exists():
            shutil.rmtree(stage_target, ignore_errors=True)
        if stage_content_target.exists():
            shutil.rmtree(stage_content_target, ignore_errors=True)
        sys.exit(1)
    finally:
        base_zip.close()
        if update_zip:
            update_zip.close()


if __name__ == "__main__":
    main()
