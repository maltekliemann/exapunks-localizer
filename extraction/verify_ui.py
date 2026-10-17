#!/usr/bin/env python3
"""End-to-end check of the UI translation: the patched exe loads workspace/build/strings.csv
through the game's own loader with your language selected, and every source string is looked
up through the game's own localization code. Reports any string that doesn't come back as your
translation (expected: only keys with leading/trailing spaces, which the game can't match).

  python extraction/verify_ui.py      (after `python tools/install.py full` or ui.py build + patch)
"""
import re
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "tools"))
import common  # noqa: E402
import mono  # noqa: E402
import ui  # noqa: E402


def main():
    B = common.build()
    for f in (B / "EXAPUNKS.exe", B / "strings.csv"):
        if not f.exists():
            sys.exit(f"{f} missing: run `python tools/install.py full` first")
    exe = mono.compile_cs(HERE / "Extract.cs", "Extract")
    run = common.WS / "run/verify"
    if run.exists():
        shutil.rmtree(run)
    (run / "Content").mkdir(parents=True)
    shutil.copy2(B / "EXAPUNKS.exe", run / "EXAPUNKS.exe")
    shutil.copy2(B / "strings.csv", run / "Content/strings.csv")
    for dll in common.game().glob("*.dll"):
        if not (dll.name == "mscorlib.dll" or dll.name.startswith("System")):
            shutil.copy2(dll, run / dll.name)
    if not ui.dest().exists():
        sys.exit(f"{ui.dest()} not found: nothing to verify")
    src = ui.read(ui.SRC, 4)
    trs = ui.read(ui.dest(), 3)
    keys = list(src.items())
    (run / "keys.tsv").write_text("".join(f"{en}\t{ctx}\n" for _, (en, ctx, _) in keys), encoding="utf-8")
    print(mono.run(exe, "verify", run / "EXAPUNKS.exe", common.lang_name(), run / "keys.tsv", run / "got.txt", cwd=run).strip())
    got = (run / "got.txt").read_text(encoding="utf-8").splitlines()
    if len(got) != len(keys):
        sys.exit(f"got {len(got)} results for {len(keys)} keys; see the messages above")
    bad = []
    for (n, _), g in zip(keys, got):
        want = ui.unescape(trs[n][1]).replace("--", "—")
        if ui.unescape(g) != want:
            bad.append(n)
    print(f"{len(keys) - len(bad)}/{len(keys)} strings resolve to the translation in the game's own code")
    if bad:
        print("not matching:", ", ".join(f"#{n} {src[n][0]!r}" for n in bad))


if __name__ == "__main__":
    main()
