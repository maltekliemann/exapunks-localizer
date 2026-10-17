# exapunks-localizer

A toolkit and [Claude Code](https://claude.com/claude-code) skill for translating **your own
copy** of [EXAPUNKS](https://www.zachtronics.com/exapunks/) (Zachtronics, 2018) into another
language: dialogue, puzzle briefings, menus and other UI, the WorkHouse minigame, and optionally
the TRASH WORLD NEWS manual.

**This repository contains no game files and no game text or translation**, apart from names,
single terms and a few short UI labels in the sample glossary. You bring the game; the skill has
Claude extract the English from your copy, translate it with a glossary and subagents, review
it, and install it. Extraction, building and installing run locally; for translation the text
is sent to Claude like in any Claude Code session. Uninstalling restores the original files
from a backup.

## What you get

| Part | How | Mode |
|---|---|---|
| Dialogue, cutscenes, chat rooms | rewrite `Content/vignettes/*.csv` byte-faithfully | text, full |
| Puzzle briefings | `Content/descriptions/en/*.txt` | text, full |
| Menus, task list, editor, errors (~500 strings) | the game's own `strings.csv` localization table + a one-method patch so non-English settings don't break; needs the optional `extraction/` | full |
| WorkHouse job screen | text painted into textures, redrawn with matching open fonts | text, full |
| Manual PDFs (optional) | OCR, erase, typeset in place, rebuild all PDF variants | text, full |

Languages: the engine knows German, French, Russian, Chinese and Japanese. **Only German has
been carried through completely and played in-game.** For other languages the tools are
generic, but `full` mode is untested in the game (the skill has you install a pilot first); the
WorkHouse and manual fonts cover Latin script (Cyrillic partly), CJK not at all.

What was tested, on the GOG macOS build: the tools reproduce a complete German translation
byte-identically (dialogue, briefings, UI table, patched program); `install.py text`, `full`
and `restore` on a copy of the game (restore is byte-identical to the backup); the UI lookup
check through the game's own code; the manual pipeline against the original renders.
Steam/Windows/Linux builds should work (code is located by structure, not by fixed addresses)
but are untested; settings-file locations there are guesses.

## Usage

Requirements: Python 3.10+, Mono (`mcs`) for the program patch and UI extraction; for the
manual also poppler and tesseract. Run the tools with the venv's Python (`.venv/bin/python`).

```
git clone <this repo> && cd exapunks-localizer
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
claude          # then: "Translate my EXAPUNKS into German. The game is at …"
```

The skill (`.claude/skills/exapunks-localize/SKILL.md`) drives the whole process. You can also
run the tools yourself:

```
.venv/bin/python tools/setup.py --game "/path/to/EXAPUNKS.app" --lang de   # backup + config
.venv/bin/python tools/vignettes.py extract | check | build
.venv/bin/python tools/descriptions.py extract | check | build
.venv/bin/python tools/workhouse.py extract | check | build
.venv/bin/python extraction/extract_ui.py     # optional, see extraction/README.md
.venv/bin/python tools/ui.py template | check | build
.venv/bin/python tools/install.py text | full | restore
```

Everything you produce lives in `workspace/` (git-ignored). Before committing anything to a
fork, run `.venv/bin/python tools/check_release.py`: it flags game-like files and text from the
game or from your translation found in the files git would commit. It is a safety net, not a
guarantee (very short phrases can't be told apart from ordinary words); look at your diff too.

If the game is updated or repaired by your store, your backup no longer matches it: `install.py`
refuses to run, and you start over with a fresh workspace (translations can be copied over).

## Layout

```
.claude/skills/exapunks-localize/   the skill + reference docs (game internals, translation
                                    rules, review brief, manual pipeline)
glossaries/de.md                    starting glossary for German (terms only, no game text)
tools/                              setup, extract/check/build per part, install/restore,
                                    texture codec, WorkHouse redraw, program patch, manual pipeline
extraction/                         optional UI-string decryption (separable, see its README)
workspace/                          yours: backups, extracted text, translations, builds (ignored)
```

Fonts (Roboto, Big Shoulders Display, Kalam and the manual's fonts) are downloaded from the
google/fonts repository (pinned commit) at first use and are not included; they are under the
SIL Open Font License or, for a few (e.g. Permanent Marker, Special Elite), Apache 2.0.
Mono.Cecil is taken from your Mono installation.

## License

MIT for the code and documentation in this repository (see `LICENSE`).
