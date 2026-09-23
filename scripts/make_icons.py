#!/usr/bin/env python3
"""Generate the PWA icons for docs/.

The icon is drawn with Pillow: a dark rounded square holding a two-qubit
circuit glyph (control dot, CNOT target, measurement bar). Regenerating is
deterministic, so the PNGs in docs/ can always be reproduced from this script.

    python3 scripts/make_icons.py
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
SIZES = (192, 512)
BACKGROUND = (11, 18, 32, 255)
WIRE = (147, 162, 189, 255)
ACCENT = (77, 140, 245, 255)
MARK = (62, 207, 142, 255)


def draw_icon(size: int) -> Image.Image:
    scale = size / 192.0
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    def box(values):
        return [round(value * scale) for value in values]

    draw.rounded_rectangle(box([0, 0, 192, 192]), radius=round(40 * scale), fill=BACKGROUND)

    # Two qubit wires.
    draw.rounded_rectangle(box([28, 62, 164, 66]), radius=round(2 * scale), fill=WIRE)
    draw.rounded_rectangle(box([28, 126, 164, 130]), radius=round(2 * scale), fill=WIRE)

    # Control dot on the upper wire, CNOT target on the lower one.
    draw.ellipse(box([84, 52, 108, 76]), fill=ACCENT)
    draw.ellipse(box([72, 114, 120, 162]), outline=ACCENT, width=round(6 * scale))
    draw.rounded_rectangle(box([92, 100, 100, 142]), radius=round(4 * scale), fill=ACCENT)

    # Hadamard block on the upper wire.
    draw.rounded_rectangle(box([116, 44, 156, 84]), radius=round(8 * scale), fill=MARK)

    return image


def main() -> int:
    DOCS.mkdir(parents=True, exist_ok=True)
    for size in SIZES:
        target = DOCS / f"icon-{size}.png"
        draw_icon(size).save(target, format="PNG", optimize=True)
        print(f"wrote {target.relative_to(ROOT)} ({size}x{size})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
