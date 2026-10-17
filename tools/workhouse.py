#!/usr/bin/env python3
"""WorkHouse screen: redraw the English text baked into textures/workhouse/*.tex.

The WorkHouse "job" minigame draws almost all of its text from images (panels, column headers,
buttons, pop-up messages), so strings.csv can't translate it. This tool erases the English from
the original textures and typesets your translation with matching open fonts.

  extract -> workspace/source/workhouse/<key>.png  (crop of the English text for each key) and
             workspace/<lang>/workhouse.json        (template: keys + notes, empty values; only if missing)
  check   -> all keys translated, line limits, every character available in the fonts
  check   -> all keys translated, line limits, every character available in the fonts, and a
             full trial layout: fails if any text overflows its area (too wide even at the
             smallest allowed size, more lines than allowed, or running into the next element)
  build   -> workspace/build/textures/workhouse/*.tex, the half-resolution set the game uses at
             lower quality settings (workspace/build/half/textures/workhouse/*.tex), and
             before/after previews in workspace/build/workhouse-preview/ (look at them!)

Pixels are premultiplied RGBA (FNA); text is composited with premultiplied "over", so the same
code works for opaque panels and for the transparent message textures. Buttons are "engraved":
the glyphs darken the button by the same ratio as the original lettering.
The receipt itself stays English: it is an in-world document and the game checks what the player
types against a fixed answer key. Fonts cover Latin (and partly Cyrillic) scripts only.
Geometry was measured on the GOG macOS build; the previews show at once if another build differs.
"""
import json
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

import common
import fonts
import tex

ORIG = common.backup() / "PackedContent/textures/workhouse"
HALF_ORIG = common.backup() / "PackedContent/half/textures/workhouse"
OUT = common.build() / "textures/workhouse"
HALF_OUT = common.build() / "half/textures/workhouse"
PREV = common.build() / "workhouse-preview"

ISSUES = []      # layout problems found while drawing: (key, message)

# colours (RGB) sampled from the originals
GREY = (113, 116, 138)       # body text on white cards
BLUE = (78, 116, 154)        # bold italic headings on white cards
LOGO = (43, 123, 168)        # slogan under the logo, right panel
INK = (43, 83, 115)          # handwritten slogans
NAVY = (27, 45, 73)          # column headers
WHITE = (255, 255, 255)
RED = (246, 41, 41)
DIM = (55, 70, 104)          # dim message text
LABEL = (111, 129, 150)      # "earned" label
TASK_NO = "#01287472"        # the task number printed on the middle panel


_FONTS = None


def font(name, size):
    global _FONTS
    if _FONTS is None:
        _FONTS = fonts.ensure()
    return ImageFont.truetype(str(_FONTS / f"{name}.ttf"), size)


# ---------------------------------------------------------------- erasing

def erase_fill(img, box, rgb=None):
    """Flat fill (opaque). Colour = most common colour on the box border unless given."""
    x0, y0, x1, y1 = box
    if rgb is None:
        border = np.concatenate([img[y0 - 2, x0:x1], img[y1 + 1, x0:x1], img[y0:y1, x0 - 2], img[y0:y1, x1 + 1]])
        v, c = np.unique(border, axis=0, return_counts=True)
        img[y0:y1, x0:x1] = v[c.argmax()]
    else:
        img[y0:y1, x0:x1, :3] = rgb
        img[y0:y1, x0:x1, 3] = 255


def erase_rows(img, box, ref=6):
    """Per row: linear blend between the median of a strip left and right of the box.
    Handles vertical gradients and gentle horizontal shading (buttons, panel backgrounds)."""
    x0, y0, x1, y1 = box
    left = np.median(img[y0:y1, x0 - ref:x0].astype(float), axis=1)
    right = np.median(img[y0:y1, x1:x1 + ref].astype(float), axis=1)
    t = np.linspace(0, 1, x1 - x0)[None, :, None]
    img[y0:y1, x0:x1] = np.round(left[:, None] * (1 - t) + right[:, None] * t).astype(np.uint8)


def erase_clear(img, box):
    x0, y0, x1, y1 = box
    img[y0:y1, x0:x1] = 0


