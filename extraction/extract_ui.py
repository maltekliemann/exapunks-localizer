#!/usr/bin/env python3
"""Produce workspace/source/ui_strings.tsv: every UI string the game passes to its localization
function, plus the rows of the original Content/strings.csv. Read string-extraction.md first.

  python extraction/extract_ui.py

Works on the backed-up original exe. Runs Extract.exe (compiled on first use with Mono) in a
scratch directory that holds a copy of the exe and the game's own libraries.
"""
import csv
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "tools"))
import common  # noqa: E402
import mono  # noqa: E402


def main():
    if not (common.backup() / "EXAPUNKS.exe").exists():
        sys.exit("no backup of EXAPUNKS.exe in workspace/backup: run tools/setup.py first")
    exe = mono.compile_cs(HERE / "Extract.cs", "Extract")
    run = common.WS / "run/extract"
    if run.exists():
        shutil.rmtree(run)
    run.mkdir(parents=True)
    shutil.copy2(common.backup() / "EXAPUNKS.exe", run / "EXAPUNKS.exe")
    for dll in common.game().glob("*.dll"):  # the game's libraries, minus the framework it bundles
        if not (dll.name == "mscorlib.dll" or dll.name.startswith("System")):
            shutil.copy2(dll, run / dll.name)
    raw = run / "strings.tsv"
    print(mono.run(exe, run / "EXAPUNKS.exe", raw, cwd=run).strip())

    if not raw.exists():
        sys.exit(f"Extract.exe produced no output ({raw}); see the messages above")
    rows = [l.split("\t") for l in raw.read_text(encoding="utf-8").splitlines()[1:] if l.strip()]
    if not rows:
        sys.exit("no UI strings found: unknown build? Read extraction/string-extraction.md")
    seen = {(r[0], r[1]) for r in rows}
    # keys already present in the shipped strings.csv (shared engine strings)
    shipped = common.backup() / "Content/strings.csv"
    if shipped.exists():
        for rec in csv.reader(shipped.read_text(encoding="utf-8-sig").splitlines()):
            if rec and rec[0].strip():
                k = (rec[0].strip().replace("\n", "\\n"), (rec[1].strip() if len(rec) > 1 else ""))
                if k not in seen:
                    seen.add(k)
                    rows.append([k[0], k[1], "strings.csv"])
    out = common.source() / "ui_strings.tsv"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("n\tenglish\tcontext\thint\n" + "".join(f"{i}\t{r[0]}\t{r[1]}\t{r[2]}\n" for i, r in enumerate(rows, 1)),
                   encoding="utf-8")
    print(f"wrote {out} ({len(rows)} strings)")


if __name__ == "__main__":
    main()
