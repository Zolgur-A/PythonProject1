from __future__ import annotations

import importlib
import json
import os
import urllib.error
import urllib.request
from urllib.parse import urlparse

from app.config import AnalysisPrompt, LlmSettings


DEMO_PROVIDER = "demo"
STUB_PROVIDER = "stub"
DEEPSEEK_PROVIDER = "deepseek"
OLLAMA_PROVIDER = "ollama"
VEAI_PROVIDER = "veai"
DEEPSEEK_API_KEY_ENV = "DEEPSEEK_API_KEY"
DEEPSEEK_CHAT_COMPLETIONS_URL = "https://api.deepseek.com/chat/completions"
DEFAULT_DEEPSEEK_MODEL = "deepseek-chat"
DEFAULT_OLLAMA_MODEL = "hhao/qwen2.5-coder-tools"
DEFAULT_VEAI_MODEL = "veai-current"
DEFAULT_OLLAMA_BASE_URL = "http://localhost:11434"
DEFAULT_VEAI_BASE_URL = "http://127.0.0.1:8765"
OLLAMA_CHAT_ENDPOINT = "/api/chat"
OPENAI_CHAT_COMPLETIONS_ENDPOINT = "/chat/completions"
OPENAI_V1_CHAT_COMPLETIONS_ENDPOINT = "/v1/chat/completions"
REQUEST_TIMEOUT_SECONDS = 60
PERCENT_SIGN = "%"
SYSTEM_PROMPT = (
    "Ты ассистент для кратких справок по письмам и вложениям. "
    "Отвечай по-русски, кратко, структурно, без выдумывания фактов. "
    "Выделяй summary, key_points, action_items, deadlines, risks, confidence "
    "и needs_human_review. Если данных в письме недостаточно, явно напиши об этом."
)



