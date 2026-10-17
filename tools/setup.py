#!/usr/bin/env python3
"""Point the toolkit at your copy of EXAPUNKS and back it up (once).

  python tools/setup.py --game <path> --lang de [--config-cfg <path>]

--game        the game folder (the one with EXAPUNKS.exe, Content/, PackedContent/) or, on macOS,
              the EXAPUNKS.app bundle
--lang        target language code: de, fr, ru, zh, ja (the languages the engine knows)
--config-cfg  the game's settings file, if it isn't found automatically (start the game once
              so it exists)

Backups go to workspace/backup/ and are never overwritten. Run this on an unmodified game: setup
refuses to back up an exe that already carries this toolkit's patch, or a config whose Language
isn't English (both signs of an earlier install). After a game update, start over with a fresh
workspace (or delete workspace/backup) so the backup matches the new version.
"""
import argparse
import hashlib
import json
import os
import platform
import re
import shutil
import sys
from pathlib import Path

import common


def find_game(p):
    p = Path(p).expanduser().resolve()
    for cand in (p, p / "Contents/MacOS"):
        if (cand / "EXAPUNKS.exe").exists() and (cand / "Content").is_dir():
            return cand
    sys.exit(f"EXAPUNKS.exe + Content/ not found in {p}")


def config_candidates():
    home = Path.home()
    roots = {
        "Darwin": [home / "Library/Application Support/EXAPUNKS"],
        "Windows": [home / "Documents/My Games/EXAPUNKS", Path(os.environ.get("USERPROFILE", home)) / "Documents/My Games/EXAPUNKS"],
        "Linux": [home / ".local/share/EXAPUNKS", Path(os.environ.get("XDG_DATA_HOME", home / ".local/share")) / "EXAPUNKS"],
    }.get(platform.system(), [])
    found = []
    for r in roots:
        found += sorted(r.glob("*/config.cfg")) + sorted(r.glob("config.cfg"))
    return list(dict.fromkeys(found))


KNOWN_BUILDS = {  # informational only
    "9e32c95075421faa26fdbeabb97e70f89f398908ee6eecfb9bf679107e43420f": "GOG macOS build (2019), the one this toolkit was developed on",
}
PATCH_MARKER = "[!!! MISSING".encode("utf-16-le")  # our patch's plain string; the original's strings are encrypted


def sha256(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def unmodified_or_exit(game, cfg):
    if PATCH_MARKER in (game / "EXAPUNKS.exe").read_bytes():
        sys.exit("This EXAPUNKS.exe is already patched by this toolkit, so it can't serve as the backup. "
                 "Restore the original first (`python tools/install.py restore` with the workspace that "
                 "installed it, or your store's verify/repair function), then run setup again.")
    lang = re.search(r"(?m)^Language = *([^\r\n]*)", cfg.read_text(encoding="utf-8-sig", errors="replace"))
    if lang and lang.group(1).strip() != "English":
        sys.exit(f"{cfg} says Language = {lang.group(1).strip()}: the game looks already modified. Restore it "
                 "first (or set Language = English if you changed it yourself), then run setup again.")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--game", required=True)
    ap.add_argument("--lang", required=True, choices=sorted(common.LANGS))
    ap.add_argument("--config-cfg")
    a = ap.parse_args()

    game = find_game(a.game)
    if a.config_cfg:
        cfg = Path(a.config_cfg).expanduser().resolve()
    else:
        c = config_candidates()
        if len(c) != 1:
            sys.exit("Could not pick the game's config.cfg automatically "
                     f"({'none found; start the game once' if not c else 'several: ' + ', '.join(map(str, c))}). "
                     "Pass --config-cfg.")
        cfg = c[0]
    if not cfg.exists():
        sys.exit(f"{cfg} does not exist")

    b = common.backup()
    if (b / "EXAPUNKS.exe").exists() and (b / "SHA256").exists():
        print(f"backup already exists in {b}, leaving it alone")
    else:
        if b.exists():
            sys.exit(f"{b} exists but is incomplete. Delete it and run setup again.")
        unmodified_or_exit(game, cfg)
        tmp = b.with_name("backup.tmp")
        if tmp.exists():
            shutil.rmtree(tmp)  # left over from an interrupted run
        print(f"backing up {game} -> {b} (Content, PackedContent, EXAPUNKS.exe, config.cfg)")
        tmp.mkdir(parents=True)
        shutil.copytree(game / "Content", tmp / "Content")
        shutil.copytree(game / "PackedContent", tmp / "PackedContent")
        shutil.copy2(game / "EXAPUNKS.exe", tmp / "EXAPUNKS.exe")
        shutil.copy2(cfg, tmp / "config.cfg")
        h = sha256(tmp / "EXAPUNKS.exe")
        (tmp / "SHA256").write_text(f"{h}  EXAPUNKS.exe\n")
        tmp.rename(b)
        print(f"EXAPUNKS.exe sha256 {h}" + (f" ({KNOWN_BUILDS[h]})" if h in KNOWN_BUILDS else " (unknown build: tools may still work, check carefully)"))

    common.WS.mkdir(parents=True, exist_ok=True)
    conf = {"game": str(game), "lang": a.lang, "config_cfg": str(cfg)}
    (common.WS / "config.json").write_text(json.dumps(conf, indent=2) + "\n", encoding="utf-8")
    common.tr().mkdir(exist_ok=True)
    print(json.dumps(conf, indent=2))
    print(f"language: {common.LANGS[a.lang][0]}; translations go to {common.tr()}")


if __name__ == "__main__":
    main()
