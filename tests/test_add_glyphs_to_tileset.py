import tempfile
import unittest
from pathlib import Path

from add_glyphs_to_tileset import (
    GlyphAddition,
    add_glyphs_to_tileset,
    load_source_images,
    parse_placement,
    parse_placements,
)
from build_tileset_from_png_font import (
    FONT_COLUMNS,
    FONT_ROWS,
    MISAKI_SPEC,
    TILESET_HEIGHT,
    TILESET_WIDTH,
    load_pillow,
    source_box_for_kuten,
)


class AddGlyphsToTilesetTest(unittest.TestCase):
    def test_parses_character_and_tile_coordinates(self):
        self.assertEqual(parse_placement("Ⅰ=14,15"), GlyphAddition("Ⅰ", 14, 15))
        self.assertEqual(parse_placement("あ=0xF,0x17"), GlyphAddition("あ", 15, 23))

    def test_rejects_invalid_character_coordinates_and_duplicate_positions(self):
        for value in ("", "Ⅰ", "Ⅰ=1", "Ⅰ=1,2,3", "Ⅰ=x,2", "Ⅰ=16,0", "Ⅰ=0,24"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                parse_placement(value)

        with self.assertRaisesRegex(ValueError, "duplicate"):
            parse_placements(["Ⅰ=1,2", "Ⅱ=1,2"])

    def test_allows_same_character_at_different_positions(self):
        self.assertEqual(
            parse_placements(["Ⅰ=1,2", "Ⅰ=3,4"]),
            [GlyphAddition("Ⅰ", 1, 2), GlyphAddition("Ⅰ", 3, 4)],
        )

    def test_adds_standard_and_misaki_extension_glyphs(self):
        Image = load_pillow()
        font_size = (
            MISAKI_SPEC.glyph_width * FONT_COLUMNS,
            MISAKI_SPEC.glyph_height * FONT_ROWS,
        )
        font_image = Image.new("RGB", font_size, "white")
        tileset = Image.new("RGB", (TILESET_WIDTH, TILESET_HEIGHT), "black")
        font_image.paste((255, 0, 0), source_box_for_kuten((4, 2), font_spec=MISAKI_SPEC))
        font_image.paste(
            (0, 0, 255),
            source_box_for_kuten((13, 21), font_spec=MISAKI_SPEC),
        )

        output = add_glyphs_to_tileset(
            font_image,
            tileset,
            [GlyphAddition("あ", 0, 0), GlyphAddition("Ⅰ", 15, 23)],
        )

        self.assertEqual(output.getpixel((0, 0)), (255, 0, 0))
        self.assertEqual(output.getpixel((127, 191)), (0, 0, 255))
        self.assertEqual(tileset.getpixel((0, 0)), (0, 0, 0))

    def test_overwrites_reserved_positions_when_explicitly_requested(self):
        Image = load_pillow()
        font_size = (
            MISAKI_SPEC.glyph_width * FONT_COLUMNS,
            MISAKI_SPEC.glyph_height * FONT_ROWS,
        )
        font_image = Image.new("RGB", font_size, "white")
        tileset = Image.new("RGB", (TILESET_WIDTH, TILESET_HEIGHT), "black")

        output = add_glyphs_to_tileset(
            font_image,
            tileset,
            [GlyphAddition("Ⅰ", 14, 15), GlyphAddition("Ⅱ", 15, 23)],
        )

        self.assertEqual(output.getpixel((112, 120)), (255, 255, 255))
        self.assertEqual(output.getpixel((120, 184)), (255, 255, 255))

    def test_rejects_character_without_misaki_kuten_mapping(self):
        Image = load_pillow()
        font_size = (
            MISAKI_SPEC.glyph_width * FONT_COLUMNS,
            MISAKI_SPEC.glyph_height * FONT_ROWS,
        )
        font_image = Image.new("RGB", font_size, "white")
        tileset = Image.new("RGB", (TILESET_WIDTH, TILESET_HEIGHT), "white")

        with self.assertRaisesRegex(ValueError, r"U\+1F600"):
            add_glyphs_to_tileset(
                font_image,
                tileset,
                [GlyphAddition("😀", 0, 0)],
            )

    def test_load_source_images_validates_both_dimensions(self):
        Image = load_pillow()
        valid_font_size = (
            MISAKI_SPEC.glyph_width * FONT_COLUMNS,
            MISAKI_SPEC.glyph_height * FONT_ROWS,
        )
        with tempfile.TemporaryDirectory() as directory:
            font_path = Path(directory) / "font.png"
            tileset_path = Path(directory) / "tileset.png"
            Image.new("RGB", valid_font_size, "white").save(font_path)
            Image.new("RGB", (8, 8), "white").save(tileset_path)

            with self.assertRaisesRegex(ValueError, "128x192"):
                load_source_images(font_path, tileset_path)

            Image.new("RGB", (8, 8), "white").save(font_path)
            Image.new("RGB", (TILESET_WIDTH, TILESET_HEIGHT), "white").save(
                tileset_path
            )
            with self.assertRaisesRegex(ValueError, "752x752"):
                load_source_images(font_path, tileset_path)


if __name__ == "__main__":
    unittest.main()
