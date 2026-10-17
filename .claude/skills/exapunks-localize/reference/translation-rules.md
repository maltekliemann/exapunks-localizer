# Translator brief (all languages)

Give this file, together with `workspace/<lang>/glossary.md`, to every translator agent.
Paths are relative to the repo root; `<lang>` is the configured language code (e.g. `de`).
Run tools as `.venv/bin/python tools/…` from the repo root (Windows: `.venv\Scripts\python`).

## Before you start

1. **Read the glossary completely.** It is binding: tone, hard rules, names, fixed phrases,
   terminology. Look terms up every time instead of improvising.
2. Translate only the files assigned to you. Don't edit the glossary; record every new
   non-standard term you introduce in `workspace/<lang>/notes/newterms-<agent>.md` as
   `| English | translation | file |`, plus open questions.
3. Run the validator for your part after every file, **restricted to your files**
   (`.venv/bin/python tools/vignettes.py check tutorial-1 tutorial-2`, names without extension;
   same for `descriptions.py`). Other agents' files may be half-written; ignore their errors.
   Yours must report no problems before you finish. Write JSON as UTF-8 without `\u` escapes.

## Context in one paragraph

An alternate 1997 where everything runs on networks of small programs called EXAs. Moss,
the player, is a once-legendary hacker with memory gaps, suffering from a disease called
the phage that is converting their body into machinery bit by bit. A strange AI, EMBER-2, offers medication in exchange
for hacks and asks odd questions in between. Friends (Ghast, Isadora, the courier Nivas) and
an underground chat room of hackers fill in the world; the hacker zine TRASH WORLD NEWS
teaches the programming. Tone: cool, dry, a bit bleak, a bit funny. The source files give
you everything else; read a whole conversation before translating any line of it.

## What you translate and where it goes

| Part | Source (read-only) | Your output | Validator |
|---|---|---|---|
| Dialogue | `workspace/source/vignettes/<name>.txt` | `workspace/<lang>/vignettes/<name>.json` | `tools/vignettes.py check <names>` |
| Puzzle briefings | `workspace/source/descriptions/<name>.txt` | `workspace/<lang>/descriptions/<name>.txt` | `tools/descriptions.py check <names>` |
| UI strings (only if extracted) | `workspace/source/ui_strings.tsv` | `workspace/<lang>/ui_strings.tsv` | `tools/ui.py check` |
| WorkHouse screen | crops in `workspace/source/workhouse/` | `workspace/<lang>/workhouse.json` (template made by `extract`) | `tools/workhouse.py check` |

### Dialogue

Each source line looks like `[12] SPEAKER: text`; `== SECTION-… ==` headers mark
before-puzzle (PRE), after-puzzle (POST) and chat-room (CHAT) parts; `↳ alt` marks an
alternative to the line above. Output is one JSON object mapping **every** line number
(as a string) to the translated text only, no speaker:

```json
{"12": "…", "13": "…"}
```

Valid JSON (escape backslashes). Branches: a run of alternatives after a Moss line is a set
of player choices; the following alternative groups are the responses, **matched by
position** (response 2 answers choice 2). Read every path as its own conversation and make
each one work.

### Briefings

Plain UTF-8 text mirroring the source: same paragraphs, blank lines, indented lines (same
number of leading spaces), all markup, numbers, registers, instructions and host names.
Briefings are instructions: precise, imperative, addressed to the player. The puzzle must
stay solvable exactly as described in English: same numbers, order, conditions and edge
cases. Zine references use the translated article title from your glossary table, in your
language's quotation marks.

### UI strings

`ui_strings.tsv`: header line `n<TAB>english<TAB>translation`, then one row per source row
with `n` and `english` copied **verbatim** and your translation in column 3. Tabs only as
separators. Escapes as in the source: `\n` = line break (keep the same number), `\\` =
backslash. Neighbouring rows usually belong to the same screen; the source's hint column
names the screen class when known.

### WorkHouse

The WorkHouse job screen has its text painted into textures. `python tools/workhouse.py extract`
writes a crop image of every text area to `workspace/source/workhouse/<key>.png` and a template
`workspace/<lang>/workhouse.json`: one key per text area (empty value to fill in) plus a
`_notes` object with each key's limit (max lines, purpose). Look at each crop, fill in every key,
and use `\n` for a forced line break where the note allows two lines (long texts such as the
job description wrap automatically). The build shrinks text that doesn't fit, so shorter is
better. Buttons are one short word in CAPITALS (the engraved lettering is widely spaced); leave
`button.okay` as `OKAY` if that works in your language. The receipt stays as it is.
`python tools/workhouse.py check` also verifies that the fonts have every character you used;
then `build` and look at the before/after previews in `workspace/build/workhouse-preview/`.

