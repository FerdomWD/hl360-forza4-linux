#!/usr/bin/env python3
import argparse
import os
import shutil
import sys
from pathlib import Path


def assert_no_links(path: Path):
    probe = path.resolve()
    while probe != probe.parent:
        if probe.is_symlink():
            raise ValueError(f"Linked path: {probe}")
        probe = probe.parent


def assert_tree(path: Path):
    assert_no_links(path)
    if not path.exists():
        return
    for root, dirs, files in os.walk(path):
        for name in dirs + files:
            p = Path(root) / name
            if p.is_symlink():
                raise ValueError(f"Linked mod entry: {p}")


def main():
    parser = argparse.ArgumentParser(description="Uninstall Project Forza Plus 4")
    parser.add_argument("-GameDir", "--game-dir", required=True, dest="game_dir")
    parser.add_argument("-UserDir", "--user-dir", required=True, dest="user_dir")
    args, _ = parser.parse_known_args()

    game_dir = Path(args.game_dir).resolve()
    user_dir = Path(args.user_dir).resolve()

    if game_dir == user_dir:
        sys.exit("Game and user roots must be separate")

    mod_game = (game_dir / ".fm4-plus").resolve()
    mod_user = (user_dir / ".fm4-plus").resolve()

    if mod_game.parent != game_dir or mod_user.parent != user_dir:
        sys.exit("Invalid mod roots")

    if not (game_dir / "default.xex").exists() or \
       not (mod_game / ".fm4-plus-ready").exists() or \
       not (mod_user / ".fm4-plus-ready").exists():
        sys.exit("A complete separate Forza Plus installation is required")

    assert_tree(mod_game)
    assert_tree(mod_user)

    content = (mod_user / "0000000000000000/4D530910").resolve()
    try:
        content.relative_to(mod_user)
    except ValueError:
        sys.exit("Content escaped mod user root")

    try:
        # Preserve profile folders, settings and caches in-place
        with open(mod_user / ".fm4-plus-preserved", "w") as f:
            f.write("1\n")

        if content.exists():
            shutil.rmtree(content)

        shutil.rmtree(mod_game)

        for name in (".fm4-plus-ready", ".fm4-plus.sha256"):
            file_path = mod_user / name
            if file_path.exists():
                file_path.unlink()

        print("Forza Plus uninstalled. Original game, mod saves and settings preserved. Install again to select another career mode.")
    except Exception as e:
        print(f"Forza Plus uninstall: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