def erase_colour(img, box, rgb, tol=90):
    """Make pixels transparent whose un-premultiplied colour is near rgb (transparent textures)."""
    x0, y0, x1, y1 = box
    reg = img[y0:y1, x0:x1].astype(float)
    a = np.maximum(reg[:, :, 3:4], 1) / 255
    straight = reg[:, :, :3] / a
    m = (np.abs(straight - np.array(rgb)).sum(axis=2) < tol) & (reg[:, :, 3] > 0)
    m = cv2.dilate(m.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)
    reg[m] = 0
    img[y0:y1, x0:x1] = reg.astype(np.uint8)


# ---------------------------------------------------------------- drawing

def over(img, mask, rgb, ox, oy):
    """Premultiplied 'over' of a solid colour with coverage mask (float 0..1) at ox, oy."""
    h, w = mask.shape
    H, W = img.shape[:2]
    x0, y0, x1, y1 = max(ox, 0), max(oy, 0), min(ox + w, W), min(oy + h, H)
    if x1 <= x0 or y1 <= y0:
        return
    m = mask[y0 - oy:y1 - oy, x0 - ox:x1 - ox, None]
    dst = img[y0:y1, x0:x1].astype(float)
    src = np.concatenate([np.array(rgb, float) * m, 255 * m], axis=2)
    img[y0:y1, x0:x1] = np.round(src + dst * (1 - m)).astype(np.uint8)


def tint(img, mask, ratio, ox, oy):
    """Engraved look: multiply the background under the glyphs by ratio (per channel; < 1 darkens,
    > 1 lightens)."""
    h, w = mask.shape
    H, W = img.shape[:2]
    x0, y0, x1, y1 = max(ox, 0), max(oy, 0), min(ox + w, W), min(oy + h, H)
    m = mask[y0 - oy:y1 - oy, x0 - ox:x1 - ox, None]
    dst = img[y0:y1, x0:x1].astype(float)
    f = 1 - m * (1 - np.append(np.array(ratio, float), 1.0))
    out = np.round(dst * f)
    out[:, :, :3] = np.minimum(out[:, :, :3], dst[:, :, 3:4])   # premultiplied: colour <= alpha
    img[y0:y1, x0:x1] = np.clip(out, 0, 255).astype(np.uint8)


def text_mask(lines, fnt, pitch, align, tracking=0):
    """Render lines into a coverage mask; returns mask and per-line ink boxes."""
    widths = [line_width(l, fnt, tracking) for l in lines]
    asc, desc = fnt.getmetrics()
    W = int(max(widths)) + 40
    H = int(pitch * (len(lines) - 1) + asc + desc) + 40
    im = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(im)
    for i, (l, w) in enumerate(zip(lines, widths)):
        x = 20 + {"center": (max(widths) - w) / 2, "left": 0, "right": max(widths) - w}[align]
        y = 20 + i * pitch
        if tracking:
            for ch in l:
                d.text((x, y), ch, font=fnt, fill=255)
                x += fnt.getlength(ch) + tracking
        else:
            d.text((x, y), l, font=fnt, fill=255)
    return np.asarray(im, float) / 255


def line_width(l, fnt, tracking=0):
    return fnt.getlength(l) + tracking * max(len(l) - 1, 0)


def wrap(text, fnt, width):
    out = []
    for para in text.split("\n"):
        line = ""
        for word in para.split(" "):
            cand = (line + " " + word).strip()
            if line and fnt.getlength(cand) > width:
                out.append(line)
                line = word
            else:
                line = cand
        out.append(line)
    return out


def ink_box(mask):
    ys, xs = np.where(mask > 0.05)
    return xs.min(), ys.min(), xs.max() + 1, ys.max() + 1


