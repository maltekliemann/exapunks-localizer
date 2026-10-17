#!/usr/bin/env python3
"""Extract translatable dialogue from EXAPUNKS vignette CSVs and rebuild them translated.

The game's CSVs are hand-edited and inconsistent (quoted/unquoted fields, trailing commas,
missing closing quotes, mixed BOM/EOL). We never re-serialize a line from scratch: each
dialogue line is split into prefix + text + suffix, and only the text is swapped out.

  extract                      -> workspace/source/vignettes/<name>.txt (numbered, readable)
  check [name ...] [--partial] -> validate workspace/<lang>/vignettes/<name>.json against the source
  build [name ...] [--partial] -> workspace/build/vignettes/<name>.csv

Without names, every source file is processed and a missing translation file is an error
(--partial turns that off while work is in progress). With names (e.g. `check tutorial-1`),
only those files are checked/built, so parallel translators only see their own errors.
A full build (no names) empties workspace/build/vignettes/ first, so stale files never ship.

Translation file format: {"<line number>": "<translated text>", ...} with one entry per numbered
line of the extracted .txt. The translation goes into the English column: the game only reads
English, French, Chinese and Japanese from these files, and the patched exe falls back to
English for every other language.
"""
import json, re, sys

import common

SRC = common.backup() / "Content/vignettes"
SPEAKER = re.compile(r'^("[^"]*"|[^,"]*),(.*)$')


def parse_line(line):
    """Return (prefix, text, suffix, speaker) for a dialogue line, or None for structure lines."""
    if not line.strip() or line.strip() == "," or re.match(r"^(SECTION|ACTION)-", line):
        return None
    m = SPEAKER.match(line)
    if not m:
        raise ValueError(f"unparseable line: {line!r}")
    spk, rest = m.group(1), m.group(2)
    prefix = spk + ","
    if rest.startswith('"'):
        if len(rest) > 1 and rest.endswith('"'):
            return prefix + '"', rest[1:-1], '"', spk.strip('"')
        return prefix + '"', rest[1:], "", spk.strip('"')  # missing closing quote (original quirk)
    return prefix, rest, "", spk.strip('"')


def load(path):
    """-> (bom, eol, lines). Lines are split on the file's own line ending (CRLF in the shipped
    files; LF or CR are handled too) and written back with the same one."""
    raw = path.read_bytes()
    bom = raw.startswith(b"\xef\xbb\xbf")
    text = raw[3:].decode("utf-8") if bom else raw.decode("utf-8")
    eol = "\r\n" if "\r\n" in text else ("\n" if "\n" in text else ("\r" if "\r" in text else "\r\n"))
    return bom, eol, text.split(eol)


def entries(path):
    bom, eol, lines = load(path)
    out = []
    section = None
    for i, line in enumerate(lines):
        if line.startswith("SECTION-"):
            section = line.rstrip(",")
        p = parse_line(line)
        if p:
            out.append((i, section, p))
    return bom, eol, lines, out


def extract():
    dst = common.source() / "vignettes"
    dst.mkdir(parents=True, exist_ok=True)
    for f in sorted(SRC.glob("*.csv")):
        if not f.stat().st_size:
            continue
        _, _, lines, ents = entries(f)
        buf, last = [], None
        for i, section, (_, text, _, spk) in ents:
            if section != last:
                buf.append(f"\n== {section} ==")
                last = section
            who = spk if spk else "   ↳ alt"
            buf.append(f"[{i}] {who}: {text}")
        if not buf:
            continue
        out = buf[0].lstrip("\n") + "\n" + "\n".join(buf[1:]) + "\n"
        (dst / (f.stem + ".txt")).write_bytes(out.encode("utf-8"))
    print("extracted to", dst)


MARKUP = [r"\{[^}]*\}", r"<[A-Z_]+>"]


