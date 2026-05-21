import unittest
import json

from char_counter import count_characters, display_char, format_counts, format_csv, format_json


class CountCharactersTest(unittest.TestCase):
    def test_counts_distinct_japanese_characters(self):
        counter = count_characters("あいうえおあ")

        self.assertEqual(len(counter), 5)
        self.assertEqual(counter["あ"], 2)
        self.assertEqual(counter["い"], 1)

    def test_preserves_first_seen_order(self):
        counter = count_characters("babaac")

        self.assertEqual(list(counter.keys()), ["b", "a", "c"])

    def test_includes_whitespace_by_default(self):
        counter = count_characters("a \n\t")

        self.assertEqual(list(counter.keys()), ["a", " ", "\n", "\t"])
        self.assertEqual(len(counter), 4)

    def test_excludes_whitespace_when_requested(self):
        counter = count_characters("a \n\tb", exclude_whitespace=True)

        self.assertEqual(list(counter.keys()), ["a", "b"])

    def test_empty_text_has_zero_types(self):
        counter = count_characters("")

        self.assertEqual(len(counter), 0)

    def test_displays_common_whitespace_labels(self):
        self.assertEqual(display_char(" "), "<SPACE>")
        self.assertEqual(display_char("\n"), "<LF>")
        self.assertEqual(display_char("\t"), "<TAB>")

    def test_formats_counts(self):
        output = format_counts(count_characters("ああ\n"))

        self.assertEqual(output, "種類数: 2\n文字\t回数\nあ\t2\n<LF>\t1")

    def test_formats_csv(self):
        output = format_csv(count_characters("ああ\n"))

        self.assertEqual(output, 'character,display,count\r\nあ,あ,2\r\n"\n",<LF>,1')

    def test_formats_json(self):
        output = format_json(count_characters("ああ\n"))

        self.assertEqual(
            json.loads(output),
            {
                "type_count": 2,
                "characters": [
                    {"character": "あ", "display": "あ", "count": 2},
                    {"character": "\n", "display": "<LF>", "count": 1},
                ],
            },
        )


if __name__ == "__main__":
    unittest.main()
