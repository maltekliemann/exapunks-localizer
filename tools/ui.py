#!/usr/bin/env python3
"""UI strings via the game's built-in localization table (Content/strings.csv).

Source:      workspace/source/ui_strings.tsv   n<TAB>english<TAB>context<TAB>hint
             (made by the optional extraction/extract_ui.py; escapes: \\n newline, \\t tab, \\\\ backslash)
Translation: workspace/<lang>/ui_strings.tsv   n<TAB>english<TAB>translation
             (n and english copied verbatim from the source; same escapes)

  template -> write workspace/<lang>/ui_strings.tsv with an empty translation column (only if missing)
  check    -> validate the translation against the source
  build    -> workspace/build/strings.csv   (columns: text, context, de, fr, ru, zh, ja)
  relabel  -> workspace/build/descriptions-ui/: briefings with the quoted English button labels
              ("SHOW GOAL", "TEST RUN", "SELECT OPPONENT") replaced by your translated labels,
              upper-cased, in typographic quotes of your language (used by `install.py full`)

strings.csv rules (from the game's parser): rows split on \\n, fields on commas outside "quotes",
"" is a literal quote, every field is trimmed, a literal backslash-n becomes a newline. Keys with
leading/trailing spaces can therefore never match; they are skipped. "--" is turned into an em
dash by the game when displaying.
"""
import re
import sys

import common

SRC = common.source() / "ui_strings.tsv"

# Briefing label (as quoted in descriptions/en) -> English UI string whose translation replaces it
RELABEL = {'"SHOW GOAL"': "Show Goal", '"TEST RUN"': "Test Run", '"SELECT OPPONENT"': "SELECT OPPONENT"}
QUOTES = {"de": ("„", "“"), "fr": ("«\u00a0", "\u00a0»"), "ru": ("«", "»"), "zh": ("“", "”"), "ja": ("「", "」")}


def unescape(s):
    return re.sub(r"\\(.)", lambda m: {"n": "\n", "t": "\t", "r": "\r", "\\": "\\"}.get(m.group(1), "\\" + m.group(1)), s)


def read(path, cols):
    if not path.exists():
        if path == SRC:
            raise SystemExit(f"{path} not found: UI strings not extracted (extraction/ absent or not run). "
                             "Skip ui.py; menus stay English.")
        raise SystemExit(f"{path} not found (run: python tools/ui.py template)")
    rows = {}
    for i, line in enumerate(path.read_text(encoding="utf-8-sig").split("\n")):
        line = line.rstrip("\r")
        if i == 0 or not line.strip():
            continue
        parts = line.split("\t")
        if len(parts) < cols:
            raise SystemExit(f"{path.name}:{i + 1}: expected {cols} tab-separated columns: {line!r}")
        rows[parts[0]] = parts[1:cols]
    return rows


def dest():
    return common.tr() / "ui_strings.tsv"


def problems():
    src, tr = read(SRC, 4), read(dest(), 3)
    errs = []
    for n, (en, _, _) in src.items():
        if n not in tr:
            errs.append(f"[{n}] missing: {en!r}")
            continue
        en2, t = tr[n]
        if en2 != en:
            errs.append(f"[{n}] english column was altered: {en2!r} (source {en!r})")
        if not t.strip():
            errs.append(f"[{n}] empty translation")
        for pat, what in [(r"\{\d+\}", "placeholders {0}"), (r"\\n", "line breaks \\n"),
                          (r"\*[a-z0-9][a-z0-9_-]*\*", "*host* names"), (r"\*", "* markers"),
                          (r"<[A-Z_]+>", "<PLACEHOLDER>"), (r"\\\\\*", "escaped \\*")]:
            if sorted(re.findall(pat, en)) != sorted(re.findall(pat, t)):
                errs.append(f"[{n}] {what} differ: {en!r} -> {t!r}")
        stray_en = re.sub(r"\{\d+\}", "", en)
        stray_t = re.sub(r"\{\d+\}", "", t)
        if any(stray_t.count(c) != stray_en.count(c) for c in "{}"):
            errs.append(f"[{n}] braces that aren't {{n}} placeholders (the game formats these strings): {t!r}")
        if "--" in t:
            errs.append(f"[{n}] '--' becomes an em dash in-game; use a dash character instead")
    for n in tr:
        if n not in src:
            errs.append(f"[{n}] not in source")
    return src, tr, errs


def csv_field(s):
    s = unescape(s).replace("\n", "\\n")
    return '"' + s.replace('"', '""') + '"' if any(c in s for c in ',"') else s


def template():
    if dest().exists():
        sys.exit(f"{dest()} exists; not overwriting")
    src = read(SRC, 4)
    dest().parent.mkdir(parents=True, exist_ok=True)
    dest().write_text("n\tenglish\ttranslation\n" + "".join(f"{n}\t{en}\t\n" for n, (en, _, _) in src.items()), encoding="utf-8")
    print(f"wrote {dest()} ({len(src)} rows to translate)")


def build(src, tr):
    col = common.lang_column()
    lines = []
    for n, (en, ctx, _) in src.items():
        if unescape(en).strip() != unescape(en) or unescape(ctx).strip() != unescape(ctx):
            continue  # the game trims fields, so this key can never match
        row = [csv_field(en), csv_field(ctx), "", "", "", "", ""]
        row[col] = csv_field(tr[n][1])
        lines.append(",".join(row))
    out = common.build() / "strings.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(("\r\n".join(lines) + "\r\n").encode("utf-8"))
    print(f"wrote {out} ({len(lines)} rows, translation in column {col})")


def relabel(tr):
    by_en = {v[0]: v[1] for v in tr.values()}
    src, dst = common.build() / "descriptions", common.build() / "descriptions-ui"
    if not src.exists():
        sys.exit("build the briefings first (python tools/descriptions.py build)")
    dst.mkdir(parents=True, exist_ok=True)
    q0, q1 = QUOTES.get(common.lang(), ("\"", "\""))
    n = 0
    for f in sorted(src.glob("*.txt")):
        b = f.read_bytes()
        for quoted, en in RELABEL.items():
            if en in by_en:
                b = b.replace(quoted.encode(), (q0 + unescape(by_en[en]).upper() + q1).encode("utf-8"))
        n += b != f.read_bytes()
        (dst / f.name).write_bytes(b)
    print(f"relabelled {n} briefings -> {dst}")


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "check"
    if cmd in ("-h", "--help", "help") or cmd not in ("template", "check", "build", "relabel"):
        print(__doc__)
        sys.exit(0 if cmd in ("-h", "--help", "help") else 2)
    if cmd == "template":
        return template()
    src, tr, errs = problems()
    print("\n".join(errs) if errs else "no problems")
    print(f"checked {len(tr)}/{len(src)} strings, {len(errs)} problems")
    if errs and cmd != "check":
        sys.exit("not building: fix the problems first")
    if cmd == "build":
        build(src, tr)
    elif cmd == "relabel":
        relabel(tr)
    sys.exit(1 if errs else 0)


if __name__ == "__main__":
    main()
