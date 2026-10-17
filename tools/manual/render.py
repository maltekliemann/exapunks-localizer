#!/usr/bin/env python3
"""Render a translated zine page from a spec: erase the English text in the scan, typeset the translation on top.

Usage:  python tools/manual/render.py <spec-id> [<spec-id> ...]     e.g. z1-05  epi-2
Reads   workspace/<lang>/manual/spec/<id>.json
Writes  workspace/build/manual/work/<id>.pdf          vector text over the cleaned 300dpi scan
        workspace/build/manual/work/<id>.png          preview (~1000px wide)
        workspace/build/manual/work/<id>-compare.png  original | translation, side by side
Prints  a fit report: any region whose text had to shrink below 90% of its requested size.

Spec format (coordinates/sizes in source-image pixels, 300 dpi):
{
  "source": "pages/z1s-05.png",    # relative to workspace/source/manual/
  "regions": [
    {
      "id": "intro",
      "box": [x, y, w, h],          # where the translated text goes
      "erase": "inpaint",           # inpaint (default) | fill | fill:#rrggbb (or #rgb) | copy:dx,dy | none
                                    # copy:dx,dy patches the area with original pixels from (x+dx, y+dy),
                                    # e.g. to continue a periodic halftone pattern
      "erase_box": [x, y, w, h],    # optional; area to clean (defaults to box). May also be a list of boxes.
      "erase_ocr": [x, y, w, h],    # optional; instead erase each OCR text line (see blocks.py --lines) centred
                                    # in this area, padded by "pad" px (default 8). Best for ragged text near art.
      "k": 41,                      # optional; inpaint background window (raise for big/bold glyphs)
      "html": "translated text; <b>, <i>, <u>, <br>, <p>, <span class=…> allowed",
      "font": "body",               # preset (see PRESETS) or any CSS font-family
      "size": 40, "color": "#1a1a1a", "align": "left", "valign": "top",
      "lh": 1.3, "weight": 400, "css": "letter-spacing: 2px;",  # optional extras
      "rotate": 90,                 # optional; 90 = text reads bottom-to-top, 270 = top-to-bottom
      "angle": 30                   # optional; one line of text rotated by any angle (counter-clockwise),
                                    # box[0:2] = start of its baseline, w/h unused (no wrapping/shrinking)
    }
  ]
}
A region with "html": "" only erases. A region with "erase": "none" only adds text.
The "css" value is injected into the region's `* { … }` rule. It may close that rule and add more,
e.g. `} @font-face { font-family: 'X'; src: url(Roboto-900i.ttf); } div { font-family: 'X';`
to use any static font file from workspace/fonts/manual/static/ (see tools/manual/fonts.py).
"""
import json, re, sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths as P  # noqa: E402

DPI = P.DPI
FONT_DIR = P.FONTS
# family -> {(bold, italic): file}. MuPDF cannot use variable fonts, so these are static instances.
def _fam(prefix, light=False):
    return {(False, False): f"{prefix}-400.ttf", (True, False): f"{prefix}-700.ttf",
            (False, True): f"{prefix}-400i.ttf", (True, True): f"{prefix}-700i.ttf"}
FONTS = {
    "Crimson Pro": _fam("CrimsonPro"), "EB Garamond": _fam("EBGaramond"),
    "Libre Baskerville": _fam("LibreBaskerville"), "Roboto": _fam("Roboto"),
    "Crimson Pro Light": {(False, False): "CrimsonPro-300.ttf", (False, True): "CrimsonPro-300i.ttf",
                          (True, False): "CrimsonPro-700.ttf", (True, True): "CrimsonPro-700i.ttf"},
    "Roboto Light": {(False, False): "Roboto-300.ttf", (False, True): "Roboto-300i.ttf"},
    "Roboto Black": {(False, False): "Roboto-900.ttf", (False, True): "Roboto-900i.ttf"},
    "Montserrat Black": {(False, False): "Montserrat-900.ttf"},
    "Archivo Heavy": {(False, False): "Archivo-900.ttf"},
}
for fam, pre in [("Roboto Condensed", "RobotoCondensed"), ("Archivo", "Archivo"), ("Montserrat", "Montserrat"),
                 ("Noto Sans Mono", "NotoSansMono"), ("Orbitron", "Orbitron"), ("Oswald", "Oswald"),
                 ("Dosis", "Dosis"), ("Caveat", "Caveat"), ("Cinzel", "Cinzel"), ("Pixelify Sans", "PixelifySans")]:
    FONTS[fam] = {(False, False): f"{pre}-400.ttf", (True, False): f"{pre}-700.ttf"}
