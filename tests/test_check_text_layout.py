import unittest

from check_text_layout import (
    check_text_layout,
    split_pages_with_line_numbers,
)


class CheckTextLayoutTest(unittest.TestCase):
    def test_accepts_line_with_18_characters(self):
        self.assertEqual(check_text_layout("あ" * 18), [])

    def test_rejects_line_with_19_regular_characters(self):
        issues = check_text_layout("あ" * 19)

        self.assertEqual(len(issues), 1)
        self.assertIn("line 1", issues[0].message)

    def test_rejects_line_over_limit_even_with_trailing_punctuation(self):
        self.assertEqual(len(check_text_layout(("あ" * 18) + "。")), 1)
        self.assertEqual(len(check_text_layout(("あ" * 18) + "、")), 1)

    def test_rejects_line_over_limit_before_trailing_punctuation(self):
        issues = check_text_layout(("あ" * 19) + "。")

        self.assertEqual(len(issues), 1)

    def test_page_break_lines_are_not_counted_as_page_lines(self):
        text = "\n".join(["あ"] * 16) + "\n[改ページ]\n" + "\n".join(["い"] * 16)

        self.assertEqual(check_text_layout(text), [])

    def test_rejects_page_with_more_than_16_lines(self):
        issues = check_text_layout("\n".join(["あ"] * 17))

        self.assertEqual(len(issues), 1)
        self.assertIn("page 0", issues[0].message)

    def test_split_pages_tracks_original_line_numbers(self):
        self.assertEqual(
            split_pages_with_line_numbers("あ\n[改ページ]\nい\n"),
            [[(1, "あ\n")], [(3, "い\n")]],
        )


if __name__ == "__main__":
    unittest.main()
