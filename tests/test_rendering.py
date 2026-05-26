import unittest

from app.email_processing import NormalizedEmail
from app.rendering import PromptAnswer, render_enriched_email_summary


class RenderingTestCase(unittest.TestCase):
    def test_render_enriched_email_summary_appends_prompt_answers(self):
        email = NormalizedEmail(
            subject="Согласование договора",
            sender="sender@example.com",
            recipients=["user@example.com"],
            body_text="Нужно согласовать договор до пятницы.",
            source_name="contract.eml",
        )
        answers = [
            PromptAnswer(
                title="Задачи и сроки",
                question="Есть ли задачи?",
                answer="Согласовать договор до пятницы.",
            )
        ]

        result = render_enriched_email_summary(email, answers)

        self.assertIn("Согласование договора", result)
        self.assertIn("## Краткая справка по письму", result)
        self.assertIn("## Структурированный анализ LLM", result)
        self.assertIn("### Задачи и сроки", result)
        self.assertIn("Согласовать договор", result)



if __name__ == "__main__":
    unittest.main()
