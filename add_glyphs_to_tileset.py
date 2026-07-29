#!/usr/bin/env python3
"""Add selected Misaki Font glyphs to positions in an existing PNG tileset."""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from build_tileset_from_png_font import (
    FONT_COLUMNS,
    FONT_ROWS,
    MISAKI_SPEC,
    TILE_HEIGHT,
    TILE_WIDTH,
    TILESET_COLUMNS,
    TILESET_HEIGHT,
    TILESET_ROWS,
    TILESET_WIDTH,
    load_pillow,
    source_box_for_kuten,
)
from kuten_inspector import kuten_for_character


@dataclass(frozen=True)
class GlyphAddition:
    character: str
    x: int
    y: int


def parse_placement(value: str) -> GlyphAddition:
    character, separator, coordinates = value.partition("=")
    if not separator or len(character) != 1:
        raise ValueError(
            f"invalid placement {value!r}; expected one character followed by =X,Y"
        )

    x_text, comma, y_text = coordinates.partition(",")
    if not comma or not x_text or not y_text or "," in y_text:
        raise ValueError(f"invalid placement {value!r}; expected CHARACTER=X,Y")
    try:
        x = int(x_text, 0)
        y = int(y_text, 0)
    except ValueError as exc:
        raise ValueError(
            f"invalid tile coordinates in placement {value!r}"
        ) from exc

    if not 0 <= x < TILESET_COLUMNS:
        raise ValueError(
            f"placement X must be between 0 and {TILESET_COLUMNS - 1}: {x}"
        )
    if not 0 <= y < TILESET_ROWS:
        raise ValueError(
            f"placement Y must be between 0 and {TILESET_ROWS - 1}: {y}"
        )
    return GlyphAddition(character=character, x=x, y=y)


def parse_placements(values: list[str]) -> list[GlyphAddition]:
    additions = [parse_placement(value) for value in values]
    used_positions: set[tuple[int, int]] = set()
    for addition in additions:
        position = (addition.x, addition.y)
        if position in used_positions:
            raise ValueError(
                f"duplicate destination tile position: ({addition.x},{addition.y})"
            )
        used_positions.add(position)
    return additions


def load_source_images(font_png: Path, tileset_png: Path) -> tuple[Any, Any]:
    Image = load_pillow()
    expected_font_size = (
        MISAKI_SPEC.glyph_width * FONT_COLUMNS,
        MISAKI_SPEC.glyph_height * FONT_ROWS,
    )

    with Image.open(font_png) as image:
        if image.size != expected_font_size:
            raise ValueError(
                f"Misaki font PNG must be "
                f"{expected_font_size[0]}x{expected_font_size[1]} px: "
                f"got {image.size[0]}x{image.size[1]} px"
            )
        font_image = image.convert("RGB")

    with Image.open(tileset_png) as image:
        if image.size != (TILESET_WIDTH, TILESET_HEIGHT):
            raise ValueError(
                f"tileset PNG must be {TILESET_WIDTH}x{TILESET_HEIGHT} px: "
                f"got {image.size[0]}x{image.size[1]} px"
            )
        tileset = image.convert("RGB")

    return font_image, tileset


def add_glyphs_to_tileset(
    font_image: Any,
    tileset: Any,
    additions: list[GlyphAddition],
) -> Any:
    output = tileset.copy()
    for addition in additions:
        kuten = kuten_for_character(addition.character, misaki=True)
        if kuten is None:
            raise ValueError(
                f"no Misaki kuten mapping for character: "
                f"{addition.character} (U+{ord(addition.character):04X})"
            )
        glyph = font_image.crop(
            source_box_for_kuten(kuten, font_spec=MISAKI_SPEC)
        )
        output.paste(
            glyph,
            (addition.x * TILE_WIDTH, addition.y * TILE_HEIGHT),
        )
    return output


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Add selected Misaki Font glyphs to a PNG tileset.",
    )
    parser.add_argument(
        "--font-png",
        type=Path,
        required=True,
        help="Source 752x752 px Misaki Font PNG.",
    )
    parser.add_argument(
        "--tileset",
        type=Path,
        required=True,
        help="Input 128x192 px tileset PNG.",
    )
    parser.add_argument(
        "--placement",
        action="append",
        required=True,
        metavar="CHARACTER=X,Y",
        help="Glyph and destination tile coordinates. May be specified more than once.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Output tileset PNG.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    try:
        additions = parse_placements(args.placement)
        font_image, tileset = load_source_images(args.font_png, args.tileset)
        output = add_glyphs_to_tileset(font_image, tileset, additions)
        output.save(args.output)
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