def draw(img, text, fontname, size, rgb, box, align="center", pitch=None, wrap_width=None,
         valign="top", tracking=0, mode="over", ratio=None, min_size=None, shear=0.0,
         key=None, max_bottom=None):
    """Place text so its ink box is aligned in `box` (x0, y0, x1, y1).
    valign 'top': first line's cap top at y0; 'center': ink centred vertically in box.
    Shrinks the font (down to min_size) if the ink is wider than the box. Records an entry in
    ISSUES if it still doesn't fit: wider than the box, more wrapped lines than KEYS allows,
    ink below max_bottom, or ink outside the texture."""
    size_now = size
    while True:
        fnt = font(fontname, size_now)
        p = pitch * size_now / size if pitch else size_now * 1.2
        lines = wrap(text, fnt, wrap_width * size_now / size) if wrap_width else text.split("\n")
        mask = text_mask(lines, fnt, p, align, tracking)
        if shear:  # fake slant for the handwritten slogans: x += shear * (height - y)
            h, w = mask.shape
            M = np.float32([[1, -shear, shear * h], [0, 1, 0]])
            mask = cv2.warpAffine(mask, M, (int(w + shear * h) + 2, h), flags=cv2.INTER_LINEAR)
        bx0, by0, bx1, by1 = ink_box(mask)
        if bx1 - bx0 <= box[2] - box[0] or size_now <= (min_size or size):
            break
        size_now -= 1
    if size_now != size:
        print(f"    shrunk {text[:30]!r} {size}->{size_now}")
    x0, y0, x1, y1 = box
    ox = {"center": (x0 + x1) / 2 - (bx0 + bx1) / 2, "left": x0 - bx0, "right": x1 - bx1}[align]
    if valign == "top":
        # align cap height (not accents) with y0: use the top of an 'H' in this font
        cap_top = 20 + fnt.getbbox("H")[1]
        oy = y0 - cap_top
    else:
        oy = (y0 + y1) / 2 - (by0 + by1) / 2
    ox, oy = int(round(ox)), int(round(oy))
    label = key or repr(text[:30])
    H, W = img.shape[:2]
    if bx1 - bx0 > x1 - x0 + 1:
        ISSUES.append((label, f"too wide: {bx1 - bx0}px for {x1 - x0}px even at size {size_now}"))
    if key in KEYS and len(lines) > KEYS[key][2]:
        ISSUES.append((label, f"{len(lines)} lines after wrapping, max {KEYS[key][2]}"))
    if max_bottom is not None and oy + by1 > max_bottom:
        ISSUES.append((label, f"runs {oy + by1 - max_bottom}px into the element below"))
    if ox + bx0 < 0 or oy + by0 < 0 or ox + bx1 > W or oy + by1 > H:
        ISSUES.append((label, "cut off at the texture edge"))
    if mode == "tint":
        tint(img, mask, ratio, ox, oy)
    else:
        over(img, mask, rgb, ox, oy)
    return lines


# ---------------------------------------------------------------- buttons

def glyph_boxes(img, box, th=25):
    """Engraved letters (darker than the row median) inside box -> (ink bbox, tint ratio RGB, mask)
    or None if no lettering is found (e.g. the very faint *_disabled buttons)."""
    x0, y0, x1, y1 = box
    reg = img[y0:y1, x0:x1, :3].astype(float)
    bg = np.median(reg, axis=1, keepdims=True)
    d = (bg - reg).sum(axis=2)
    m = d > th
    if m.sum() < 20:
        return None
    ys, xs = np.where(m)
    sel = d > d.max() * 0.7
    ratio = np.median((reg[sel] + 1) / (np.broadcast_to(bg, reg.shape)[sel] + 1), axis=0)
    return (x0 + xs.min(), y0 + ys.min(), x0 + xs.max() + 1, y0 + ys.max() + 1), ratio, sel


def ratio_under(img, box, sel):
    """Tint ratio of a variant measured under another variant's glyph mask (same layout)."""
    x0, y0, x1, y1 = box
    reg = img[y0:y1, x0:x1, :3].astype(float)
    bg = np.median(reg, axis=1, keepdims=True)
    # > 1 where the lettering is lighter than the button (the faint *_disabled variants)
    return np.median((reg[sel] + 1) / (np.broadcast_to(bg, reg.shape)[sel] + 1), axis=0)