def problems(name, de):
    _, _, _, ents = entries(SRC / f"{name}.csv")
    errs = []
    if not isinstance(de, dict):
        return [f"{name}: the JSON must be an object {{\"<line>\": \"<text>\", ...}}"]
    ids = {str(i): text for i, _, (_, text, _, _) in ents}
    for k in ids:
        if k not in de:
            errs.append(f"{name}: missing line {k}")
    for k, v in de.items():
        if k not in ids:
            errs.append(f"{name}: unknown line {k}")
            continue
        if not isinstance(v, str):
            errs.append(f"{name}[{k}]: value must be a string, got {type(v).__name__}")
            continue
        en = ids[k]
        if "\n" in v or "\r" in v:
            errs.append(f"{name}[{k}]: line break in translation (one dialogue line = one line): {v!r}")
        if '"' in v:
            errs.append(f"{name}[{k}]: ASCII double quote in translation (use your language's quotes): {v!r}")
        if not v.strip():
            errs.append(f"{name}[{k}]: empty translation")
        for ch in "_*":
            if en.count(ch) != v.count(ch):
                errs.append(f"{name}[{k}]: markup '{ch}' count differs: {en!r} -> {v!r}")
        for pat in MARKUP:
            if len(re.findall(pat, en)) != len(re.findall(pat, v)):
                errs.append(f"{name}[{k}]: {{profanity}}/<PLACEHOLDER> count differs: {en!r} -> {v!r}")
        if re.findall(r"<[A-Z_]+>", en) != re.findall(r"<[A-Z_]+>", v):
            errs.append(f"{name}[{k}]: placeholder changed")
    return errs


def sources(names):
    """Source CSVs that contain dialogue, optionally restricted to the given names."""
    files = [f for f in sorted(SRC.glob("*.csv")) if f.stat().st_size and entries(f)[3]]
    if names:
        known = {f.stem for f in files}
        unknown = [n for n in names if n not in known]
        if unknown:
            sys.exit(f"unknown vignette file(s): {', '.join(unknown)}")
        files = [f for f in files if f.stem in names]
    return files


def build(check_only=False, names=(), partial=False):
    dst = common.build() / "vignettes"
    if not check_only and not names and dst.exists():
        for old in dst.glob("*"):
            old.unlink()
    dst.mkdir(parents=True, exist_ok=True)
    errs, done, missing = [], 0, 0
    for f in sources(names):
        jf = common.tr() / "vignettes" / (f.stem + ".json")
        if not jf.exists():
            missing += 1
            if not partial:
                errs.append(f"{f.stem}: missing translation ({jf.name} not found)")
            continue
        try:
            de = json.loads(jf.read_text(encoding="utf-8-sig"))
        except ValueError as e:
            errs.append(f"{f.stem}: invalid JSON: {e}")
            continue
        e = problems(f.stem, de)
        errs += e
        if e or check_only:
            done += 0 if e else 1
            continue
        bom, eol, lines, ents = entries(f)
        for i, _, (prefix, _, suffix, _) in ents:
            v = de[str(i)]
            if not prefix.endswith('"') and "," in v:  # unquoted original: quote it now
                prefix, suffix = prefix + '"', '"'
            lines[i] = prefix + v + suffix
        data = eol.join(lines).encode("utf-8")
        (dst / f.name).write_bytes((b"\xef\xbb\xbf" if bom else b"") + data)
        done += 1
    print("\n".join(errs) if errs else "no problems")
    extra = f", {missing} without translation" if missing else ""
    print(f"{'checked' if check_only else 'built'}: {done} files, {len(errs)} problems{extra}")
    return not errs


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help", "help") or args[0] not in ("extract", "check", "build"):
        print(__doc__)
        sys.exit(0 if not args or args[0] in ("-h", "--help", "help") else 2)
    cmd, rest = args[0], args[1:]
    names = [a for a in rest if not a.startswith("--")]
    if cmd == "extract":
        extract()
        sys.exit(0)
    sys.exit(0 if build(cmd == "check", names, "--partial" in rest) else 1)
