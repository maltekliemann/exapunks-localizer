# Translating the manual (TRASH WORLD NEWS zines + epilogue)

**Optional and by far the most labour-intensive part** (in the German project: 45 spreads, several
translator agents plus reviewers, many render rounds per spread). Do dialogue, briefings and UI
first; the game is fully playable without a translated manual.

## What the manual is

`Content/manual/` holds 7 PDFs: `digital_en_1.pdf` / `digital_en_2.pdf` (two zine issues, 21
spreads each, read in-game and on screen), `letter_en_*.pdf` / `metric_en_*.pdf` (the same pages
imposed as printable booklets, US letter / A4) and `epilogue_en.pdf` (3 pages, unlocked at the end).
They are scans of a designed print magazine: text is pixels, not a text layer.

Approach: keep the scan (art, layout, screenshots, code listings, logos), **erase the English
text in place and typeset the translation on top as vector text** with a similar font. The
result should look as if the zine had been printed in the target language. Output keeps the
original file names (the game opens `*_en_*.pdf` regardless of language).

## Pipeline

All paths are in the git-ignored workspace (see `tools/manual/paths.py`). Requirements: the
Python packages from `requirements.txt` (PyMuPDF, OpenCV, pyphen, fontTools), poppler
(`pdftoppm`) and Tesseract with English data.

1. **Fonts**: `python tools/manual/fonts.py`: downloads ~30 open-licence families from
   google/fonts and writes ~70 static instances to `workspace/fonts/manual/static/`
   (MuPDF cannot use variable fonts, so every weight/style is its own file).
2. **Rasterise + OCR**: `python tools/manual/ocr.py`: 300 dpi page images in
   `workspace/source/manual/pages/` (`z1s-NN.png` spreads, 3500×2750 px, right page starts at
   x = 1750; `epi-N.png` single pages, 2750 wide) and Tesseract output per page half in
   `workspace/source/manual/ocr/`.
3. **Author one spec per spread**: `workspace/<lang>/manual/spec/<id>.json`, ids `z1-01`…`z1-21`,
   `z2-01`…`z2-21`, `epi-1`…`epi-3`. The spec lists regions: what to erase and what text to set
   where. Format: docstring at the top of `tools/manual/render.py`. The specs *are* your
   translation: never commit or share them.
4. **Render + inspect**: `python tools/manual/render.py z1-06` →
   `workspace/build/manual/work/z1-06.pdf`, a preview PNG, and `z1-06-compare.png`
   (original | translation). Fit warnings are printed when text shrank below 90 %.
   `python tools/manual/zoom.py z1-06 x y w h [--scale 0.5]` shows one area at full resolution,
   original above, translation below. Zoom into **every** region.
5. **Assemble**: `python tools/manual/build_manual.py` → the 7 PDFs in
   `workspace/build/manual/`. Spreads without a spec stay English. The booklet layouts are
   reproduced by template-matching each printed half page against the digital spreads (cached
   as `workspace/build/manual/mapping.json`, `--remap` to recompute) and placing the same area
   of the translated spread there as vector PDF.
6. **Install**: copy `workspace/build/manual/*.pdf` into the game's `Content/manual/` (the
   install tool does this). Originals stay in `workspace/backup/Content/manual/`.

Helpers: `python tools/manual/blocks.py z1s-06 [--lines]` lists OCR paragraphs (or single
lines) with `[x, y, w, h]` boxes in spread coordinates plus a font-size estimate;
`python tools/manual/dumptext.py z1-06` prints a spec's translated text for review.

## Spec format (short)

```json
{ "source": "pages/z1s-06.png",
  "regions": [
    { "id": "intro", "box": [x, y, w, h], "erase": "inpaint",
      "html": "Text with <b>, <i>, <br>, <p>, <code>…", "font": "body", "size": 44,
      "color": "#1a1a1a", "align": "justify", "valign": "top", "lh": 1.3 } ] }
```

- Coordinates and sizes are source pixels at 300 dpi. `box` is where the text goes;
  `erase_box` (one box or a list) defaults to `box`.
- `erase`: `inpaint` (default: removes only text-like pixels; raise `"k"` for big glyphs),
  `fill` (flat fill with the surrounding colour) or `fill:#rrggbb`, `copy:dx,dy` (patch from
  an offset area of the untouched scan), `none` (add text only). `erase_ocr: [x,y,w,h]` erases
  exactly the OCR lines centred in that area (padded by `"pad"`), the best choice for ragged
  text next to artwork.
- A region with `"html": ""` only erases. `rotate` 90/270 for vertical text; `angle` for one
  line at any angle; `hyphenate: false` to switch off automatic soft hyphens.
- `font`: a preset (`body`, `label`, `mono`, `sans`, `cond`, `type`, `typewriter`, `techno`,
  `pixel`, `hand`, `display`, `bebas`, …; full list in `render.py`) or a family name.
  `"css"` is injected into the region's `* { … }` rule; it may close the rule and declare an
  extra `@font-face` pointing at any file in the static font folder.
- Inline classes: `<span class="inv">` (white-on-black run-in label), `<span class="twn">`
  (end-of-article mark), `<code>` (monospace).

## Lessons from the German edition

- **Match the original's line pitch**, not just the font size: measure it with
  `blocks.py --lines`. Zine body text ≈ `body` (Crimson Pro) at ~44 px, `lh` 1.25–1.33.
- Translations run ~30 % longer than English. Shrinking to ≥ 90 % is fine; beyond that enlarge
  the box into empty space, tighten the wording, or reduce `lh` a little. Body text below ~80 %
  of the original size looks wrong.
- **PyMuPDF `insert_htmlbox`** does the typesetting and the shrink-to-fit (render.py measures
  on a scratch page first so it can align vertically). MuPDF ignores `letter-spacing`.
- **Soft hyphens** (pyphen, per workspace language) make justified columns look right; switch
  them off for hand-broken lines around artwork (explicit `<br>` + `"hyphenate": false`).
- **Halftone backgrounds** smear with inpaint/fill. Use `copy:dx,dy` with an offset that is a
  multiple of the halftone period (e.g. one period up), so the pattern continues seamlessly.
- Big bold headings: `fill` or inpaint with a large `k` (e.g. 151). Check zooms for ghost
  remnants, missing diacritics (umlauts, accents on capitals) and damaged art.
- Long flowing text across many regions or spreads (a short story, multi-column articles):
  keep the text in one file and write a tiny generator that splits it into the spec regions,
  instead of hand-editing dozens of regions.
- Elaborate artwork titles (3D, textured, overlapping art) that can't be replaced cleanly can
  stay English; translate them in the table of contents and running text instead.
- Keep untranslated: EXA code and instruction names, screenshots, brand names and logos, page
  numbers, handles. Article titles must match how the in-game briefings refer to them: put
  them in the glossary and use them verbatim (heading and table of contents).
- Workflow per spread: list every English element → translate from the scan (OCR has errors) →
  write the spec → render → inspect compare image + zooms → fix → repeat (3–6 rounds is normal).
- Parallelise across agents by spread ranges; each agent touches only its own spec ids and logs
  new terms for the glossary. Then run a **reviewer pass** per spread range: translation
  soundness against the scan, glossary consistency, visual quality (leftover English, ghosts,
  overlaps, overflow). Reviewers fix only real problems, no stylistic nitpicking.
