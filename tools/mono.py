"""Find Mono + Mono.Cecil and compile the small C# helpers into workspace/bin/."""
import glob
import os
import shutil
import subprocess
from pathlib import Path

import common


def tool(name):
    p = shutil.which(name)
    if not p:
        raise SystemExit(f"'{name}' not found. Install Mono (https://www.mono-project.com/download/ or `brew install mono`).")
    return p


def cecil():
    """Mono.Cecil.dll: workspace/bin (user-supplied), else Mono's GAC."""
    local = common.bin_dir() / "Mono.Cecil.dll"
    if local.exists():
        return local
    prefix = Path(tool("mono")).resolve().parents[1]
    hits = sorted(glob.glob(str(prefix / "lib/mono/gac/Mono.Cecil/0.11*/Mono.Cecil.dll")))
    if not hits:
        raise SystemExit("Mono.Cecil.dll (0.11.x) not found in Mono's GAC. Download it from NuGet "
                         "(package Mono.Cecil) and put Mono.Cecil.dll into workspace/bin/.")
    return Path(hits[-1])


def compile_cs(src, name):
    """Compile src (.cs) to workspace/bin/<name>.exe against Mono.Cecil; returns the exe path."""
    out = common.bin_dir()
    out.mkdir(parents=True, exist_ok=True)
    dll = cecil()
    if dll.parent != out:
        shutil.copy(dll, out / "Mono.Cecil.dll")
    exe = out / f"{name}.exe"
    if not exe.exists() or exe.stat().st_mtime < Path(src).stat().st_mtime:
        subprocess.run([tool("mcs"), "-langversion:7", f"-out:{exe}", f"-r:{out / 'Mono.Cecil.dll'}", str(src)], check=True)
    return exe


def check():
    """Fail early (before anything is modified) if Mono, mcs or Mono.Cecil are missing."""
    tool("mono")
    tool("mcs")
    cecil()


def run(exe, *args, cwd=None):
    """Run a helper under Mono. Home/app-data variables point into a sandbox inside the run
    directory, so any game code the helper touches can't write to real saves or config.cfg."""
    env = dict(os.environ)
    sandbox = Path(cwd or common.WS / "run") / "sandbox-home"
    sandbox.mkdir(parents=True, exist_ok=True)
    for var in ("HOME", "XDG_DATA_HOME", "XDG_CONFIG_HOME", "USERPROFILE", "APPDATA", "LOCALAPPDATA"):
        env[var] = str(sandbox)
    r = subprocess.run([tool("mono"), str(exe), *map(str, args)], cwd=cwd, capture_output=True,
                       text=True, encoding="utf-8", errors="replace", env=env)
    if r.returncode:
        raise SystemExit(f"{Path(exe).name} failed:\n{r.stdout}{r.stderr}")
    return r.stdout + r.stderr
