#!/usr/bin/env python3
"""Check that the repository contains no game files, no game text and none of your translation.

  python tools/check_release.py [--skip-workspace-scan]

Scans what git would commit (tracked + untracked, not ignored) when the repo is a git repository,
otherwise every file outside workspace/, virtualenvs, .git and __pycache__.

1. Fails on binary/game-like files (executables, libraries, textures, PDFs, images, fonts, audio,
   video, archives, CSV), files > 512 KB, tracked files under workspace/, and files that aren't
   UTF-8 (they can't be scanned reliably).
2. Builds fingerprints from the game's English text (dialogue, briefings, UI strings, manual OCR;
   from workspace/) and from your translations (workspace/<lang>/: dialogue, briefings, UI,
   WorkHouse, manual specs), all normalized the same way (HTML entities decoded, soft hyphens
   removed, hyphenated line breaks joined, whitespace and punctuation ignored, case-folded), and
   fails on any repository file that contains
     - a run of 6 consecutive words from that text, or
     - a whole dialogue line, briefing line, UI string or WorkHouse text of 4+ words, or of 3 words
       and 15+ characters (in glossaries/: 5+ words, since glossaries hold short labels), or
     - more than 10 distinct UI strings of 2+ words (a pasted string table).
   Strings in which every word is capitalized (names, titles, Title Case labels) are left out of
   the last two rules: they can't be told apart from the names a glossary lists.
3. Warns (without failing) about 6-word runs shared with your own glossary and notes in
   workspace/<lang>/: those may legitimately overlap with a glossary in glossaries/, but review
   each one.
Single terms, names and very short lines can't be told apart from ordinary vocabulary; review
glossaries and examples by eye.
Exits non-zero if anything fails. Run it before every commit.
"""
import html
import json
import re
import subprocess
import sys

import common

SKIP_DIRS = {"workspace", ".git", "__pycache__", "node_modules"}
BAD_EXT = {
    ".exe", ".dll", ".so", ".dylib", ".bin", ".tex", ".array", ".packedfont", ".pdf", ".csv",
    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".ico", ".svg", ".tif", ".tiff", ".psd",
    ".ttf", ".otf", ".ttc", ".woff", ".woff2",
    ".mp3", ".ogg", ".wav", ".flac", ".m4a", ".mp4", ".webm", ".mov", ".avi",
    ".tar", ".gz", ".tgz", ".zip", ".7z", ".rar", ".xz", ".bz2",
}
N = 6
MAX_KB = 512


# ---------------------------------------------------------------- normalization

def normalize(s):
    """Plain text: HTML tags/entities resolved, soft hyphens gone, hyphenated line breaks
    joined, every kind of whitespace (NBSP, narrow NBSP, …) collapsed."""
    s = re.sub(r"<[^>]+>", " ", s)
    s = html.unescape(s)
    s = s.replace("­", "")
    s = s.replace("\\n", "\n")                       # escaped line breaks in TSV/JSON values
    s = re.sub(r"(\w)-[ \t]*\r?\n[ \t]*(\w)", r"\1\2", s)
    return re.sub(r"\s+", " ", s)


def words(s):
    return re.findall(r"[^\W_]+", normalize(s).lower())


def shingles(ws):
    return {" ".join(ws[i:i + N]) for i in range(len(ws) - N + 1)}


def alpha_tokens(s):
    return [t for t in normalize(s).split() if re.search(r"[^\W\d_]", t)]


def name_like(s):
    """Every word capitalized (names, titles, Title Case labels): indistinguishable from the
    proper names a glossary legitimately lists, so not used for exact matching."""
    toks = alpha_tokens(s)
    return bool(toks) and all(re.sub(r"^[^\w]+", "", t)[:1].isupper() for t in toks)


def exact_entry(s):
    """(token string, word count, length) for exact matching, or None for names and fragments."""
    ws = words(s)
    if len(alpha_tokens(s)) < 3 or name_like(s):
        return None
    return " ".join(ws), len(alpha_tokens(s)), len(normalize(s).strip())


