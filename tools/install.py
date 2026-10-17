#!/usr/bin/env python3
"""Build and install the translation into your game, or put the original back.

  python tools/install.py text      dialogue + briefings + WorkHouse textures (+ manual PDFs if
                                    built); original program, menus stay English, game language
                                    unchanged
  python tools/install.py full      text + patched exe + translated strings.csv (menus/UI),
                                    game language set to your language
  python tools/install.py restore   original game files and language setting from workspace/backup

Close the game first (it rewrites config.cfg on exit, and Windows locks the exe while it runs).
Every mode checks prerequisites before touching anything, then restores the files it manages
from the backup, so switching between modes is safe. If the game was updated since the backup
was made, the tool refuses to run: make a fresh backup (see setup.py).
"""
import hashlib
import json
import platform
import re
import shutil
import subprocess
import sys
from pathlib import Path

import common

MANAGED_DIRS = ["Content/vignettes", "Content/descriptions", "Content/manual",
                "PackedContent/textures/workhouse", "PackedContent/half/textures/workhouse"]
MANAGED_FILES = ["Content/strings.csv", "EXAPUNKS.exe"]
TOOLS = Path(__file__).resolve().parent


def say(*a):
    print(*a, flush=True)


def sha256(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def py(script, *args):
    r = subprocess.run([sys.executable, str(TOOLS / script), *args])
    if r.returncode:
        sys.exit(f"tools/{script} {' '.join(args)} failed (see above); the game now has the original "
                 "files for this part. Fix the problem and run install.py again.")


# ---------------------------------------------------------------- checks (nothing modified yet)

def game_running():
    try:
        if platform.system() == "Windows":
            out = subprocess.run(["tasklist"], capture_output=True, text=True).stdout
            return "EXAPUNKS" in out.upper()
        exe = re.escape(str(common.game() / "EXAPUNKS"))  # matches EXAPUNKS, EXAPUNKS.exe, EXAPUNKS.bin.*
        r = subprocess.run(["pgrep", "-f", exe], capture_output=True, text=True)
        return r.returncode == 0
    except FileNotFoundError:
        return False  # no process tool available; can't tell


def installed_record():
    p = common.WS / "installed.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def preflight(mode):
    g, b = common.game(), common.backup()
    if game_running():
        sys.exit("EXAPUNKS is running. Quit the game first, then run install.py again.")
    missing = [p for p in MANAGED_FILES + ["config.cfg", "SHA256"] if not (b / p).exists()]
    if missing:
        sys.exit(f"backup incomplete ({', '.join(missing)} missing in {b}); run setup.py")
    if not Path(common.config()["config_cfg"]).exists():
        sys.exit(f"{common.config()['config_cfg']} not found (start the game once, or fix workspace/config.json)")
    # Game updated or modified by someone else since the backup? Then restoring would downgrade it.
    current = sha256(g / "EXAPUNKS.exe")
    known = {(b / "SHA256").read_text().split()[0], installed_record().get("exe_sha256")}
    if current not in known:
        sys.exit("The game's EXAPUNKS.exe matches neither the backup nor what this workspace installed: "
                 "the game was changed or updated. Make a fresh backup: move workspace/backup away, "
                 "run setup.py on the (unmodified) game, then install again.")
    if mode in ("text", "full"):
        try:
            import cv2, lz4, numpy, PIL, fontTools  # noqa: F401  (WorkHouse textures)
        except ImportError as e:
            sys.exit(f"missing Python package ({e.name}): pip install -r requirements.txt")
    if mode == "full":
        import mono
        mono.check()


# ---------------------------------------------------------------- actions

def set_language(name):
    cfg = Path(common.config()["config_cfg"])
    raw = cfg.read_bytes()  # keep BOM and line endings exactly as the game wrote them
    eol = b"\r\n" if b"\r\n" in raw else b"\n"
    new, n = re.subn(rb"(?m)^Language = [^\r\n]*", b"Language = " + name.encode(), raw)
    if not n:
        new = raw.rstrip(b"\r\n") + eol + b"Language = " + name.encode() + eol
    cfg.write_bytes(new)
    say(f"{cfg}: Language = {name}")


def original_language():
    m = re.search(rb"(?m)^Language = ([^\r\n]*)", (common.backup() / "config.cfg").read_bytes())
    return m.group(1).decode("utf-8", "replace").strip() if m else "English"


def record(exe_sha):
    (common.WS / "installed.json").write_text(json.dumps({"exe_sha256": exe_sha}) + "\n", encoding="utf-8")


def restore():
    g, b = common.game(), common.backup()
    shutil.copy2(b / "EXAPUNKS.exe", g / "EXAPUNKS.exe")      # program and language first
    set_language(original_language())
    record(sha256(b / "EXAPUNKS.exe"))
    shutil.copy2(b / "Content/strings.csv", g / "Content/strings.csv")
    done = ["EXAPUNKS.exe", "Content/strings.csv"]
    for d in MANAGED_DIRS:
        if not (b / d).exists():
            if (g / d).exists():
                say(f"warning: {d} is not in the backup; left as it is")
            continue
        if (g / d).exists():
            shutil.rmtree(g / d)
        shutil.copytree(b / d, g / d)
        done.append(d)
    say("restored original files:", ", ".join(done))


def fresh(*dirs):
    """Empty build output folders so files from earlier runs are never installed."""
    for d in dirs:
        p = common.build() / d
        if p.exists():
            shutil.rmtree(p)


def copy_all(src, dst):
    files = sorted(Path(src).glob("*")) if Path(src).exists() else []
    for f in files:
        shutil.copy2(f, Path(dst) / f.name)
    return len(files)


def text():
    restore()
    g, B, tr = common.game(), common.build(), common.tr()
    fresh("vignettes", "descriptions", "descriptions-ui", "textures", "half", "workhouse-preview")
    if (tr / "vignettes").exists():
        py("vignettes.py", "build", "--partial")  # untranslated files stay English (pilot installs)
        say("dialogue files:", copy_all(B / "vignettes", g / "Content/vignettes"))
    if (tr / "descriptions").exists():
        py("descriptions.py", "build", "--partial")
        say("briefings:", copy_all(B / "descriptions", g / "Content/descriptions/en"))
    if (tr / "workhouse.json").exists():
        py("workhouse.py", "build")
        say("WorkHouse textures:", copy_all(B / "textures/workhouse", g / "PackedContent/textures/workhouse"))
        if (g / "PackedContent/half/textures/workhouse").exists():
            say("WorkHouse half-size textures:",
                copy_all(B / "half/textures/workhouse", g / "PackedContent/half/textures/workhouse"))
    pdfs = sorted((B / "manual").glob("*.pdf")) if (B / "manual").exists() else []
    for p in pdfs:
        shutil.copy2(p, g / "Content/manual" / p.name)
    say("manual PDFs:", len(pdfs), "" if pdfs else "(none built; see reference/manual.md)")


def full():
    import mono
    text()
    g, B, tr = common.game(), common.build(), common.tr()
    B.mkdir(parents=True, exist_ok=True)
    patch = mono.compile_cs(TOOLS / "patch/Patch.cs", "Patch")
    out = B / "EXAPUNKS.exe"
    if out.exists():
        out.unlink()
    say(mono.run(patch, common.backup() / "EXAPUNKS.exe", out).strip())
    shutil.copy2(out, g / "EXAPUNKS.exe")
    record(sha256(out))
    if (tr / "ui_strings.tsv").exists() and (common.source() / "ui_strings.tsv").exists():
        py("ui.py", "build")
        shutil.copy2(B / "strings.csv", g / "Content/strings.csv")
        if (tr / "descriptions").exists():
            py("ui.py", "relabel")
            copy_all(B / "descriptions-ui", g / "Content/descriptions/en")
    else:
        say("no UI string translation: menus stay English (UI strings need the optional extraction/ step)")
    set_language(common.lang_name())


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd not in ("text", "full", "restore"):
        sys.exit(__doc__)
    preflight(cmd)
    {"text": text, "full": full, "restore": restore}[cmd]()
    say("done:", cmd)
