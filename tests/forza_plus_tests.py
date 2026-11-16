#!/usr/bin/env python3
import os
import shutil
import subprocess
import sys
import tempfile
import uuid
import zipfile
from pathlib import Path


def write_file(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        f.write(content)


def read_file(path: Path) -> str:
    with open(path, "r") as f:
        return f.read()


def make_zip(path: Path, files: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w") as z:
        for name, data in files.items():
            z.writestr(name, data)


def assert_true(cond, msg):
    if not cond:
        raise AssertionError(msg)


def main():
    repo_root = Path(__file__).resolve().parent.parent
    installer = repo_root / "scripts/install-forza-plus.py"
    uninstaller = repo_root / "scripts/uninstall-forza-plus.py"

    temp_dir = Path(tempfile.mkdtemp(prefix="pfp_test_"))
    try:
        root = temp_dir / uuid.uuid4().hex
        root.mkdir(parents=True, exist_ok=True)

        game = root / "game"
        user = root / "user"

        write_file(game / "default.xex", "original executable")
        write_file(game / "Media/db/gamedb.slt", "original database")
        write_file(game / "Media/RenderScenarios/1-Car_Race.xml", "port shadows")
        write_file(user / "PROFILE/4D530910/00000001/ForzaProfile", "original save")

        title = "0000000000000000/4D530910"
        pkg = "4d53091000000001"
        long_pkg = "062414787A814070FA177E1C472BA36D3884B1134D"

        write_file(user / f"{title}/Headers/00000002/{long_pkg}.header", "existing DLC header")
        write_file(user / f"{title}/Headers/00000002/{pkg}.header", "original license")
        write_file(user / f"{title}/00000002/{pkg}/Media/old.bin", "original content")

        p = "Project Forza Plus 4/"
        base_files = {
            f"{p}Main Game Changes/default.xex": "incompatible executable",
            f"{p}Main Game Changes/Media/db/gamedb.slt": "base normal",
            f"{p}Main Game Changes/Media/RenderScenarios/1-Car_Race.xml": "xenia shadows",
            f"{p}Disc 2 and DLCs/00000002/{pkg}/Media/data.bin": "mod content",
            f"{p}Disc 2 and DLCs/00000002/{long_pkg}/Media/27.puboffer": "42-character package",
            f"{p}Disc 2 and DLCs/00000002/319143B00C605B32FE7622B5C0089E17296AA0E44D/Media/37.puboffer": "uninstalled DLC",
            f"{p}Disc 2 and DLCs/00000002/4d53091000000002/Media/data.bin": "missing license",
        }
        for mode in ("Normal", "Hard", "Sandbox", "Vanilla"):
            base_files[f"{p}Game Mode DBs/{mode} Mode/gamedb.slt"] = f"base {mode}"

        base_zip = root / "base.zip"
        make_zip(base_zip, base_files)

        update_zip = root / "update.zip"
        u = "Project Forza Plus 4 Update/Update Files/"
        update_files = {}
        for mode in ("Normal", "Hard", "Sandbox", "Vanilla"):
            update_files[f"{u}Game Mode DBs/{mode} Mode/gamedb.slt"] = f"update {mode}"
        update_files[f"{u}physics/PhysicsSettings.ini"] = "updated physics"
        update_files[f"{u}audio/AudioEngineConfig.xml"] = "updated audio"
        make_zip(update_zip, update_files)

        # 1. Install Hard mode with update
        cmd = [sys.executable, str(installer), "--base-zip", str(base_zip),
               "--update-zip", str(update_zip), "--game-dir", str(game),
               "--user-dir", str(user), "--mode", "Hard"]
        res = subprocess.run(cmd, capture_output=True, text=True)
        assert_true(res.returncode == 0, f"Installation failed: {res.stderr or res.stdout}")

        assert_true(read_file(game / ".fm4-plus/Media/db/gamedb.slt") == "update Hard", "Hard update failed")
        assert_true(read_file(game / ".fm4-plus/Media/audio/AudioEngineConfig.xml") == "updated audio", "Audio update failed")
        assert_true(read_file(game / ".fm4-plus/Media/physics/PhysicsSettings.ini") == "updated physics", "Physics update failed")
        assert_true(read_file(game / ".fm4-plus/default.xex") == "original executable", "Original executable replaced")
        assert_true(read_file(game / ".fm4-plus/Media/RenderScenarios/1-Car_Race.xml") == "port shadows", "Shadow fix overwritten")
        assert_true(read_file(game / "Media/db/gamedb.slt") == "original database", "Original game modified")
        assert_true(not (user / ".fm4-plus/PROFILE").exists(), "Save copied into mod")
        assert_true(not (user / f".fm4-plus/{title}/00000002/4d53091000000002").exists(), "Unlicensed package copied")
        assert_true(read_file(user / f".fm4-plus/{title}/Headers/00000002/{pkg}.header") == "original license", "Header corrupted")
        assert_true(read_file(user / f".fm4-plus/{title}/00000002/{long_pkg}/Media/27.puboffer") == "42-character package", "Long package corrupted")
        assert_true((game / ".fm4-plus/.fm4-plus-ready").exists(), "Marker missing")
        assert_true((user / ".fm4-plus/.fm4-plus.sha256").exists(), "Manifest missing")

        # 2. Existing install cannot be overwritten without uninstall
        res = subprocess.run([sys.executable, str(installer), "--base-zip", str(base_zip),
                              "--game-dir", str(game), "--user-dir", str(user)],
                             capture_output=True, text=True)
        assert_true(res.returncode != 0, "Existing installation was overwritten")

        # 3. Test other modes
        for mode in ("Normal", "Sandbox", "Vanilla"):
            g = root / mode
            u_mode = root / f"{mode}User"
            write_file(g / "default.xex", "original executable")
            res = subprocess.run([sys.executable, str(installer), "--base-zip", str(base_zip),
                                  "--game-dir", str(g), "--user-dir", str(u_mode), "--mode", mode],
                                 capture_output=True, text=True)
            assert_true(res.returncode == 0, f"Mode {mode} failed")
            assert_true(read_file(g / ".fm4-plus/Media/db/gamedb.slt") == f"base {mode}", f"Mode {mode} db mismatch")

        # 4. Uninstall test
        write_file(user / ".fm4-plus/PROFILE/4D530910/00000001/ForzaProfile", "mod career save")
        write_file(user / ".fm4-plus/cache_partition/keep.dat", "mod cache")
        res = subprocess.run([sys.executable, str(uninstaller), "--game-dir", str(game), "--user-dir", str(user)],
                             capture_output=True, text=True)
        assert_true(res.returncode == 0, f"Uninstall failed: {res.stderr or res.stdout}")
        assert_true(not (game / ".fm4-plus").exists(), "Mod game files still exist")
        assert_true(not (user / f".fm4-plus/{title}").exists(), "Mod content still exists")
        assert_true(not (user / ".fm4-plus/.fm4-plus-ready").exists(), "Ready marker still exists")
        assert_true(read_file(user / ".fm4-plus/PROFILE/4D530910/00000001/ForzaProfile") == "mod career save", "Mod save was deleted")
        assert_true(read_file(user / "PROFILE/4D530910/00000001/ForzaProfile") == "original save", "Original save was deleted")
        assert_true(read_file(game / "default.xex") == "original executable", "Original game was deleted")

        # 5. Reinstall after uninstall with different mode
        res = subprocess.run([sys.executable, str(installer), "--base-zip", str(base_zip),
                              "--game-dir", str(game), "--user-dir", str(user), "--mode", "Sandbox"],
                             capture_output=True, text=True)
        assert_true(res.returncode == 0, f"Reinstall failed: {res.stderr or res.stdout}")
        assert_true(read_file(game / ".fm4-plus/Media/db/gamedb.slt") == "base Sandbox", "Reinstall mode mismatch")
        assert_true(read_file(user / ".fm4-plus/PROFILE/4D530910/00000001/ForzaProfile") == "mod career save", "Mod save was overwritten")
        assert_true(read_file(user / ".fm4-plus/cache_partition/keep.dat") == "mod cache", "Mod cache was overwritten")

        print("Forza Plus Python install/uninstall/reinstall: all checks PASSED.")

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    main()