for fam, f in [("Archivo Black", "ArchivoBlack-Regular"), ("Michroma", "Michroma-Regular"),
               ("Audiowide", "Audiowide-Regular"), ("Special Elite", "SpecialElite-Regular"),
               ("VT323", "VT323-Regular"), ("Silkscreen", "Silkscreen-Regular"),
               ("Permanent Marker", "PermanentMarker-Regular"), ("Share Tech Mono", "ShareTechMono-Regular"),
               ("Bebas Neue", "BebasNeue-Regular"), ("Anton", "Anton-Regular"), ("Rubik Mono One", "RubikMonoOne-Regular")]:
    FONTS[fam] = {(False, False): f + ".ttf"}
FONTS["Oswald Light"] = {(False, False): "Oswald-300.ttf", (True, False): "Oswald-400.ttf"}
FONTS["Roboto Condensed Light"] = {(False, False): "RobotoCondensed-300.ttf", (True, False): "RobotoCondensed-400.ttf"}
FONTS["Courier Prime"] = {(False, False): "CourierPrime-Regular.ttf", (True, False): "CourierPrime-Bold.ttf"}
PRESETS = {  # shorthand -> family
    "body": "Crimson Pro", "bodylight": "Crimson Pro Light", "serif": "Libre Baskerville", "garamond": "EB Garamond",
    "sans": "Roboto", "sanslight": "Roboto Light", "sansblack": "Roboto Black", "cond": "Roboto Condensed",
    "label": "Archivo Black", "archivo": "Archivo", "mono": "Noto Sans Mono", "type": "Courier Prime",
    "typewriter": "Special Elite", "techno": "Michroma", "orbitron": "Orbitron", "pixel": "VT323",
    "pixel2": "Silkscreen", "marker": "Permanent Marker", "hand": "Caveat", "display": "Anton", "bebas": "Bebas Neue",
}
PT = 72 / DPI  # source pixel -> PDF point


def box_of(b):
    x, y, w, h = [int(round(v)) for v in b]
    return x, y, w, h


def ocr_lines(source):
    """OCR line boxes (spread coordinates) for a page image like pages/z1s-05.png."""
    from blocks import paras
    stem = Path(source).stem
    parts = [(P.OCR / f"{stem}.tsv", 0)] if stem.startswith("epi") else \
        [(P.OCR / f"{stem}_0.tsv", 0), (P.OCR / f"{stem}_1.tsv", P.HALF)]
    out = []
    for tsv, dx in parts:
        if tsv.exists():
            out += [(x, y, w, h) for y, x, w, h, _, _ in paras(tsv, dx, lines=True)]
    return out


_ORIG = None  # untouched scan, set by render() for "copy:" erases


def erase(img, region, source=None):
    mode = region.get("erase", "inpaint")
    if mode == "none":
        return
    if "erase_ocr" in region:  # erase every OCR text line whose centre lies inside this area (padded)
        ax, ay, aw, ah = box_of(region["erase_ocr"])
        pad = int(region.get("pad", 8))
        boxes = [[x - pad, y - pad, w + 2 * pad, h + 2 * pad] for x, y, w, h in ocr_lines(source)
                 if ax <= x + w / 2 <= ax + aw and ay <= y + h / 2 <= ay + ah]
        boxes += region.get("erase_box", []) if region.get("erase_box") and not isinstance(region["erase_box"][0], (int, float)) else ([region["erase_box"]] if region.get("erase_box") else [])
    else:
        boxes = region.get("erase_box", region["box"])
    if boxes and isinstance(boxes[0], (int, float)):
        boxes = [boxes]
    H, W = img.shape[:2]
    for b in boxes:
        x, y, w, h = box_of(b)
        x0, y0, x1, y1 = max(0, x), max(0, y), min(W, x + w), min(H, y + h)
        if x1 <= x0 or y1 <= y0:
            continue
        if mode.startswith("copy:"):  # patch from an offset area of the ORIGINAL scan (e.g. periodic halftone)
            dx, dy = (int(v) for v in mode.split(":", 1)[1].split(","))  # offsets may be negative
            src = _ORIG if _ORIG is not None else img
            # clip so the source area stays inside the image (no wrap-around for negative indices)
            cx0, cy0 = max(x0, -dx), max(y0, -dy)
            cx1, cy1 = min(x1, W - dx), min(y1, H - dy)
            if cx1 > cx0 and cy1 > cy0:
                img[cy0:cy1, cx0:cx1] = src[cy0 + dy:cy1 + dy, cx0 + dx:cx1 + dx]
            continue
        if mode.startswith("fill"):
            if ":" in mode:
                c = mode.split(":", 1)[1].lstrip("#")
                if len(c) == 3:  # #rgb shorthand
                    c = "".join(ch * 2 for ch in c)
                col = np.array([int(c[4:6], 16), int(c[2:4], 16), int(c[0:2], 16)], np.uint8)  # BGR
            else:  # median colour of a thin ring just outside the box
                r = 6
                ring = np.concatenate([
                    img[max(0, y0 - r):y0, x0:x1].reshape(-1, 3), img[y1:min(H, y1 + r), x0:x1].reshape(-1, 3),
                    img[y0:y1, max(0, x0 - r):x0].reshape(-1, 3), img[y0:y1, x1:min(W, x1 + r)].reshape(-1, 3)])
                col = np.median(ring, axis=0).astype(np.uint8) if len(ring) else np.array([255, 255, 255], np.uint8)
            img[y0:y1, x0:x1] = col
        else:  # inpaint: mask = pixels that differ from a large-window median background
            k = int(region.get("k", 41)) | 1
            m = k
            cx0, cy0, cx1, cy1 = max(0, x0 - m), max(0, y0 - m), min(W, x1 + m), min(H, y1 + m)
            crop = img[cy0:cy1, cx0:cx1].copy()
            bg = cv2.medianBlur(crop, k)
            diff = np.abs(crop.astype(np.int16) - bg.astype(np.int16)).max(axis=2)
            mask = (diff > int(region.get("thresh", 30))).astype(np.uint8) * 255
            keep = np.zeros_like(mask)
            keep[y0 - cy0:y1 - cy0, x0 - cx0:x1 - cx0] = 255
            mask &= keep
            mask = cv2.dilate(mask, np.ones((3, 3), np.uint8), iterations=2) & keep
            out = cv2.inpaint(crop, mask, 4, cv2.INPAINT_TELEA)
            img[y0:y1, x0:x1] = out[y0 - cy0:y1 - cy0, x0 - cx0:x1 - cx0]