def exact_applies(entry, in_glossary):
    """Whole-line matching threshold. Glossaries exist to hold short labels and catchphrases,
    so there only lines of 5+ words count; elsewhere 4+ words, or 3 words of 15+ characters."""
    _, n, length = entry
    return n >= 5 if in_glossary else (n >= 4 or (n == 3 and length >= 15))


def ui_entry(s):
    """Token string for the string-table rule: 2+ words, not name-like."""
    if len(alpha_tokens(s)) < 2 or name_like(s):
        return None
    return " ".join(words(s))


# ---------------------------------------------------------------- what to scan

def is_venv(path):
    return (path / "pyvenv.cfg").exists()


def git_files():
    try:
        r = subprocess.run(["git", "-C", str(common.REPO), "ls-files", "-co", "--exclude-standard", "-z"],
                           capture_output=True, check=True)
    except (OSError, subprocess.CalledProcessError):
        return None
    return [common.REPO / p for p in r.stdout.decode("utf-8", "replace").split("\0") if p]


def walk_files():
    out = []

    def walk(d):
        for p in sorted(d.iterdir()):
            if p.is_dir():
                if p.name in SKIP_DIRS or is_venv(p) or p.resolve() == common.WS:
                    continue
                walk(p)
            elif p.is_file():
                out.append(p)

    walk(common.REPO)
    return out


def repo_files():
    if (common.REPO / ".git").exists():
        files = git_files()
        if files is not None:
            return [p for p in files if p.is_file()], "git"
    return walk_files(), "file walk"


# ---------------------------------------------------------------- fingerprints

# JSON keys whose values are tool settings or template notes, not translated text
NOT_TEXT = {"_notes", "css", "font", "erase", "source", "align", "valign", "color", "id", "preset", "weight"}


def strings_in(x, key=None):
    if key in NOT_TEXT:
        return
    if isinstance(x, str):
        yield x
    elif isinstance(x, dict):
        for k, v in x.items():
            yield from strings_in(v, k)
    elif isinstance(x, list):
        for v in x:
            yield from strings_in(v, key)


def read(f):
    return f.read_text(encoding="utf-8-sig", errors="replace")


def json_strings(f):
    try:
        return list(strings_in(json.loads(read(f))))
    except ValueError:
        return read(f).splitlines()


def tsv_fields(f, cols=None):
    out = []
    for i, line in enumerate(read(f).splitlines()):
        fields = line.split("\t")
        if i == 0 and f.suffix == ".tsv" and fields[:1] == ["n"]:
            continue  # header
        out += [fields[c] for c in cols if c < len(fields)] if cols else fields
    return out


class Corpus:
    def __init__(self):
        self.shingles = set()
        self.exact = {}        # token string -> (entry, example original text)
        self.ui = {}           # token string -> example
        self.warn = set()      # shingles from your glossary/notes

    def add(self, texts, exact=True, ui=False):
        for t in texts:
            self.shingles |= shingles(words(t))
            if exact:
                e = exact_entry(t)
                if e:
                    self.exact.setdefault(e[0], (e, t.strip()))
            if ui:
                k = ui_entry(t)
                if k:
                    self.ui.setdefault(k, t.strip())


def vignette_texts(f):
    import csv
    out = []
    for row in csv.reader(read(f).splitlines()):
        if len(row) >= 2 and not (row[0].startswith("SECTION-") or row[0].startswith("ACTION-")):
            out += [c for c in row[1:] if c.strip()]
    return out


