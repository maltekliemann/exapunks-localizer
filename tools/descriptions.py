#!/usr/bin/env python3
"""Puzzle briefings (Content/descriptions/en/*.txt).

  extract                      -> workspace/source/descriptions/<name>.txt (UTF-8 copies, LF)
  check [name ...] [--partial] -> compare workspace/<lang>/descriptions/<name>.txt with the English
                                  (protected tokens, markup, paragraph/indent structure)
  build [name ...] [--partial] -> workspace/build/descriptions/<name>.txt, keeping each original's
                                  BOM and line ending (the shipped files use CRLF)

Without names every briefing is processed and a missing translation is an error (--partial
turns that off); with names only those files. A full build empties the output folder first.
Translations may be saved with or without BOM, LF or CRLF.

The game only loads descriptions/en/, so the translation is installed there (the patched exe
falls back to the English slot for the selected language).
"""
import re, sys

import common

SRC = common.backup() / "Content/descriptions/en"

# Tokens that must survive translation verbatim (same multiset).
PROTECTED = [
    r"\*[^*\s][^*]*?\*",          # *host* names
    r"‗[^‗]+‗",                   # ‗KEYWORDS‗
    r"#[A-Z]{2,}[A-Z0-9]*",       # #REGISTERS
    r"\b[A-Z]{3,}\b",             # instructions / abbreviations (KILL, TEST, CNS, HDI…)
    r"\d+",                        # numbers, file IDs
    r"\\[*_]",                     # escaped markup
]
UI_LABELS = ['"SHOW GOAL"', '"TEST RUN"', '"SELECT OPPONENT"']
# Words that appear in caps in the English but may be translated or inflected
CAPS_OK = {"EXA", "EXAS", "AND", "THE"}


def read(p):
    raw = p.read_bytes()
    bom = raw.startswith(b"\xef\xbb\xbf")
    txt = (raw[3:] if bom else raw).decode("utf-8")
    return bom, txt.replace("\r\n", "\n")


def eol_of(p):
    raw = p.read_bytes()
    return "\n" if b"\n" in raw and b"\r\n" not in raw else "\r\n"


def toks(s):
    out = []
    for pat in PROTECTED:
        out += [t for t in re.findall(pat, s) if t.upper() not in CAPS_OK]
    return sorted(out)


def problems(name, de):
    _, en = read(SRC / f"{name}.txt")
    errs = []
    a, b = toks(en), toks(de)
    if a != b:
        missing = [t for t in a if a.count(t) > b.count(t)]
        extra = [t for t in b if b.count(t) > a.count(t)]
        errs.append(f"{name}: protected tokens differ; missing {sorted(set(missing))} extra {sorted(set(extra))}")
    for lab in UI_LABELS:
        if lab in en and lab not in de:
            errs.append(f"{name}: UI label {lab} must stay in English with ASCII quotes (ui.py relabel swaps it in UI mode)")
    if en.count("_") != de.count("_"):
        errs.append(f"{name}: '_' markup count differs")
    pe, pd = en.strip("\n").split("\n\n"), de.strip("\n").split("\n\n")
    if len(pe) != len(pd):
        errs.append(f"{name}: paragraph count {len(pe)} -> {len(pd)}")
    ind_e = [l[: len(l) - len(l.lstrip(" "))] for l in en.split("\n") if l.startswith(" ")]
    ind_d = [l[: len(l) - len(l.lstrip(" "))] for l in de.split("\n") if l.startswith(" ")]
    if ind_e != ind_d:
        errs.append(f"{name}: indented lines differ ({len(ind_e)} -> {len(ind_d)})")
    return errs


def extract():
    dst = common.source() / "descriptions"
    dst.mkdir(parents=True, exist_ok=True)
    for f in sorted(SRC.glob("*.txt")):
        (dst / f.name).write_bytes(read(f)[1].encode("utf-8"))
    print("extracted to", dst)


def run(build, names=(), partial=False):
    errs, n, missing = [], 0, 0
    out = common.build() / "descriptions"
    if build and not names and out.exists():
        for old in out.glob("*"):
            old.unlink()
    out.mkdir(parents=True, exist_ok=True)
    files = sorted(SRC.glob("*.txt"))
    if names:
        unknown = [x for x in names if not (SRC / f"{x}.txt").exists()]
        if unknown:
            sys.exit(f"unknown briefing(s): {', '.join(unknown)}")
        files = [f for f in files if f.stem in names]
    for f in files:
        d = common.tr() / "descriptions" / f.name
        if not d.exists():
            missing += 1
            if not partial:
                errs.append(f"{f.stem}: missing translation ({d.name} not found)")
            continue
        de = d.read_text(encoding="utf-8-sig").replace("\r\n", "\n")
        e = problems(f.stem, de)
        errs += e
        n += 1
        if build and not e:
            bom, en = read(f)
            de = de.rstrip("\n") + ("\n" if en.endswith("\n") else "")
            (out / f.name).write_bytes((b"\xef\xbb\xbf" if bom else b"") + de.replace("\n", eol_of(f)).encode("utf-8"))
    print("\n".join(errs) if errs else "no problems")
    extra = f", {missing} without translation" if missing else ""
    print(f"{'built' if build else 'checked'}: {n} files, {len(errs)} problems{extra}")
    return not errs


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help", "help") or args[0] not in ("extract", "check", "build"):
        print(__doc__)
        sys.exit(0 if not args or args[0] in ("-h", "--help", "help") else 2)
    cmd, rest = args[0], args[1:]
    if cmd == "extract":
        extract()
        sys.exit(0)
    names = [a for a in rest if not a.startswith("--")]
    sys.exit(0 if run(cmd == "build", names, "--partial" in rest) else 1)