def font_css():
    css = []
    for fam, files in FONTS.items():
        for (bold, ital), f in files.items():
            css.append(f"@font-face {{font-family: '{fam}'; src: url({f}); "
                       f"font-weight: {'bold' if bold else 'normal'}; font-style: {'italic' if ital else 'normal'};}}")
    return "\n".join(css)


BASE_CSS = """
p { margin: 0 0 0.5em 0; } p:last-child { margin-bottom: 0; }
.ind { text-indent: 1.4em; }
code, .code { font-family: 'Noto Sans Mono'; font-size: 0.86em; }
.inv { background-color: #111; color: #fff; font-family: 'Archivo Black'; font-size: 0.85em; }
.twn { background-color: #111; color: #fff; font-family: 'Archivo Black'; font-size: 0.5em; }
ul { margin: 0 0 0.5em 0; padding-left: 1.2em; }
"""


def region_css(r, size_px):
    fam = PRESETS.get(r.get("font", "body"), r.get("font", "body"))
    w = r.get("weight", 400)
    return (f"* {{ font-family: '{fam}'; font-size: {size_px * PT:.2f}px; color: {r.get('color', '#1a1a1a')}; "
            f"text-align: {r.get('align', 'left')}; line-height: {r.get('lh', 1.3)}; "
            f"font-weight: {'bold' if (w if isinstance(w, int) else 400) >= 600 or w == 'bold' else 'normal'}; "
            f"{r.get('css', '')} }}\n{BASE_CSS}")


_DIC = None


HYPH_LANG = {"de": "de_DE", "fr": "fr_FR", "ru": "ru_RU"}


def hyphenate(html):
    """Insert soft hyphens into long words (outside tags and <code>), so justified text breaks nicely.
    Uses the workspace language's pyphen dictionary; no-op for languages without one (zh, ja)."""
    global _DIC
    import pyphen
    lang = HYPH_LANG.get(P.common.lang())
    if not lang:
        return html
    _DIC = _DIC or pyphen.Pyphen(lang=lang)
    out, in_code = [], 0
    for part in re.split(r"(<[^>]+>)", html):
        if part.startswith("<"):
            if re.match(r"<code|<span[^>]*class=\"[^\"]*code", part):
                in_code += 1
            elif part.startswith("</code") or (part.startswith("</span") and in_code):
                in_code = max(0, in_code - 1)
            out.append(part)
        elif in_code:
            out.append(part)
        else:
            out.append(re.sub(r"(?<![-\w])[^\W\d_]{8,}(?![-\w])",
                              lambda m: _DIC.inserted(m.group(0), hyphen="\u00ad"), part))
    return "".join(out)