def button(img, word, search, max_right=None, pitch_max=64, min_left=None, th=25, key=None, base=None):
    """Redraw an engraved button label. `base` = the enabled variant's texture name: its lettering
    supplies the geometry when this variant's own lettering is too faint to detect."""
    found = glyph_boxes(img, search, th)
    if found is None and base:
        _, base_img = tex.decode(ORIG / f"{base}.tex")
        bfound = glyph_boxes(base_img, search, 25)
        if bfound is not None:
            found = (bfound[0], ratio_under(img, search, bfound[2]), bfound[2])
    if found is None:
        ISSUES.append((key or word, f"no lettering found in the original texture (search box {search})"))
        return None
    (gx0, gy0, gx1, gy1), ratio, _ = found
    erase_rows(img, (gx0 - 6, gy0 - 4, gx1 + 6, gy1 + 4))
    cap_h = gy1 - gy0
    # Big Shoulders Display: cap height = 0.75 em
    fnt_size = int(round(cap_h / 0.75))
    fnt = font("BSD-300", fnt_size)
    glyph_w = max(fnt.getlength(c) for c in word)
    cx = (gx0 + gx1) / 2
    left = min_left or gx0
    avail = (max_right or gx1) - left
    n = len(word)
    pitch = min(pitch_max, (avail - glyph_w) / max(n - 1, 1))
    if pitch < glyph_w + 2:
        ISSUES.append((key or word, f"{n} letters don't fit the button (letters would touch); use a shorter word"))
    tracking = pitch - np.mean([fnt.getlength(c) for c in word])
    draw(img, word, "BSD-300", fnt_size, None, (left, gy0, max_right or gx1, gy1),
         align="center", tracking=tracking, mode="tint", ratio=ratio, key=key)
    return (gx0, gy0, gx1, gy1)


# ---------------------------------------------------------------- what to translate

# key -> (texture, crop box shown to the translator, max lines, note)
KEYS = {
    "panel_left.body": ("panel_left", (70, 400, 640, 830), 7, "job description, wrapped automatically"),
    "panel_left.tagline": ("panel_left", (70, 915, 640, 1035), 2, "bold italic; use \\n for the line break"),
    "panel_right.welcome": ("panel_right", (90, 130, 690, 190), 1, "heading"),
    "panel_right.intro": ("panel_right", (90, 225, 690, 375), 4, "italic, wrapped automatically"),
    "panel_right.slogan": ("panel_right", (150, 770, 680, 835), 1, "company slogan under the logo"),
    "panel_right.balance": ("panel_right", (200, 920, 620, 975), 1, "label above the balance display"),
    "panel_middle.task_label": ("panel_middle", (130, 495, 520, 560), 1, f"word before the task number {TASK_NO}"),
    "panel_middle.instruction": ("panel_middle", (940, 495, 1770, 560), 1, "instruction in the header bar"),
    "panel_middle.col_receipt": ("panel_middle", (415, 645, 580, 700), 1, "column header, short"),
    "panel_middle.col_description": ("panel_middle", (1115, 645, 1355, 700), 1, "column header, short"),
    "panel_middle.col_price": ("panel_middle", (1660, 645, 1780, 700), 1, "column header, short"),
    "panel_middle.slogan": ("panel_middle", (270, 1980, 950, 2070), 1, "the slogan again, handwritten style"),
    "message_complete.title": ("message_complete", (240, 25, 1045, 125), 1, "banner"),
    "message_complete.earned": ("message_complete", (360, 160, 900, 235), 1, "label before the amount (amount stays)"),
    "message_complete.slogan": ("message_complete", (930, 290, 1287, 364), 1, "handwritten exclamation"),
    "message_rejected.title": ("message_rejected", (0, 0, 726, 150), 2, "red capitals, two lines (\\n)"),
    "message_rejected.hint": ("message_rejected", (0, 260, 726, 310), 1, ""),
    "message_disconnect.question": ("message_disconnect", (0, 0, 517, 130), 2, "small texture: keep it short, \\n"),
    "message_verifying.text": ("message_verifying", (0, 0, 419, 49), 1, "small texture: keep it short"),
    "popup_connecting.text": ("popup_connecting", (270, 255, 640, 325), 1, "followed by the logo"),
    "button.submit": ("submit", (0, 0, 619, 155), 1, "CAPITALS, ≤ 9 letters"),
    "button.cancel": ("cancel", (0, 0, 582, 134), 1, "CAPITALS, ≤ 10 letters"),
    "button.disconnect": ("disconnect", (0, 0, 582, 134), 1, "CAPITALS, ≤ 10 letters"),
    "button.exit": ("exit", (0, 0, 449, 280), 1, "CAPITALS, ≤ 8 letters"),
    "button.okay": ("okay", (0, 0, 619, 155), 1, "CAPITALS; leave OKAY if it works in your language"),
}


