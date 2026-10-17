# How EXAPUNKS stores its text

Findings from analysing the GOG macOS build (game version of 2018/2019). Other builds
(Steam, Windows, Linux) use the same engine and file layout; the tools locate code by its
structure rather than by fixed addresses, so they should carry over, but verify.

## Where things are

The game folder (macOS: `EXAPUNKS.app/Contents/MacOS/`) contains `EXAPUNKS.exe` (a .NET
assembly run by a bundled Mono, rendering via FNA), `Content/` and `PackedContent/`.

| Text | File(s) | Format | Tool |
|---|---|---|---|
| Dialogue / cutscenes / chat | `Content/vignettes/*.csv` | hand-edited CSV: speaker, English, French, Chinese, Japanese columns; `SECTION-…`/`ACTION-…` structure lines | `tools/vignettes.py` |
| Puzzle briefings | `Content/descriptions/en/*.txt` | plain text with light markup (`*host*`, `_italic_`, `‗KEYWORD‗`) | `tools/descriptions.py` |
| UI (menus, task list, editor, errors) | string literals inside `EXAPUNKS.exe`, translated via `Content/strings.csv` | see below | `tools/ui.py`, optional `extraction/` |
| WorkHouse minigame | `PackedContent/textures/workhouse/*.tex` and half-size copies in `PackedContent/half/textures/workhouse/` (used at low texture quality) | text painted into textures | `tools/workhouse.py` |
| Other baked labels | `PackedContent/textures/**/*.tex` | textures | `tools/tex.py` |
| Manual | `Content/manual/*.pdf` | scanned zines (300 dpi images) | `tools/manual/` |
| Settings | per-user `config.cfg` (macOS: `~/Library/Application Support/EXAPUNKS/<user>/`) | `Key = Value` lines, incl. `Language = English` | `tools/install.py` |

## The built-in localization system

- `enum Language { Pseudo=0, English=1, German=2, French=3, Russian=4, Chinese=5, Japanese=6 }`;
  `config.cfg` accepts the names (`Language = German`). The options screen of the analysed
  build has no language setting (none among its strings); the config line works.
- UI code calls a lookup `L(text, context)` (≈590 call sites) that returns a `LocString`
  (a `Dictionary<Language,string>`). Lookups are keyed by (English text, context) in a table
  loaded from `Content/strings.csv`. Missing keys fall back to the English text.
- `strings.csv` parser: rows split on `\n`; fields split on commas outside `"…"`; `""` is a
  literal quote; **every field is trimmed**; a literal backslash-n in a cell becomes a newline.
  Columns: `0 English key | 1 context | 2 German | 3 French | 4 Russian | 5 Chinese | 6 Japanese`.
  Consequence: a key with leading/trailing spaces can never match (one such string exists).
- When displaying, the game replaces `--` with an em dash and `……` with `…`.

### Why the exe needs a patch

The `LocString` display getter returns `dict[currentLanguage]` with no fallback. That breaks
two content loaders as soon as the language isn't English:

- The briefing loader fills every language with the placeholder `[!!! MISSING !!!]` and then
  loads only `descriptions/en/` → briefings show the placeholder.
- The dialogue parser fills English, French, Chinese and Japanese from the CSV columns (empty
  in the shipped files), never German or Russian → missing-key crash for German/Russian, empty
  dialogue for French/Chinese/Japanese.

`tools/patch/Patch.cs` (Mono.Cecil) rewrites that one getter to:
`if (dict.TryGetValue(lang, out s) && !string.IsNullOrEmpty(s) && !s.StartsWith("[!!! MISSING", Ordinal)) return s; return dict[English];`
It finds the getter by shape (instance, returns string, no parameters, 5 IL instructions that
read a static field of type `Language`). With the patch, the translation can simply be written
into the **English** slots of the content files (dialogue column 2, `descriptions/en/`), while
`strings.csv` supplies the UI in the selected language. The patched exe was checked to decrypt
its strings identically (no tamper check).

## Text-only vs full mode

- **text**: translated dialogue and briefings in the English slots, WorkHouse textures; original
  exe; language stays English. Menus stay English.
- **full**: additionally the patched exe, translated `strings.csv` and `Language = <yours>`. Briefings that quote button labels get the translated labels
  (`ui.py relabel`).

## Textures (`.tex`)

60-byte header: int32 version (1002), int32 width, int32 height, …, int32 at offset 56 =
compressed length; then an LZ4 block of **premultiplied** RGBA8 pixels, rows stored bottom-up.
`tools/tex.py decode|encode` flips rows on the way; re-encoding is lossless. Composite text
with premultiplied "over" (`tools/workhouse.py` does), or transparent edges get halos.

## Not translatable (and shouldn't be)

EXA instructions, registers, keyword values, host names and file contents in puzzles are game
data; changing them breaks puzzles or contradicts the briefings. The WorkHouse receipt is an
answer key checked against what the player types. A handful of labels are hardcoded strings
that bypass `L()` (e.g. some status panels in puzzle networks); they stay English unless you
patch them individually.

## Quirks worth knowing

- Vignette CSVs are inconsistent (quoted/unquoted fields, missing closing quotes, mixed BOM and
  line endings). `vignettes.py` never re-serializes a line; it swaps only the text between the
  original prefix and suffix, so untouched bytes stay identical.
- Text in `{braces}` in dialogue is profanity the game can censor (`FilterProfanity`).
- Dialogue choices are short buttons; long translations clip.
- Some dialogue lines contain `<PLACEHOLDER>` tokens filled by the game (key combos etc.).