def place_text(page, r, arch, faces, dry=None):
    """Insert region text, shrinking to fit; returns achieved scale (or -1 if it never fits)."""
    import pymupdf
    if "angle" in r:  # single line at an arbitrary angle: box[0:2] = start of the baseline, w/h unused
        import html as _h
        fam = PRESETS.get(r.get("font", "body"), r.get("font", "body"))
        c = r.get("color", "#1a1a1a").lstrip("#")
        c = "".join(ch * 2 for ch in c) if len(c) == 3 else c
        p = pymupdf.Point(r["box"][0] * PT, r["box"][1] * PT)
        page.insert_text(p, _h.unescape(re.sub(r"<[^>]+>", "", r["html"])), fontsize=r.get("size", 40) * PT,
                         fontfile=str(FONT_DIR / FONTS[fam][(False, False)]), fontname=f"ang{abs(hash(fam)) % 10**6}",
                         color=tuple(int(c[i:i + 2], 16) / 255 for i in (0, 2, 4)),
                         morph=(p, pymupdf.Matrix(r["angle"])))
        return 1.0
    x, y, w, h = box_of(r["box"])
    rect = pymupdf.Rect(x * PT, y * PT, (x + w) * PT, (y + h) * PT)
    size = r.get("size", 40)
    body = r["html"] if r.get("hyphenate") is False else hyphenate(r["html"])
    html = f"<div>{body}</div>"
    css = faces + "\n" + region_css(r, size)
    # measure on a scratch page first so we can vertically align
    tmp = pymupdf.open()
    tp = tmp.new_page(width=page.rect.width, height=page.rect.height)
    rot = int(r.get("rotate", 0)) % 360  # optional: 90 = reads bottom-to-top, 270 = top-to-bottom
    spare, scale = tp.insert_htmlbox(rect, html, css=css, archive=arch, scale_low=0.4, rotate=rot)
    if spare < 0:
        return -1
    va = r.get("valign", "top")
    used = rect.height - spare / scale if scale else rect.height
    # spare is reported in the scaled coordinate system; recompute by re-measuring at fixed scale
    css2 = faces + "\n" + region_css(r, size * scale)
    tp2 = tmp.new_page(width=page.rect.width, height=page.rect.height)
    spare2, _ = tp2.insert_htmlbox(rect, html, css=css2, archive=arch, scale_low=1, rotate=rot)
    shift = 0 if va == "top" else (spare2 / 2 if va == "middle" else spare2)
    if spare2 < 0:  # rounding: fall back to auto-scaled insert
        page.insert_htmlbox(rect, html, css=css, archive=arch, scale_low=0.4, rotate=rot)
        return scale
    d = {0: (0, shift), 90: (shift, 0), 180: (0, -shift), 270: (-shift, 0)}.get(rot, (0, shift))
    page.insert_htmlbox(rect + (d[0], d[1], d[0], d[1]), html, css=css2, archive=arch, scale_low=1, rotate=rot)
    return scale


def render(sid):
    import pymupdf
    spec = json.loads(P.spec_path(sid).read_text(encoding="utf-8"))
    src = P.source_image(spec)
    img = cv2.imread(str(src))
    H, W = img.shape[:2]
    global _ORIG
    _ORIG = img.copy()
    for r in spec["regions"]:
        erase(img, r, spec["source"])
    out = P.WORK
    (out / "bg").mkdir(parents=True, exist_ok=True)
    bg = out / "bg" / f"{sid}.jpg"
    cv2.imwrite(str(bg), img, [cv2.IMWRITE_JPEG_QUALITY, 88])
    doc = pymupdf.open()
    page = doc.new_page(width=W * PT, height=H * PT)
    page.insert_image(page.rect, filename=str(bg))
    arch = pymupdf.Archive(str(FONT_DIR))
    faces = font_css()
    warn = []
    for r in spec["regions"]:
        if not r.get("html"):
            continue
        sc = place_text(page, r, arch, faces)
        if sc < 0:
            warn.append(f"{r.get('id')}: DOES NOT FIT even at 40% — enlarge the box or shorten the text")
        elif sc < 0.9:
            warn.append(f"{r.get('id')}: shrunk to {sc:.0%} of requested size ({r.get('size', 40) * sc:.0f}px)")
    pdf = out / f"{sid}.pdf"
    doc.save(str(pdf), garbage=3, deflate=True)
    pix = page.get_pixmap(dpi=int(1000 / (W / DPI)))
    pix.save(str(out / f"{sid}.png"))
    g = cv2.imread(str(out / f"{sid}.png"))
    o = cv2.resize(cv2.imread(str(src)), (g.shape[1], g.shape[0]), interpolation=cv2.INTER_AREA)
    cv2.imwrite(str(out / f"{sid}-compare.png"), np.hstack([o, np.full((g.shape[0], 12, 3), 255, np.uint8), g]))
    print(f"{sid}: ok -> {out}/{sid}.pdf, {sid}.png, {sid}-compare.png")
    for w_ in warn:
        print("  fit:", w_)


if __name__ == "__main__":
    for sid in sys.argv[1:]:
        render(sid)