def corpus():
    c = Corpus()
    b, src = common.backup(), common.source()
    # the game's English
    for f in (b / "Content/vignettes").glob("*.csv"):
        c.add(vignette_texts(f))
    for f in (b / "Content/descriptions").rglob("*.txt"):
        c.add(read(f).splitlines())
    if (b / "Content/strings.csv").exists():
        import csv
        for row in csv.reader(read(b / "Content/strings.csv").splitlines()):
            c.add([x for x in row if x.strip()], ui=True)
    if (src / "ui_strings.tsv").exists():
        c.add(tsv_fields(src / "ui_strings.tsv", [1]), ui=True)
    for f in src.rglob("*.txt"):
        if f.parent.name == "vignettes":   # "[12] SPEAKER: text"
            c.add([re.sub(r"^\[\d+\][^:]*:\s*", "", l) for l in read(f).splitlines()])
        elif "ocr" in f.parts:             # manual OCR: whole page, line breaks joined
            c.add([read(f)], exact=False)
            c.add([l for l in read(f).splitlines()])
        else:
            c.add(read(f).splitlines())
    # your translations
    for lang in common.LANGS:
        d = common.WS / lang
        if not d.exists():
            continue
        for f in d.rglob("*"):
            if not f.is_file():
                continue
            if f.name == "glossary.md" or "notes" in f.relative_to(d).parts:
                c.warn |= shingles(words(read(f)))
                continue
            if f.name == "ui_strings.tsv":
                c.add(tsv_fields(f, [1, 2]), ui=True)
            elif f.name == "workhouse.json":
                c.add([v for k, v in json.loads(read(f)).items() if not k.startswith("_") and isinstance(v, str)])
            elif f.suffix == ".json":
                c.add(json_strings(f))
            elif f.suffix in (".txt", ".md", ".tsv"):
                c.add(read(f).splitlines())
    return c


# ---------------------------------------------------------------- main

def main():
    problems, warnings = [], []
    files, mode = repo_files()
    WS = common.WS
    for p in files:
        rel = p.relative_to(common.REPO)
        inside_ws = rel.parts[:1] == ("workspace",)
        try:
            p.resolve().relative_to(WS)
            inside_ws = True
        except ValueError:
            pass
        if inside_ws:
            problems.append(f"{rel}: inside the workspace; never commit it")
            continue
        if p.suffix.lower() in BAD_EXT:
            problems.append(f"{rel}: file type {p.suffix} doesn't belong in the repo")
        elif p.stat().st_size > MAX_KB * 1024:
            problems.append(f"{rel}: {p.stat().st_size // 1024} KB, suspiciously large")
        else:
            try:
                p.read_bytes().decode("utf-8")
            except UnicodeDecodeError:
                problems.append(f"{rel}: not UTF-8 text, can't be checked; convert or remove it")

    if "--skip-workspace-scan" not in sys.argv:
        if not common.backup().exists():
            sys.exit("workspace/backup not found: can't scan for game text (or pass --skip-workspace-scan)")
        c = corpus()
        print(f"fingerprint: {len(c.shingles)} six-word runs, {len(c.exact)} whole lines/strings, "
              f"{len(c.ui)} UI strings (scanning {len(files)} files via {mode})")
        for p in files:
            if p.suffix.lower() in BAD_EXT or p.stat().st_size > MAX_KB * 1024:
                continue
            rel = p.relative_to(common.REPO)
            text = p.read_bytes().decode("utf-8", errors="replace")
            ws = words(text)
            hay = " " + " ".join(ws) + " "
            sh = shingles(ws)
            hits = sorted(sh & c.shingles)
            if hits:
                problems.append(f"{rel}: {len(hits)} six-word runs from the game/your translation, e.g. {hits[0]!r}")
            in_glossary = "glossaries" in rel.parts
            ex = sorted(k for k, (e, _) in c.exact.items() if exact_applies(e, in_glossary) and f" {k} " in hay)
            if ex:
                problems.append(f"{rel}: {len(ex)} whole lines/strings from the game/your translation, "
                                f"e.g. {c.exact[ex[0]][1]!r}")
            ui = [k for k in c.ui if f" {k} " in hay]
            if len(ui) > 10:
                problems.append(f"{rel}: contains {len(ui)} UI strings (a string table?), e.g. "
                                + ", ".join(repr(c.ui[k]) for k in ui[:3]))
            w = sorted((sh & c.warn) - c.shingles)
            if w:
                warnings.append(f"{rel}: {len(w)} six-word runs shared with your glossary/notes, e.g. {w[0]!r}")

    for w in warnings:
        print("WARN", w)
    print("\n".join("FAIL " + p for p in problems) if problems
          else f"OK: {len(files)} files, no game files or game/translation text found")
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
