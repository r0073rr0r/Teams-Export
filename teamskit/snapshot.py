"""Copy the live Teams IndexedDB (LevelDB) to export/_snapshot so it can be read safely.

Teams keeps the .log file open while running; Python's open() on Windows shares read/write,
so a plain copy works. The LOCK file is skipped on purpose - the copy must not look locked.
"""
import os
import shutil

from . import config


def run(profile):
    src = config.leveldb_dir(profile)
    if not os.path.isdir(src):
        print(f"  [{profile}] cache not found: {src}")
        return None
    dst = config.snapshot_dir(profile)
    if os.path.isdir(dst):
        shutil.rmtree(dst)
    os.makedirs(dst)
    copied = failed = 0
    for name in os.listdir(src):
        if name == "LOCK":
            continue
        try:
            shutil.copy2(os.path.join(src, name), dst)
            copied += 1
        except OSError as e:
            failed += 1
            print(f"  [{profile}] could not copy {name}: {e}")
    print(f"  [{profile}] snapshot: {copied} files copied, {failed} failed -> {dst}")
    return dst
