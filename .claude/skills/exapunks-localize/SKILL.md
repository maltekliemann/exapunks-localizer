---
name: exapunks-localize
description: Translate a locally installed copy of the game EXAPUNKS (dialogue, puzzle briefings, the WorkHouse minigame, optionally menus/UI and the TRASH WORLD NEWS manual PDFs) into German, French, Russian, Chinese or Japanese, using subagents for translation and review, and install/uninstall the result. Only German has been carried through completely; other languages are untested in-game.
---

# Localize EXAPUNKS

You translate the user's own copy of EXAPUNKS. Everything game-derived (backups, extracted
English, translations, builds) lives in the git-ignored `workspace/`; never copy any of it into
the repo or anywhere public.

**Python:** always run tools as `.venv/bin/python …` from the repo root (Windows:
`.venv\Scripts\python`); shell state does not persist between commands. Tell subagents the same.

Read first: `reference/game-internals.md` (how the game stores text and why each step exists).
Translators get `reference/translation-rules.md` + the glossary; reviewers get
`reference/review.md` + the glossary. (`reference/` = `.claude/skills/exapunks-localize/reference/`.)

## 0. Intake (ask before doing anything)

1. **Find the game.** Look in the usual places (macOS: `/Applications/EXAPUNKS.app`,
   `~/Applications`, `~/GOG Games`; Steam: `…/steamapps/common/EXAPUNKS`; Windows GOG:
   `C:\GOG Games\EXAPUNKS`, `C:\Program Files (x86)\GOG Galaxy\Games\EXAPUNKS`). Ask if not found.
2. **Agree on scope and register** with the user:
   - parts: dialogue + briefings + WorkHouse (always), menus/UI (needs the optional decryption
     step and a program patch, see §2 and §5), manual (optional, large);
   - language variant and audience (e.g. who will play it, age), form of address (du/Sie,
     tu/vous …);
   - scale: ~17,000 English words without the manual (dialogue ~11k, briefings ~4k, UI ~2k),
     roughly double with it; expect many subagents and hours of agent time. Fonts are downloaded from GitHub on first use.
3. **Prerequisites** (ask before system-wide installs): Python 3.10+ and
   `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`; Mono with `mcs` (for
   the program patch and UI extraction); poppler + tesseract for the manual only. The game must
   have been started once (so its `config.cfg` exists).

## 1. Setup and backup

```
.venv/bin/python tools/setup.py --game "<game folder or EXAPUNKS.app>" --lang <de|fr|ru|zh|ja>
```

Backs up `Content/`, `PackedContent/`, `EXAPUNKS.exe` and `config.cfg` to `workspace/backup/`
and writes `workspace/config.json`. It refuses a game that is already patched or set to a
non-English language. Tell the user where the backup is and that
`.venv/bin/python tools/install.py restore` undoes everything. If the game is later updated
(or "repaired" by the store), the backup is stale: start over with a fresh workspace.

**Glossary.** If `glossaries/<lang>.md` exists, copy it to `workspace/<lang>/glossary.md`.
Otherwise build one *before* any translation:
- take the language-neutral parts of `glossaries/de.md` (§1 hard rules without the German
  examples, §2 names kept) and use the English columns of its term tables as the checklist of
  terms to decide;
