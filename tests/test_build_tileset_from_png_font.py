import csv
import io
import tempfile
import unittest
from pathlib import Path

from build_tileset_from_png_font import (
    GlyphPlacement,
    CONTROL_BOTTOM_COLOR,
    CONTROL_TOP_COLOR,
    FIXED_SYMBOL_KUTEN,
    FIXED_SYMBOL_TILE_INDEX,
    K6X8_SPEC,
    MISAKI_SPEC,
    background_color_for_image,
    destination_position_for_index,
    fill_control_tile,
    fill_fixed_symbol_tile,
    group_placements_by_bank,
    is_reserved_blank_tile,
    load_placements,
    output_path_for_bank,
    parse_kuten,
    source_box_for_kuten,
    tile_origin_for_index,
    warn_if_tileset_is_full,
)


class BuildTilesetFromPngFontTest(unittest.TestCase):
    def test_parse_kuten(self):
        self.assertEqual(parse_kuten("04-02"), (4, 2))

    def test_rejects_out_of_range_kuten(self):
        with self.assertRaisesRegex(ValueError, "ku"):
            parse_kuten("95-01")

    def test_source_box_for_kuten(self):
        self.assertEqual(source_box_for_kuten((1, 1)), (0, 0, 6, 8))
        self.assertEqual(source_box_for_kuten((4, 2)), (6, 24, 12, 32))

    def test_source_box_for_misaki(self):
        self.assertEqual(
            source_box_for_kuten((4, 2), font_spec=MISAKI_SPEC),
            (8, 24, 16, 32),
        )

    def test_font_specs(self):
        self.assertEqual(K6X8_SPEC.default_offset_x, 1)
        self.assertEqual(K6X8_SPEC.default_offset_y, 1)
        self.assertEqual(MISAKI_SPEC.glyph_width, 8)
        self.assertEqual(MISAKI_SPEC.default_offset_x, 0)
        self.assertEqual(MISAKI_SPEC.default_offset_y, 0)

    def test_destination_position_for_index(self):
        self.assertEqual(destination_position_for_index(0), (1, 1))
        self.assertEqual(destination_position_for_index(15), (121, 1))
        self.assertEqual(destination_position_for_index(16), (1, 9))

    def test_tile_origin_for_last_tile(self):
        self.assertEqual(tile_origin_for_index(383), (120, 184))

    def test_index_255_is_reserved_blank_tile(self):
        self.assertFalse(is_reserved_blank_tile(254))
        self.assertTrue(is_reserved_blank_tile(255))
        self.assertFalse(is_reserved_blank_tile(253))
        self.assertFalse(is_reserved_blank_tile(256))

    def test_fixed_symbol_tile_constants(self):
        self.assertEqual(FIXED_SYMBOL_TILE_INDEX, 254)
        self.assertEqual(FIXED_SYMBOL_KUTEN, (2, 7))
        self.assertEqual(source_box_for_kuten(FIXED_SYMBOL_KUTEN), (36, 8, 42, 16))

    def test_load_placements_filters_bank(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "mapping.csv"
            with path.open("w", encoding="utf-8", newline="") as file:
                writer = csv.DictWriter(
                    file,
                    fieldnames=["character", "jis_x_0208_kuten", "bank", "index"],
                )
                writer.writeheader()
                writer.writerow(
                    {
                        "character": "あ",
                        "jis_x_0208_kuten": "04-02",
                        "bank": "1",
                        "index": "0",
                    }
                )
                writer.writerow(
                    {
                        "character": "い",
                        "jis_x_0208_kuten": "04-04",
                        "bank": "2",
                        "index": "0",
                    }
                )

            self.assertEqual(
                load_placements(path, bank=1),
                [GlyphPlacement(character="あ", kuten=(4, 2), bank=1, index=0)],
            )

    def test_load_placements_keeps_multiple_banks_when_bank_is_omitted(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "mapping.csv"
            with path.open("w", encoding="utf-8", newline="") as file:
                writer = csv.DictWriter(
                    file,
                    fieldnames=["character", "jis_x_0208_kuten", "bank", "index"],
                )
                writer.writeheader()
                writer.writerow(
                    {
                        "character": "あ",
                        "jis_x_0208_kuten": "04-02",
                        "bank": "1",
                        "index": "0",
                    }
                )
                writer.writerow(
                    {
                        "character": "い",
                        "jis_x_0208_kuten": "04-04",
                        "bank": "2",
                        "index": "0",
                    }
                )

            self.assertEqual(
                load_placements(path, bank=None),
                [
                    GlyphPlacement(character="あ", kuten=(4, 2), bank=1, index=0),
                    GlyphPlacement(character="い", kuten=(4, 4), bank=2, index=0),
                ],
            )

    def test_groups_placements_by_bank(self):
        placements = [
            GlyphPlacement(character="い", kuten=(4, 4), bank=2, index=0),
            GlyphPlacement(character="あ", kuten=(4, 2), bank=1, index=0),
        ]

        self.assertEqual(
            group_placements_by_bank(placements),
            {
                1: [GlyphPlacement(character="あ", kuten=(4, 2), bank=1, index=0)],
                2: [GlyphPlacement(character="い", kuten=(4, 4), bank=2, index=0)],
            },
        )

    def test_output_path_for_bank_adds_suffix_only_for_multiple_banks(self):
        output = Path("tileset.png")

        self.assertEqual(output_path_for_bank(output, bank=1, multiple_banks=False), output)
        self.assertEqual(
            output_path_for_bank(output, bank=1, multiple_banks=True),
            Path("tileset_bank1.png"),
        )

    def test_background_color_is_white(self):
        class ImageStub:
            mode = "RGB"

        self.assertEqual(background_color_for_image(ImageStub()), (255, 255, 255))

    def test_fill_control_tile_colors_last_tile(self):
        class TilesetStub:
            def __init__(self):
                self.calls = []

            def paste(self, color, box):
                self.calls.append((color, box))

        tileset = TilesetStub()

        fill_control_tile(tileset)

        self.assertEqual(
            tileset.calls,
            [
                (CONTROL_TOP_COLOR, (120, 184, 128, 188)),
                (CONTROL_BOTTOM_COLOR, (120, 188, 128, 192)),
            ],
        )

    def test_fill_fixed_symbol_tile_pastes_to_index_254(self):
        class ImageStub:
            def crop(self, box):
                self.cropped_box = box
                return "glyph"

        class TilesetStub:
            def __init__(self):
                self.calls = []

            def paste(self, glyph, position):
                self.calls.append((glyph, position))

        font_image = ImageStub()
        tileset = TilesetStub()

        fill_fixed_symbol_tile(
            tileset,
            font_image,
            font_spec=K6X8_SPEC,
            offset_x=1,
            offset_y=1,
        )

        self.assertEqual(font_image.cropped_box, (36, 8, 42, 16))
        self.assertEqual(tileset.calls, [("glyph", (113, 121))])

    def test_warns_when_tileset_is_full(self):
        stream = io.StringIO()
        placements = [
            GlyphPlacement(character="あ", kuten=(4, 2), bank=1, index=index)
            for index in range(384)
        ]

        warn_if_tileset_is_full(placements, bank=1, stream=stream)

        self.assertIn("warning: bank 1 uses 384 tiles", stream.getvalue())

    def test_does_not_warn_when_tileset_has_reserved_last_tile(self):
        stream = io.StringIO()
        placements = [
            GlyphPlacement(character="あ", kuten=(4, 2), bank=1, index=index)
            for index in range(383)
        ]

        warn_if_tileset_is_full(placements, bank=1, stream=stream)

        self.assertEqual(stream.getvalue(), "")


if __name__ == "__main__":
    unittest.main()