def panel_left(img, t):
    erase_fill(img, (90, 400, 625, 1040))
    draw(img, t["panel_left.body"], "RC-400", 48, GREY, (95, 415, 620, 820), pitch=57.5, wrap_width=500, key="panel_left.body",
         max_bottom=905)
    draw(img, t["panel_left.tagline"], "RCI-700", 50, BLUE, (85, 925, 630, 1030), pitch=59, min_size=40, key="panel_left.tagline",
         max_bottom=1100)


def panel_right(img, t):
    erase_fill(img, (100, 130, 684, 375), WHITE)
    draw(img, t["panel_right.welcome"], "RCI-700", 55, BLUE, (125, 139, 645, 181), min_size=40, key="panel_right.welcome")
    draw(img, t["panel_right.intro"], "RCI-400", 38, GREY, (110, 232, 660, 430), pitch=48.5, wrap_width=520, key="panel_right.intro",
         max_bottom=440)
    erase_fill(img, (180, 776, 655, 832))
    draw(img, t["panel_right.slogan"], "RCI-400", 45, LOGO, (110, 781, 660, 825), min_size=34, key="panel_right.slogan")
    erase_fill(img, (250, 925, 575, 970))
    draw(img, t["panel_right.balance"], "R-400", 40, WHITE, (210, 932, 615, 962), min_size=30, key="panel_right.balance")


def panel_middle(img, t):
    erase_fill(img, (135, 500, 500, 560))
    draw(img, f'{t["panel_middle.task_label"]} {TASK_NO}', "R-400", 46, WHITE, (145, 509, 700, 543), align="left",
         key="panel_middle.task_label")
    erase_fill(img, (950, 500, 1760, 560))
    draw(img, t["panel_middle.instruction"], "R-400", 46, WHITE, (720, 508, 1741, 552), align="right", min_size=34, key="panel_middle.instruction")
    for (x0, x1), key in [((429, 567), "col_receipt"), ((1130, 1339), "col_description"), ((1676, 1767), "col_price")]:
        erase_fill(img, (x0 - 8, 645, x1 + 8, 700))
        cx = (x0 + x1) / 2
        w = {"col_receipt": 170, "col_description": 220, "col_price": 120}[key]
        draw(img, t["panel_middle." + key], "R-400", 40, NAVY, (cx - w, 653, cx + w, 685), min_size=28,
             key="panel_middle." + key)
    erase_rows(img, (275, 1980, 940, 2070))
    draw(img, t["panel_middle.slogan"], "Kalam-Bold", 60, INK, (240, 1990, 1000, 2060),
         align="left", valign="center", shear=0.22, min_size=40, key="panel_middle.slogan")


def message_complete(img, t):
    erase_rows(img, (240, 25, 1045, 125))
    draw(img, t["message_complete.title"], "RCI-700", 84, WHITE, (240, 36, 1045, 101), min_size=56, key="message_complete.title")
    erase_colour(img, (360, 160, 740, 235), LABEL)
    draw(img, t["message_complete.earned"], "RC-700", 62, LABEL, (240, 172, 712, 214), align="right", min_size=44, key="message_complete.earned")
    erase_clear(img, (930, 290, 1287, 364))
    draw(img, t["message_complete.slogan"], "Kalam-Bold", 62, INK, (900, 296, 1278, 362), align="right",
         valign="center", shear=0.22, min_size=44, key="message_complete.slogan")


def message_rejected(img, t):
    erase_clear(img, (0, 0, 726, 310))
    draw(img, t["message_rejected.title"], "R-700", 64, RED, (0, 12, 726, 140), pitch=86, min_size=44, key="message_rejected.title",
         max_bottom=255)
    draw(img, t["message_rejected.hint"], "RCI-700", 49, DIM, (20, 265, 706, 307), min_size=36, key="message_rejected.hint")


def message_disconnect(img, t):
    erase_clear(img, (0, 0, 517, 130))
    draw(img, t["message_disconnect.question"], "RCI-700", 60, DIM, (0, 4, 517, 128), pitch=62,
         valign="center", min_size=40, key="message_disconnect.question")


