#!/usr/bin/env python3
"""Generate a multi-size Windows icon for ArtyGal."""

from __future__ import annotations

from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "role" / "artygal.png"
OUTPUT = ROOT / "resources" / "artygal.ico"
SIZES = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]


def main() -> None:
    if not SOURCE.exists():
        raise FileNotFoundError(SOURCE)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    image = Image.open(SOURCE).convert("RGBA")
    image.save(OUTPUT, sizes=SIZES)
    print(f"wrote {OUTPUT}")


if __name__ == "__main__":
    main()
