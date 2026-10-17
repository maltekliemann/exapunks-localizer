#!/usr/bin/env python3
"""Decode/encode EXAPUNKS .tex textures (see .claude/skills/exapunks-localize/reference/game-internals.md).

Format (as observed): 60-byte header: int32 version (1002), int32 width, int32 height, ...,
int32 at offset 56 = compressed size; then LZ4 block-compressed RGBA8 pixels, rows stored
bottom-up (the image appears upside down when decoded; decode/encode flip it for editing).
  decode <file.tex> <out.png>
  encode <orig.tex> <in.png> <out.tex>   (reuses orig header; size must match)
"""
import struct, sys
import lz4.block, numpy as np, cv2

HDR = 60


def decode(path):
    b = open(path, "rb").read()
    ver, w, h = struct.unpack_from("<iii", b, 0)
    raw = lz4.block.decompress(b[HDR:], uncompressed_size=w * h * 4)
    return b[:HDR], np.frombuffer(raw, np.uint8).reshape(h, w, 4)[::-1].copy()


def encode(orig, rgba, out):
    hdr, old = decode(orig)
    assert rgba.shape == old.shape, f"size mismatch {rgba.shape} vs {old.shape}"
    comp = lz4.block.compress(np.ascontiguousarray(rgba[::-1]).tobytes(), store_size=False)
    hdr = hdr[:56] + struct.pack("<i", len(comp)) + hdr[60:]
    open(out, "wb").write(hdr + comp)


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in ("decode", "encode"):
        sys.exit(__doc__)
    if sys.argv[1] == "decode":
        _, img = decode(sys.argv[2])
        cv2.imwrite(sys.argv[3], cv2.cvtColor(img, cv2.COLOR_RGBA2BGRA))
    elif sys.argv[1] == "encode":
        img = cv2.imread(sys.argv[3], cv2.IMREAD_UNCHANGED)
        encode(sys.argv[2], cv2.cvtColor(img, cv2.COLOR_BGRA2RGBA), sys.argv[4])