class ArticleAnalyzer:
    def __init__(self, settings: LlmSettings) -> None:
        self._settings = settings

    def answer_prompt(self, article_text: str, prompt: AnalysisPrompt) -> str:
        provider = self._settings.provider or DEMO_PROVIDER
        if provider == DEMO_PROVIDER:
            return self._demo_answer(article_text, prompt)
        if provider == VEAI_PROVIDER:
            return self._veai_answer(article_text, prompt)
        if provider == STUB_PROVIDER:
            return self._stub_answer(article_text, prompt)
        if provider == DEEPSEEK_PROVIDER:
            return self._deepseek_answer(article_text, prompt)
        if provider == OLLAMA_PROVIDER:
            return self._ollama_answer(article_text, prompt)
        raise NotImplementedError(
            f"LLM provider '{provider}' is not implemented yet. "
            "Use provider 'demo', 'veai', 'stub', 'deepseek' or 'ollama'."
        )

    def _deepseek_answer(self, article_text: str, prompt: AnalysisPrompt) -> str:
        api_key = self._get_deepseek_api_key()
        payload = self._build_deepseek_payload(article_text, prompt)
        response_payload = self._post_json(
            DEEPSEEK_CHAT_COMPLETIONS_URL,
            payload,
            {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            "DeepSeek API",
        )
        return self._extract_openai_compatible_answer(response_payload, "DeepSeek")

    def _ollama_answer(self, article_text: str, prompt: AnalysisPrompt) -> str:
        try:
            return self._ollama_python_client_answer(article_text, prompt)
        except ImportError:
            return self._ollama_http_answer(article_text, prompt)

    def _ollama_python_client_answer(self, article_text: str, prompt: AnalysisPrompt) -> str:
        ollama_module = importlib.import_module("ollama")
        response = ollama_module.chat(
            model=self._settings.model or DEFAULT_OLLAMA_MODEL,
            messages=self._build_messages(article_text, prompt),
        )
        return self._extract_ollama_python_client_answer(response)

    def _ollama_http_answer(self, article_text: str, prompt: AnalysisPrompt) -> str:
        payload = self._build_ollama_payload(article_text, prompt)
        response_payload = self._post_json(
            self._get_ollama_chat_url(),
            payload,
            {"Content-Type": "application/json"},
            "Ollama API",
        )
        return self._extract_ollama_answer(response_payload)

    def _veai_answer(self, article_text: str, prompt: AnalysisPrompt) -> str:
        payload = self._build_veai_payload(article_text, prompt)
        headers = {"Content-Type": "application/json"}
        if self._settings.api_key:
            headers["Authorization"] = f"Bearer {self._settings.api_key}"

        last_error: RuntimeError | None = None
        for url in self._get_veai_chat_urls():
            try:
                response_payload = self._post_json(url, payload, headers, "VEAI local HTTP")
                return self._extract_openai_compatible_answer(response_payload, "VEAI")
            except RuntimeError as error:
                last_error = error
                if "HTTP error 404" not in str(error):
                    break

        endpoint_hint = ", ".join(self._get_veai_chat_urls())
        raise RuntimeError(
            f"VEAI request was not completed. Tried endpoints: {endpoint_hint}. Last error: {last_error}"
        )

    def _get_deepseek_api_key(self) -> str:
        api_key = self._settings.api_key or os.getenv(DEEPSEEK_API_KEY_ENV, "")
        if not api_key:
            raise RuntimeError(
                "DeepSeek API key is not configured. "
                f"Set {DEEPSEEK_API_KEY_ENV} or config/settings.json llm.api_key."
            )
        return api_key

    def _get_ollama_chat_url(self) -> str:
        base_url = (self._settings.base_url or DEFAULT_OLLAMA_BASE_URL).rstrip("/")
        return f"{base_url}{OLLAMA_CHAT_ENDPOINT}"

    def _get_veai_chat_url(self) -> str:
        return self._get_veai_chat_urls()[0]

    def _get_veai_chat_urls(self) -> list[str]:
        base_url = (self._settings.base_url or DEFAULT_VEAI_BASE_URL).rstrip("/")
        parsed = urlparse(base_url)
        if parsed.path.endswith(OPENAI_CHAT_COMPLETIONS_ENDPOINT):
            return [base_url]
        return [
            f"{base_url}{OPENAI_V1_CHAT_COMPLETIONS_ENDPOINT}",
            f"{base_url}{OPENAI_CHAT_COMPLETIONS_ENDPOINT}",
        ]

    def _build_deepseek_payload(self, article_text: str, prompt: AnalysisPrompt) -> dict[str, object]:
        model = self._settings.model or DEFAULT_DEEPSEEK_MODEL
        return self._build_openai_compatible_payload(model, article_text, prompt)

    def _build_ollama_payload(self, article_text: str, prompt: AnalysisPrompt) -> dict[str, object]:
        model = self._settings.model or DEFAULT_OLLAMA_MODEL
        return {
            "model": model,
            "messages": self._build_messages(article_text, prompt),
            "stream": False,
        }

    def _build_veai_payload(self, article_text: str, prompt: AnalysisPrompt) -> dict[str, object]:
        model = self._settings.model or DEFAULT_VEAI_MODEL
        return self._build_openai_compatible_payload(model, article_text, prompt)

    @staticmethod
    def _build_openai_compatible_payload(
        model: str,
        article_text: str,
        prompt: AnalysisPrompt,
    ) -> dict[str, object]:
        return {
            "model": model,
            "messages": ArticleAnalyzer._build_messages(article_text, prompt),
            "stream": False,
        }

    @staticmethod
    def _build_messages(article_text: str, prompt: AnalysisPrompt) -> list[dict[str, str]]:
        user_prompt = (
            f"Нормализованное письмо:\n{article_text.strip()}\n\n"
            f"Задача анализа:\n{prompt.question}\n\n"
            "Формат ответа: валидный JSON с полями summary_1_2_sentences, important_facts, "
            "action_items, deadlines, attachments_summary, risks, confidence, needs_human_review."
        )

        return [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]

    @staticmethod
    def _post_json(
        url: str,
        payload: dict[str, object],
        headers: dict[str, str],
        provider_name: str,
    ) -> dict[str, object]:
        request = urllib.request.Request(
            url,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
                response_payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            details = error.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"{provider_name} HTTP error {error.code}: {details}") from error
        except urllib.error.URLError as error:
            raise RuntimeError(
                f"{provider_name} connection error: {error.reason}. Check endpoint: {url}."
            ) from error
        if not isinstance(response_payload, dict):
            raise RuntimeError(f"{provider_name} response is not a JSON object")
        return response_payload

    @staticmethod
    def _extract_deepseek_answer(response_payload: dict[str, object]) -> str:
        return ArticleAnalyzer._extract_openai_compatible_answer(response_payload, "DeepSeek")

    @staticmethod
    def _extract_openai_compatible_answer(response_payload: dict[str, object], provider_name: str) -> str:
        choices = response_payload.get("choices")
        if not isinstance(choices, list) or not choices:
            raise RuntimeError(f"{provider_name} API response does not contain choices")
        first_choice = choices[0]
        if not isinstance(first_choice, dict):
            raise RuntimeError(f"{provider_name} API response choice has invalid format")
        message = first_choice.get("message")
        if not isinstance(message, dict):
            raise RuntimeError(f"{provider_name} API response message has invalid format")
        content = message.get("content")
        if not isinstance(content, str) or not content.strip():
            raise RuntimeError(f"{provider_name} API response content is empty")
        return content.strip()

    @staticmethod
    def _extract_ollama_answer(response_payload: dict[str, object]) -> str:
        message = response_payload.get("message")
        if not isinstance(message, dict):
            raise RuntimeError("Ollama API response message has invalid format")
        content = message.get("content")
        if not isinstance(content, str) or not content.strip():
            raise RuntimeError("Ollama API response content is empty")
        return content.strip()

    @staticmethod
    def _extract_ollama_python_client_answer(response: object) -> str:
        message = getattr(response, "message", None)
        content = getattr(message, "content", None)
        if isinstance(content, str) and content.strip():
            return content.strip()
        if isinstance(response, dict):
            dict_message = response.get("message")
            if isinstance(dict_message, dict):
                dict_content = dict_message.get("content")
                if isinstance(dict_content, str) and dict_content.strip():
                    return dict_content.strip()
        raise RuntimeError("Ollama Python client response content is empty")

    @staticmethod
    def _extract_answer(response_payload: dict[str, object]) -> str:
        return ArticleAnalyzer._extract_deepseek_answer(response_payload)

    @staticmethod
    def _demo_answer(article_text: str, prompt: AnalysisPrompt) -> str:
        compact_text = " ".join(article_text.split())
        has_deadline = any(marker in compact_text.lower() for marker in ("срок", "дедлайн", "до "))
        has_attachment = "Вложения:" in article_text and "нет вложений" not in article_text.lower()
        confidence = "средний" if compact_text else "низкий"
        return json.dumps(
            {
                "summary_1_2_sentences": f"Демо-справка по промту '{prompt.title}': письмо требует управленческой оценки.",
                "important_facts": ["Найден текст письма для анализа."],
                "action_items": ["Проверить факты и назначить владельца следующего действия."],
                "deadlines": ["В письме есть возможный срок."] if has_deadline else [],
                "attachments_summary": "Есть вложения." if has_attachment else "Вложения не указаны.",
                "risks": ["Демо-режим не заменяет проверку исходного письма."],
                "confidence": confidence,
                "needs_human_review": True,
            },
            ensure_ascii=False,
        )


    @staticmethod
    def _stub_answer(article_text: str, prompt: AnalysisPrompt) -> str:
        compact_text = " ".join(article_text.split())
        excerpt = compact_text[:180] if compact_text else "нет текста письма"
        return json.dumps(
            {
                "summary_1_2_sentences": f"Локальная тестовая справка: {excerpt}",
                "important_facts": [],
                "action_items": [],
                "deadlines": [],
                "attachments_summary": "Не анализировалось внешней LLM.",
                "risks": [],
                "confidence": "низкий",
                "needs_human_review": True,
                "prompt_question": prompt.question,
            },
            ensure_ascii=False,
        )