def message_verifying(img, t):
    erase_clear(img, (0, 0, 419, 49))
    draw(img, t["message_verifying.text"], "RCI-700", 49, DIM, (0, 0, 419, 49), valign="center", min_size=34, key="message_verifying.text")


def popup_connecting(img, t):
    erase_rows(img, (276, 258, 634, 324))
    draw(img, t["popup_connecting.text"], "RI-400", 49, WHITE, (200, 269, 710, 316), min_size=36, key="popup_connecting.text")


# texture -> (drawing function or button spec). Button spec: (key, glyph search box, kwargs)
BUTTONS = {
    "submit": ("button.submit", (60, 30, 440, 125), dict(max_right=430)),
    "cancel": ("button.cancel", (80, 30, 500, 105), dict(pitch_max=55)),
    "disconnect": ("button.disconnect", (80, 30, 520, 105), dict(pitch_max=55)),
    "exit": ("button.exit", (85, 155, 272, 240), dict(pitch_max=50, min_left=62)),
    "okay": ("button.okay", (60, 30, 560, 125), dict(min_left=115, max_right=500)),  # no icon: room to spread
}
PANELS = {
    "panel_left": panel_left, "panel_right": panel_right, "panel_middle": panel_middle,
    "message_complete": message_complete, "message_rejected": message_rejected,
    "message_disconnect": message_disconnect, "message_verifying": message_verifying,
    "popup_connecting": popup_connecting,
}
ENGLISH_BUTTONS = {"button.okay": "OKAY"}   # skip a button whose translation equals this


def jobs(t):
    """(texture name, function(img)) for everything that needs redrawing."""
    out = [(name, (lambda f: lambda img: f(img, t))(f)) for name, f in PANELS.items()]
    for base, (key, search, kw) in BUTTONS.items():
        if t.get(key, "").strip() == ENGLISH_BUTTONS.get(key):
            continue
        for variant in sorted(p.stem for p in ORIG.glob(base + "*.tex")):
            if variant == base or variant.startswith(base + "_"):
                th = 8 if variant.endswith("_disabled") else 25
                out.append((variant, (lambda k, s, kw, th, b: lambda img: button(img, t[k], s, th=th, key=k, base=b, **kw))(
                    key, search, kw, th, base)))
    return out


# ---------------------------------------------------------------- commands

def tpath():
    return common.tr() / "workhouse.json"


def composite(img, bg=(40, 30, 60)):
    a = img[:, :, 3:4].astype(float) / 255
    return np.clip(img[:, :, :3] + np.array(bg, float) * (1 - a), 0, 255).astype(np.uint8)


