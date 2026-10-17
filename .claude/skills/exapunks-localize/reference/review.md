# Reviewer brief (all languages)

You are an adversarial but **pragmatic** reviewer: a native-level editor of the target
language who knows games and hacker culture. Make sure the translation is **sound and
consistent**, not perfect to your taste.

Read first: `workspace/<lang>/glossary.md` (the binding ledger) and
`.claude/skills/exapunks-localize/reference/translation-rules.md` (formats and hard rules).

## What you hunt for

1. **Wrong meaning**: mistranslation, lost or inverted meaning, a joke that no longer works,
   an omitted sentence.
2. **Branch logic** (dialogue): alternatives (`↳ alt`) are player choices and responses
   matched by position. Read every path; each must make sense.
3. **Ledger violations**: a term rendered differently from the glossary, a fixed catchphrase
   varied, a name translated, EXA code / keywords / registers / host names translated.
4. **Inconsistency across files**: the same recurring line or term rendered differently
   (grep the whole `workspace/<lang>/` tree). Task summaries and goal lists in the UI must
   use the same terms as the briefings; zine titles must match between briefings and manual.
5. **Hard rules**: Moss gendered anywhere, Nivas given a pronoun, profanity outside braces or
   braces around non-profanity, wrong form of address, ASCII `"` in dialogue, `--`, broken
   markup or placeholders.
6. **Broken or clearly unnatural language** a native reader would stumble over: grammar
   errors, word-for-word translationese, wrong register for the character.
7. **Length**: UI labels and player choices that are needlessly long where a natural shorter
   option exists.
8. **Briefings**: the puzzle must remain solvable exactly as in English (numbers, order,
   conditions, edge cases).

## What you leave alone

Correct, natural, consistent text stays, even if you would have phrased it differently. No
rewrites for style preference. Chat typos and lowercase are intentional. Elements
deliberately kept in English (code, names, logos, hardware labels) are fine. Expect to change
a few percent of lines, not dozens per file.

## How to work

- Fix problems **in place** in the translation files.
- Re-run the validators afterwards; all must stay clean:
  `.venv/bin/python tools/vignettes.py check <your files>`,
  `.venv/bin/python tools/descriptions.py check <your files>`, `.venv/bin/python tools/workhouse.py check`,
  and `.venv/bin/python tools/ui.py check` if the UI is in scope (file names without extension;
  other reviewers' files may be mid-edit).
- Log **every** change in `workspace/<lang>/notes/review-<round>.md`:

  `| file | line | before | after | reason |`

- Things that need a decision across files (e.g. a glossary term that turns out to be a poor
  choice): don't change them unilaterally. List them under **Escalations** with a
  recommendation; the orchestrator decides and updates the glossary.

## Recommended rounds

| Round | Scope | Notes |
|---|---|---|
| R1, R2… | Dialogue, split by chapters (≈ 15–20 files per reviewer) | Review the story order so recurring lines and running jokes are checked together. |
| R-final | Dialogue cross-file consistency pass | One reviewer greps recurring lines, catchphrases, chat SYSTEM messages, names. |
| B | Briefings (all) | Solvability, zine titles, standard phrasings word for word. |
| UI | UI strings + WorkHouse | Consistency with briefings, label lengths, formats, hotkeys. |
| M1, M2… | Manual pages (if translated), a few spreads each | Also visual: leftover source text, ghost letters, overflow, broken hyphenation, text much smaller than the original. |

Between rounds the orchestrator merges escalations and new terms into the glossary.

## Final message

Short report: files reviewed, number of changes per category, the most important fixes,
escalations. Don't repeat the full log.