## Hard rules (every part)

1. **The EXA language stays English**: instructions (`LINK`, `GRAB`, `COPY`, `KILL`, `TEST`,
   `MARK`, `@REP`…), registers (`X`, `T`, `F`, `M`, `GX`, `#NERV`…), keyword values in `‗…‗`.
   Code listings verbatim; only `NOTE` comments may be translated.
2. **Identifiers stay as shown on screen**: host names `*outbox*`, file IDs, hardware
   abbreviations (CNS, ARM, SA-N, V-CTX…), speaker names and chat handles, brand and
   product names (see the glossary's name list). Generic descriptors next to a name are
   translated ("Order System" → your language's word for it).
3. **Markup survives with the same count**: `*host*`, `_italic_`, `‗KEYWORD‗`, `#REGISTER`,
   `{profanity}`, `<PLACEHOLDER>`, `{0}`/`{1}`, escaped `\*` `\_` `\\*`, indentation, blank
   lines. Profanity goes *inside* braces (the game censors brace content when the profanity
   filter is on); nothing else may be in braces. `{0}` placeholders may be reordered.
4. **No ASCII double quote `"` inside dialogue.** Use your language's quotation marks.
   Typographic apostrophe ’. (Briefings in text-only mode keep the quoted English UI labels
   in ASCII quotes; see rule 9.)
5. **Never write `--`**: the game turns it into an em dash. Use – or — directly.
6. **UI keys are trimmed** by the game's CSV loader: a source string with leading/trailing
   spaces can never match; translate it anyway (it stays English in-game, the validator
   knows).
7. **Length and case**:
   - Player choices are buttons: short and punchy.
   - UI labels have fixed widths: short labels (≤ 20 chars) at most ~1.3× the English;
     prefer the shorter natural option. Tooltips and sentences may run ~30 % longer.
   - ALL CAPS stays ALL CAPS. English Title Case becomes your language's convention
     (German: normal noun capitalization; French: sentence case).
8. **Localize formats** in dialogue and UI: dates and times in your locale's format, money in
   your locale's notation, keyboard names as printed on your keyboards (German: Strg, Umschalt,
   Esc; French: Ctrl, Maj, Échap, Entrée). `Cmd` and function keys stay. **In briefings, all
   numbers must stay as digits identical to the English** (the validator compares them: puzzle
   data), so write e.g. "9 PM" as a 24-hour time only if the digits survive, otherwise keep it.
   Typography: follow your language's rules (French: space before `; : ! ?` and inside « » —
   use U+00A0 NO-BREAK SPACE; avoid U+202F, the game's fonts may lack it).
9. **UI labels quoted in briefings** (show-goal, test-run, select-opponent buttons): keep the
   English label in ASCII double quotes. In UI mode `tools/ui.py relabel` replaces them with
   your translated labels automatically, so both modes stay consistent.
10. **Gender**: Moss is never gendered (no gendered pronouns, articles, nouns, adjective
    endings; rephrase). This includes Moss's own first-person narration in languages where
    adjectives and participles agree with the speaker (French "je suis prêt/prête"): use
    epicene words or rephrase. Nivas is non-binary and gets **no pronoun**: repeat the name or
    restructure; same care with agreeing adjectives. Ghast is male, Isadora female; avoid
    pronouns for EMBER-2 (if your grammar forces a gender for "the AI", decide once in the
    glossary).
11. **Chat**: lowercase, sloppy punctuation, emoticons kept, typos reproduced with typos of
    your language (if a typo gets corrected later, keep the correction meaningful).
12. **Jokes and puns**: adapt so they work in your language; mention adaptations in your
    report.

## Batching (for the orchestrating agent)

- Dialogue: about 6 agents with ~10 vignette files each, grouped so an agent sees connected
  conversations (a numbered character series together, a puzzle with its chat rooms).
  Briefings: 2–3 agents. UI strings + WorkHouse: one agent (consistency matters more than
  speed). See SKILL.md §3 for deriving the campaign order and what each prompt must contain.
- Every agent gets this file + the glossary, writes its own `newterms-<agent>.md`, and must
  finish with a clean validator run.
- After each wave, merge the new-terms notes into the glossary (resolve conflicts: one
  rendering per term), then let later waves and the reviewers work from the updated ledger.

## Final report (translator's last message)

Files done, validator output, notable adaptations (puns, typos, cut lines), new terms. Short.
