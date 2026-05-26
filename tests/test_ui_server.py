import unittest
from unittest.mock import patch

from app.config import AnalysisPrompt, AppSettings, EmailSettings, LlmSettings, TelegramSettings
from app.ui_server import (
    enrich_article_for_ui,
    parse_prompts,
    prompts_to_text,
    render_page,
    send_digest_from_ui,
)


class UiServerTestCase(unittest.TestCase):
    def test_parse_prompts_supports_title_question_lines(self):
        prompts = parse_prompts("Резюме: Сделай резюме\nВыдели риски")

        self.assertEqual(2, len(prompts))
        self.assertEqual("Резюме", prompts[0].title)
        self.assertEqual("Сделай резюме", prompts[0].question)
        self.assertEqual("Промт 2", prompts[1].title)
        self.assertEqual("Выдели риски", prompts[1].question)

    def test_prompts_to_text_serializes_existing_prompts(self):
        prompts = [AnalysisPrompt("summary", "Резюме", "Сделай резюме")]

        result = prompts_to_text(prompts)

        self.assertEqual("Резюме: Сделай резюме", result)

    @patch("app.ui_server.load_settings")
    def test_enrich_article_for_ui_uses_demo_analyzer(self, load_settings_mock):
        load_settings_mock.return_value = make_settings(email_enabled=False)
        prompts = [AnalysisPrompt("summary", "Резюме", "Сделай резюме")]

        result = enrich_article_for_ui("Статья про AI", prompts)

        self.assertIn("Статья про AI", result)
        self.assertIn("Краткая справка по письму", result)
        self.assertIn("Демо-справка", result)


    def test_render_page_has_send_email_button_and_editable_result(self):
        result = render_page("Статья", "Резюме: Сделай резюме", "Дайджест", "Готово")

        self.assertIn("Отправить дайджест на почту", result)
        self.assertIn("Краткая справка по письму через LLM", result)
        self.assertIn('name="email_text"', result)

        self.assertIn("API-ключ LLM", result)
        self.assertIn('name="api_key"', result)
        self.assertIn('name="action" value="send_email"', result)
        self.assertIn('name="result"', result)
        self.assertIn("Дайджест", result)


    @patch("app.ui_server.EmailSender")
    @patch("app.ui_server.load_settings")
    def test_send_digest_from_ui_sends_email(self, load_settings_mock, email_sender_mock):
        load_settings_mock.return_value = make_settings(email_enabled=True)

        send_digest_from_ui("Готовый дайджест")

        email_sender_mock.return_value.send.assert_called_once_with(
            "Дайджест: краткая справка по письму",

            "Готовый дайджест",
        )

    @patch("app.ui_server.load_settings")
    def test_send_digest_from_ui_requires_enabled_email(self, load_settings_mock):
        load_settings_mock.return_value = make_settings(email_enabled=False)

        with self.assertRaisesRegex(ValueError, "email.enabled"):
            send_digest_from_ui("Готовый дайджест")


def make_settings(email_enabled: bool) -> AppSettings:
    return AppSettings(
        article_input_dir="",
        outbox_dir="",
        processed_dir="",
        failed_dir="",
        database_path="",
        run_once=True,
        poll_interval_seconds=60,
        llm=LlmSettings(provider="demo", api_key="", model="", base_url=""),
        telegram=TelegramSettings(enabled=False, bot_token="", chat_ids=[]),
        email=EmailSettings(
            enabled=email_enabled,
            smtp_host="smtp.office365.com",
            smtp_port=587,
            username="user@example.com",
            password="password",
            from_address="user@example.com",
            to_addresses=["manager@example.com"],
        ),
    )


if __name__ == "__main__":
    unittest.main()
