#!/usr/bin/env python3
"""Close-up check: crop the same area from the original scan and the rendered translated page.

Usage: python tools/manual/zoom.py <spec-id> x y w h [--scale 0.5]
Writes workspace/build/manual/work/<spec-id>-zoom.png (original on top, translation below),
coordinates in source pixels (300 dpi).
"""
import json, sys
from pathlib import Path

import cv2
import numpy as np
import pymupdf

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths as P  # noqa: E402

sid = sys.argv[1]
x, y, w, h = map(int, sys.argv[2:6])
scale = float(sys.argv[sys.argv.index("--scale") + 1]) if "--scale" in sys.argv else 0.5
spec = json.loads(P.spec_path(sid).read_text(encoding="utf-8"))
orig = cv2.imread(str(P.source_image(spec)))[y:y + h, x:x + w]
doc = pymupdf.open(str(P.WORK / f"{sid}.pdf"))
k = 72 / 300
pix = doc[0].get_pixmap(dpi=300, clip=pymupdf.Rect(x * k, y * k, (x + w) * k, (y + h) * k))
tr = cv2.imdecode(np.frombuffer(pix.tobytes("png"), np.uint8), cv2.IMREAD_COLOR)
tr = cv2.resize(tr, (orig.shape[1], orig.shape[0]))
both = np.vstack([orig, np.full((10, orig.shape[1], 3), (0, 0, 255), np.uint8), tr])
both = cv2.resize(both, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
out = P.WORK / f"{sid}-zoom.png"
cv2.imwrite(str(out), both)
print(out)