def extract():
    dst = common.source() / "workhouse"
    dst.mkdir(parents=True, exist_ok=True)
    for key, (texname, (x0, y0, x1, y1), _, _) in KEYS.items():
        _, img = tex.decode(ORIG / f"{texname}.tex")
        crop = composite(img)[y0:y1, x0:x1]
        cv2.imwrite(str(dst / f"{key}.png"), cv2.cvtColor(crop, cv2.COLOR_RGB2BGR))
    print(f"wrote {len(KEYS)} crops to {dst}")
    if tpath().exists():
        print(f"{tpath()} exists; not overwriting")
        return
    tpath().parent.mkdir(parents=True, exist_ok=True)
    tmpl = {"_notes": {k: f"{v[3]} (max {v[2]} line{'s' if v[2] > 1 else ''}); see source/workhouse/{k}.png"
                       for k, v in KEYS.items()}}
    tmpl.update({k: "" for k in KEYS})
    tpath().write_text(json.dumps(tmpl, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote template {tpath()}")


FONT_OF = {"panel_left.body": "RC-400", "panel_left.tagline": "RCI-700", "panel_right.welcome": "RCI-700",
           "panel_right.intro": "RCI-400", "panel_right.slogan": "RCI-400", "panel_middle.slogan": "Kalam-Bold",
           "message_complete.title": "RCI-700", "message_complete.earned": "RC-700",
           "message_complete.slogan": "Kalam-Bold", "message_rejected.title": "R-700",
           "message_rejected.hint": "RCI-700", "message_disconnect.question": "RCI-700",
           "message_verifying.text": "RCI-700", "popup_connecting.text": "RI-400"}


def load():
    if not tpath().exists():
        sys.exit(f"{tpath()} not found (run: python tools/workhouse.py extract)")
    try:
        t = json.loads(tpath().read_text(encoding="utf-8-sig"))
    except ValueError as e:
        sys.exit(f"{tpath()}: invalid JSON: {e}")
    return {k: v.replace("\\n", "\n") if isinstance(v, str) else v for k, v in t.items()}


def problems(t):
    from fontTools.ttLib import TTFont
    d = fonts.ensure()
    cmaps = {}
    errs = []
    for key, (_, _, maxl, _) in KEYS.items():
        v = t.get(key, "")
        if not v.strip():
            errs.append(f"{key}: empty")
            continue
        if v.count("\n") + 1 > maxl:
            errs.append(f"{key}: {v.count(chr(10)) + 1} lines, max {maxl}")
        fname = "BSD-300" if key.startswith("button.") else FONT_OF.get(key, "R-400")
        if key.startswith("button.") and v != v.upper():
            errs.append(f"{key}: buttons are lettered in capitals")
        if fname not in cmaps:
            cmaps[fname] = TTFont(d / f"{fname}.ttf").getBestCmap()
        missing = sorted({c for c in v if c not in "\n" and ord(c) not in cmaps[fname]})
        if missing:
            errs.append(f"{key}: font {fname} has no glyph for {''.join(missing)!r}")
    return errs


def layout(t):
    """Draw everything in memory. Returns {texture name: (original, translated)} and fills ISSUES."""
    ISSUES.clear()
    out = {}
    for name, fn in jobs(t):
        _, orig = tex.decode(ORIG / f"{name}.tex")
        img = orig.copy()
        fn(img)
        out[name] = (orig, img)
    return out


def half_size(name, img):
    """The game also ships every texture at half resolution (PackedContent/half/...), used at lower
    quality settings. Downscale the translated full-size image to the half original's exact size
    (INTER_AREA works on premultiplied pixels) and encode it with the half original's header."""
    src = HALF_ORIG / f"{name}.tex"
    if not src.exists():
        return None
    _, h = tex.decode(src)
    small = cv2.resize(img, (h.shape[1], h.shape[0]), interpolation=cv2.INTER_AREA)
    HALF_OUT.mkdir(parents=True, exist_ok=True)
    tex.encode(src, small, HALF_OUT / f"{name}.tex")
    return small


def build(t):
    import shutil
    drawn = layout(t)
    if ISSUES:
        report_issues()
        sys.exit("not building: fix the overflowing texts first")
    for d in (OUT, HALF_OUT):          # no stale textures from earlier builds
        if d.exists():
            shutil.rmtree(d)
    OUT.mkdir(parents=True)
    PREV.mkdir(parents=True, exist_ok=True)
    print(f"WorkHouse textures -> {OUT} (+ half resolution -> {HALF_OUT})")
    for name, (orig, img) in drawn.items():
        tex.encode(ORIG / f"{name}.tex", img, OUT / f"{name}.tex")
        half_size(name, img)
        both = np.concatenate([composite(orig), np.full((orig.shape[0], 12, 3), 255, np.uint8), composite(img)], axis=1)
        cv2.imwrite(str(PREV / f"{name}.png"), cv2.cvtColor(both, cv2.COLOR_RGB2BGR))
        print(f"  {name}")
    print(f"previews (original | translated): {PREV}")


def report_issues():
    for key, msg in dict.fromkeys(ISSUES):   # button variants repeat the same message
        print(f"{key}: {msg}")


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "check"
    if cmd in ("-h", "--help", "help") or cmd not in ("extract", "check", "build"):
        print(__doc__)
        sys.exit(0 if cmd in ("-h", "--help", "help") else 2)
    if cmd == "extract":
        return extract()
    t = load()
    errs = problems(t)
    if errs:
        print("\n".join(errs))
        sys.exit(1)
    if cmd == "check":
        layout(t)
        report_issues()
        print("no problems" if not ISSUES else f"{len(dict.fromkeys(ISSUES))} layout problem(s)")
        sys.exit(1 if ISSUES else 0)
    build(t)


if __name__ == "__main__":
    main()
