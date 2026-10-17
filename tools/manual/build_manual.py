#!/usr/bin/env python3
"""Assemble the translated manual PDFs from the rendered spreads.

  digital_en_{1,2}.pdf   reading-order spreads: work/z{i}-{nn}.pdf, or the original page if not translated
  letter_en_{1,2}.pdf    booklet imposition (US letter), derived from the translated spreads
  metric_en_{1,2}.pdf    booklet imposition (A4), derived from the translated spreads
  epilogue_en.pdf        work/epi-{1,2,3}.pdf (original page where missing)

The print layouts are reproduced exactly: each print page half is located in the original digital
spreads by template matching (computed once, cached in workspace/build/manual/mapping.json; pass
--remap to recompute) and the same region of the translated spread is placed there as vector PDF.
Halves that match nothing (blank pages) keep the original.
The output keeps the original file names (the game opens *_en_*.pdf whatever the language).
Output: workspace/build/manual/   Install: copy those PDFs into the game's Content/manual/.

Usage: python tools/manual/build_manual.py [--remap]
"""
import json, sys
from pathlib import Path

import cv2
import numpy as np
import pymupdf

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths as P  # noqa: E402

ORIG = P.ORIG
OUT = P.OUT
MAP = OUT / "mapping.json"
Z = 0.2  # matching resolution relative to 300 dpi


def gray(doc, pno, px_per_pt):
    pix = doc[pno].get_pixmap(matrix=pymupdf.Matrix(px_per_pt, px_per_pt), colorspace=pymupdf.csGRAY, alpha=False)
    return np.frombuffer(pix.samples, np.uint8).reshape(pix.h, pix.w)


def find_mapping():
    """For every print page half: which digital spread, which source rect, which target rect (in points)."""
    mapping = {}
    for issue in (1, 2):
        dig = pymupdf.open(ORIG / f"digital_en_{issue}.pdf")
        k = 300 / 72 * Z
        spreads = [gray(dig, i, k) for i in range(len(dig))]
        for fmt in ("letter", "metric"):
            pr = pymupdf.open(ORIG / f"{fmt}_en_{issue}.pdf")
            pages = []
            for p in range(len(pr)):
                page = pr[p]
                img = gray(pr, p, k)
                h, w = img.shape
                halves = []
                for side, x0 in (("L", 0), ("R", w // 2)):
                    half = img[:, x0:x0 + w // 2]
                    best = None
                    if half.std() > 8:  # not blank
                        # content scale: print page height vs digital page area height (2550 px of 2750)
                        s = (page.rect.height / (2550 / 300 * 72))
                        # search: crop centre of the half, rescale to digital scale, match in each spread
                        ch, cw = half.shape
                        core = half[int(ch * .08):int(ch * .92), int(cw * .12):int(cw * .88)]
                        core = cv2.resize(core, None, fx=1 / s, fy=1 / s, interpolation=cv2.INTER_AREA)
                        for si, D in enumerate(spreads):
                            r = cv2.matchTemplate(D, core, cv2.TM_CCOEFF_NORMED)
                            _, mx, _, loc = cv2.minMaxLoc(r)
                            if best is None or mx > best[0]:
                                best = (mx, si, loc)
                    if best and best[0] > 0.8:
                        mx, si, loc = best
                        # core's top-left in print half (pt) and in spread (pt)
                        core_x_pr = (x0 + int(cw * .12)) / k
                        core_y_pr = int(ch * .08) / k
                        sx, sy = loc[0] / k, loc[1] / k
                        # translate: spread point -> print point:  print = (spread - (sx,sy)) * s + (core_x_pr, core_y_pr)
                        half_rect_pr = pymupdf.Rect(x0 / k, 0, (x0 + w // 2) / k, page.rect.height)
                        src = pymupdf.Rect((half_rect_pr.x0 - core_x_pr) / s + sx, (0 - core_y_pr) / s + sy,
                                           (half_rect_pr.x1 - core_x_pr) / s + sx, (page.rect.height - core_y_pr) / s + sy)
                        halves.append({"side": side, "spread": si + 1, "score": round(mx, 3),
                                       "src": [round(v, 2) for v in src], "dst": [round(v, 2) for v in half_rect_pr]})
                    else:
                        halves.append({"side": side, "spread": None})
                pages.append(halves)
                print(f"issue {issue} {fmt} p{p + 1}: " + ", ".join(
                    f"{h['side']}<-{h['spread']}" + (f"({h['score']})" if h['spread'] else "") for h in halves))
            mapping[f"{fmt}_{issue}"] = pages
    MAP.parent.mkdir(parents=True, exist_ok=True)
    MAP.write_text(json.dumps(mapping, indent=1), encoding="utf-8")
    return mapping


def build_digital(issue):
    orig = pymupdf.open(ORIG / f"digital_en_{issue}.pdf")
    out = pymupdf.open()
    done = 0
    for i in range(len(orig)):
        f = P.WORK / f"z{issue}-{i + 1:02d}.pdf"
        if f.exists():
            out.insert_pdf(pymupdf.open(f))
            done += 1
        else:
            out.insert_pdf(orig, from_page=i, to_page=i)
    print(f"digital_en_{issue}: {done}/{len(orig)} spreads translated")
    return out


def build_print(fmt, issue, digital, mapping):
    orig = pymupdf.open(ORIG / f"{fmt}_en_{issue}.pdf")
    out = pymupdf.open()
    for p, halves in enumerate(mapping[f"{fmt}_{issue}"]):
        r = orig[p].rect
        page = out.new_page(width=r.width, height=r.height)
        if any(h["spread"] is None for h in halves):
            page.show_pdf_page(r, orig, p)  # keep blank/unmatched halves as they were
        for h in halves:
            if h["spread"] is None:
                continue
            dst = pymupdf.Rect(h["dst"])
            src = pymupdf.Rect(h["src"])
            page.show_pdf_page(dst, digital, h["spread"] - 1, clip=src, keep_proportion=False)
    return out


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    mapping = json.loads(MAP.read_text(encoding="utf-8")) if MAP.exists() and "--remap" not in sys.argv else find_mapping()
    for issue in (1, 2):
        dig = build_digital(issue)
        dig.save(OUT / f"digital_en_{issue}.pdf", garbage=3, deflate=True)
        dig = pymupdf.open(OUT / f"digital_en_{issue}.pdf")
        for fmt in ("letter", "metric"):
            pr = build_print(fmt, issue, dig, mapping)
            pr.save(OUT / f"{fmt}_en_{issue}.pdf", garbage=3, deflate=True)
    epi = pymupdf.open()
    orig = pymupdf.open(ORIG / "epilogue_en.pdf")
    for i in range(len(orig)):
        f = P.WORK / f"epi-{i + 1}.pdf"
        epi.insert_pdf(pymupdf.open(f) if f.exists() else orig, from_page=0 if f.exists() else i,
                       to_page=0 if f.exists() else i)
    epi.save(OUT / "epilogue_en.pdf", garbage=3, deflate=True)
    for f in sorted(OUT.glob("*.pdf")):
        print(f"{f.name}: {f.stat().st_size / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
