import unittest

from app.state import calculate_article_hash


class StateTestCase(unittest.TestCase):
    def test_calculate_article_hash_ignores_outer_spaces(self):
        self.assertEqual(calculate_article_hash(" article "), calculate_article_hash("article"))

    def test_calculate_article_hash_changes_for_different_texts(self):
        self.assertNotEqual(calculate_article_hash("article one"), calculate_article_hash("article two"))


if __name__ == "__main__":
    unittest.main()
