import tempfile
import unittest
from pathlib import Path

from app.config import AppSettings, EmailSettings, LlmSettings, TelegramSettings
from app.llm import ArticleAnalyzer
from app.service import ArticleProcessingService
from app.state import ProcessingState


class FakeDelivery:
    def __init__(self):
        self.sent_articles = []

    def send_article(self, article_name: str, enriched_article: str) -> None:
        self.sent_articles.append((article_name, enriched_article))


def make_settings(base_path: Path) -> AppSettings:
    return AppSettings(
        article_input_dir=base_path / "inbox",
        outbox_dir=base_path / "outbox",
        processed_dir=base_path / "processed",
        failed_dir=base_path / "failed",
        database_path=base_path / "state.sqlite3",
        run_once=True,
        poll_interval_seconds=60,
        llm=LlmSettings(provider="stub", api_key="", model="", base_url=""),
        telegram=TelegramSettings(enabled=False, bot_token="", chat_ids=[]),
        email=EmailSettings(
            enabled=False,
            smtp_host="smtp.office365.com",
            smtp_port=587,
            username="",
            password="",
            from_address="",
            to_addresses=[],
        ),
    )


class ArticleProcessingServiceTestCase(unittest.TestCase):
    def test_process_pending_articles_saves_outbox_file_and_sends_result(self):

        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir)
            settings = make_settings(base_path)
            settings.article_input_dir.mkdir(parents=True)
            article_path = settings.article_input_dir / "meeting_follow_up.txt"
            article_path.write_text(
                "Нужно подготовить справку по договору до пятницы.",

                encoding="utf-8",
            )
            delivery = FakeDelivery()
            service = ArticleProcessingService(
                settings=settings,
                analyzer=ArticleAnalyzer(settings.llm),
                delivery=delivery,
                state=ProcessingState(settings.database_path),
            )

            processed_count = service.process_pending_articles()

            outbox_path = settings.outbox_dir / "meeting_follow_up.md"

            self.assertEqual(1, processed_count)
            self.assertFalse(article_path.exists())
            self.assertTrue((settings.processed_dir / "meeting_follow_up.txt").exists())

            self.assertTrue(outbox_path.exists())
            self.assertIn("Краткая справка по письму", outbox_path.read_text(encoding="utf-8"))

            self.assertEqual(1, len(delivery.sent_articles))
            self.assertIn("Структурированный анализ LLM", delivery.sent_articles[0][1])

    def test_process_pending_articles_moves_empty_input_to_failed(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir)
            settings = make_settings(base_path)
            settings.article_input_dir.mkdir(parents=True)
            article_path = settings.article_input_dir / "empty.txt"
            article_path.write_text("   ", encoding="utf-8")
            delivery = FakeDelivery()
            service = ArticleProcessingService(
                settings=settings,
                analyzer=ArticleAnalyzer(settings.llm),
                delivery=delivery,
                state=ProcessingState(settings.database_path),
            )

            processed_count = service.process_pending_articles()

            self.assertEqual(1, processed_count)
            self.assertFalse(article_path.exists())
            self.assertTrue((settings.failed_dir / "empty.txt").exists())
            self.assertEqual([], delivery.sent_articles)
            self.assertFalse(settings.outbox_dir.exists())


if __name__ == "__main__":

    unittest.main()
