import unittest
from types import SimpleNamespace

from app.config import AnalysisPrompt, LlmSettings

from app.llm import ArticleAnalyzer


class LlmAnalyzerTestCase(unittest.TestCase):
    def test_build_deepseek_payload_uses_model_and_messages(self):
        analyzer = ArticleAnalyzer(
            LlmSettings(
                provider="deepseek",
                api_key="test-key",
                model="deepseek-chat",
                base_url="",
            )
        )
        prompt = AnalysisPrompt(
            prompt_id="executive_summary",
            title="Краткое резюме",
            question="Сделай резюме для правления.",
        )

        payload = analyzer._build_deepseek_payload("Тестовая статья про AI", prompt)

        self.assertEqual("deepseek-chat", payload["model"])
        self.assertFalse(payload["stream"])
        self.assertEqual("system", payload["messages"][0]["role"])
        self.assertEqual("user", payload["messages"][1]["role"])
        self.assertIn("Тестовая статья про AI", payload["messages"][1]["content"])
        self.assertIn("Сделай резюме для правления", payload["messages"][1]["content"])

    def test_build_ollama_payload_uses_local_model_and_messages(self):
        analyzer = ArticleAnalyzer(
            LlmSettings(
                provider="ollama",
                api_key="",
                model="llama3.1:8b",
                base_url="http://localhost:11434",
            )
        )
        prompt = AnalysisPrompt(
            prompt_id="risk_compliance_security",
            title="Риски",
            question="Выдели риски.",
        )

        payload = analyzer._build_ollama_payload("Текст статьи", prompt)

        self.assertEqual("llama3.1:8b", payload["model"])
        self.assertFalse(payload["stream"])
        self.assertIn("Текст статьи", payload["messages"][1]["content"])
        self.assertIn("Выдели риски", payload["messages"][1]["content"])

    def test_empty_provider_uses_demo_answer(self):
        analyzer = ArticleAnalyzer(
            LlmSettings(
                provider="",
                api_key="",
                model="",
                base_url="",
            )
        )
        prompt = AnalysisPrompt(
            prompt_id="summary",
            title="Резюме",
            question="Сделай резюме.",
        )

        answer = analyzer.answer_prompt("AI повышает эффективность на 20%", prompt)

        self.assertIn("Демо-справка", answer)
        self.assertIn("confidence", answer)


    def test_build_veai_payload_uses_openai_compatible_format(self):
        analyzer = ArticleAnalyzer(
            LlmSettings(
                provider="veai",
                api_key="",
                model="veai-current",
                base_url="http://127.0.0.1:8765",
            )
        )

        prompt = AnalysisPrompt(
            prompt_id="board_questions",
            title="Вопросы",
            question="Сформулируй вопросы.",
        )

        payload = analyzer._build_veai_payload("Статья", prompt)

        self.assertEqual("veai-current", payload["model"])
        self.assertFalse(payload["stream"])
        self.assertEqual("system", payload["messages"][0]["role"])
        self.assertEqual("user", payload["messages"][1]["role"])
        self.assertIn("Сформулируй вопросы", payload["messages"][1]["content"])

    def test_get_ollama_chat_url_uses_configured_base_url(self):
        analyzer = ArticleAnalyzer(
            LlmSettings(
                provider="ollama",
                api_key="",
                model="llama3.1:8b",
                base_url="http://127.0.0.1:11434/",
            )
        )

        self.assertEqual("http://127.0.0.1:11434/api/chat", analyzer._get_ollama_chat_url())

    def test_get_veai_chat_url_uses_configured_base_url(self):
        analyzer = ArticleAnalyzer(
            LlmSettings(
                provider="veai",
                api_key="",
                model="veai-current",
                base_url="http://127.0.0.1:8765/",
            )
        )

        self.assertEqual("http://127.0.0.1:8765/v1/chat/completions", analyzer._get_veai_chat_url())


    def test_extract_deepseek_answer_reads_first_choice_content(self):
        response_payload = {
            "choices": [
                {
                    "message": {
                        "content": "Ответ DeepSeek"
                    }
                }
            ]
        }

        answer = ArticleAnalyzer._extract_deepseek_answer(response_payload)

        self.assertEqual("Ответ DeepSeek", answer)

    def test_extract_openai_compatible_answer_reads_first_choice_content(self):
        response_payload = {
            "choices": [
                {
                    "message": {
                        "content": "Ответ VEAI"
                    }
                }
            ]
        }

        answer = ArticleAnalyzer._extract_openai_compatible_answer(response_payload, "VEAI")

        self.assertEqual("Ответ VEAI", answer)

    def test_extract_ollama_answer_reads_message_content(self):
        response_payload = {"message": {"content": "Ответ Ollama"}}

        answer = ArticleAnalyzer._extract_ollama_answer(response_payload)

        self.assertEqual("Ответ Ollama", answer)

    def test_extract_ollama_python_client_answer_reads_message_content(self):
        response = SimpleNamespace(message=SimpleNamespace(content="Ответ Python Ollama"))

        answer = ArticleAnalyzer._extract_ollama_python_client_answer(response)

        self.assertEqual("Ответ Python Ollama", answer)


if __name__ == "__main__":
    unittest.main()