- decide and write down: form of address (player, briefings, EMBER-2), quotation marks and
  punctuation spacing, how the deliberately ungendered characters (Moss, Nivas) stay ungendered
  in your grammar (including first-person agreement in Moss's narration), keyboard key names,
  number/money/date/time formats, the register of the chat rooms;
- confirm address and audience choices with the user;
- run a pilot (2–3 dialogue files, one agent), merge its new terms, then start the waves.

Keep progress notes in `workspace/<lang>/notes/STATUS.md` (done, decisions, open points) so the
work survives context compaction.

## 2. Extract

```
.venv/bin/python tools/vignettes.py extract      # dialogue -> workspace/source/vignettes/*.txt
.venv/bin/python tools/descriptions.py extract   # briefings -> workspace/source/descriptions/*.txt
.venv/bin/python tools/workhouse.py extract      # WorkHouse crops + workspace/<lang>/workhouse.json
```

**Menus/UI (optional).** The UI strings are encrypted inside the exe. Only if `extraction/`
contains `extract_ui.py`: explain to the user that this step analyses and decrypts part of
*their* copy of the program, locally; that store/licence terms may prohibit reverse engineering;
and that it is their decision. **Only after the user agrees:**

```
.venv/bin/python extraction/extract_ui.py        # -> workspace/source/ui_strings.tsv
.venv/bin/python tools/ui.py template            # -> workspace/<lang>/ui_strings.tsv to fill in
```

If `extraction/` is absent or the user declines: skip the UI entirely (no `ui.py` anywhere,
not in validator lists either); do not try to reconstruct a decryption tool. Menus stay English.

## 3. Translate (subagents, in waves)

Dialogue: about 6 agents × ~10 files. Keep each numbered character series together (e.g. all
`nivas-*`, all `ember-*`), and a puzzle's file with the chat rooms around it. Campaign order:
the task list rows in `workspace/source/ui_strings.tsv` (network names, one-line summaries and
meeting entries) appear in campaign order; match each vignette file to its task by its name and
its PRE section. Briefings: 2–3 agents. UI + WorkHouse: one agent.

**Every subagent prompt must include:** the repo root (absolute path), `<lang>`, an agent id,
the exact files assigned, the paths of `reference/translation-rules.md` (or `review.md`) and
`workspace/<lang>/glossary.md`, the Python path, and these rules: write UTF-8 JSON without
`\u` escapes; validate only your own files and fix every error in them:

```
.venv/bin/python tools/vignettes.py check <names…>      # file names without extension
.venv/bin/python tools/descriptions.py check <names…>
.venv/bin/python tools/ui.py check                      # only if UI is in scope
.venv/bin/python tools/workhouse.py check
```

Agents record new terms in `workspace/<lang>/notes/newterms-<agent>.md`. After each wave, merge
them into the glossary (one rendering per term) before the next wave and the reviews. At the
end, a full `check` without names must pass (it also reports untranslated files).

## 4. Review (subagents)

Adversarial but not nitpicky, per `reference/review.md`: meaning, consistency with the ledger
and across files, hard rules, broken grammar, label length. Reviewers fix in place, log every
change in `workspace/<lang>/notes/review-<round>.md`, rerun validators on their files. Rounds:
dialogue (two passes, split by chapters), a cross-file consistency pass, briefings, UI +
WorkHouse, manual. Never let two agents edit the same file at the same time.

## 5. Build and install (ask first; the game must be closed)

Explain the two modes and let the user choose:

- `text`: dialogue, briefings, WorkHouse textures (+ manual PDFs if built). The game program is
  not modified; the game language stays English, so menus stay English.
- `full`: additionally a **patched copy of `EXAPUNKS.exe`** (one method: the localization lookup
  falls back to English; without it, non-English settings break briefings and dialogue), the
  translated UI table, and the game language set in `config.cfg`. Modifying the program is
  subject to the same terms caveat as the extraction; it is the user's decision.

```
.venv/bin/python tools/install.py text
.venv/bin/python tools/install.py full
.venv/bin/python tools/install.py restore      # original English game
```

Each mode first restores the files it manages, so switching modes is safe. `install.py` refuses
to run while the game is running or if the game files changed since the backup.

After `full`: if `extraction/verify_ui.py` exists, run it (every UI string is looked up through
the game's own code; expect all but keys with leading/trailing spaces). Look at
`workspace/build/workhouse-preview/*.png` before handing over. **For languages other than
German, `full` mode has not been tested in the game:** before translating everything, install a
pilot (one dialogue file, a briefing, a few UI strings) in `full` mode and have the user check
it in the game.

## 6. Manual (optional, labour-intensive)

The manual PDFs are scans; translating them means OCR, erasing English and typesetting the
translation per spread. Follow `reference/manual.md`. `install.py` picks up any PDFs in
`workspace/build/manual/`.

## 7. Hand over for an in-game test

Ask the user to play through: task list, options and controls, an editor session with a test
run, a hacker battle, solitaire, a WorkHouse job (also with low texture quality, which uses
the half-size textures), and dialogues with choices. Ask for screenshots of clipped text,
leftover English and any crash. Leftover English usually means text baked into a texture
(`tools/tex.py` decodes them; `tools/workhouse.py` shows how to redraw) or a hardcoded string
that does not go through the localization function.

## Rules for you

- Never commit or publish anything from `workspace/`. Before any commit, run
  `.venv/bin/python tools/check_release.py`. Contributing a glossary for a new language back is
  welcome: terms only, no sentences, and the check must pass.
- Never modify `workspace/backup/`. Never edit game files directly; only `install.py` does.
- Report validator failures and test results as they are.
