from __future__ import annotations

import html
import logging
import urllib.parse
from dataclasses import replace
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from app.config import AnalysisPrompt, AppSettings, load_prompts, load_settings
from app.delivery import EmailSender
from app.llm import ArticleAnalyzer
from app.rendering import PromptAnswer, render_enriched_article



LOGGER = logging.getLogger(__name__)
HOST = "127.0.0.1"
PORT = 8080
FORM_ACTION = "action"
FORM_API_KEY = "api_key"
FORM_EMAIL_TEXT = "email_text"

FORM_PROMPTS = "prompts"
FORM_RESULT = "result"
ACTION_ENRICH = "enrich"
ACTION_SEND_EMAIL = "send_email"
DIGEST_EMAIL_SUBJECT = "Дайджест: краткая справка по письму"
UTF8 = "utf-8"
DEFAULT_EMAIL_TEXT = (
    "Коллеги, прошу подготовить краткую справку по договору, "
    "выделить риски и прислать комментарии до пятницы."
)



class UiServer:
    def __init__(self, host: str = HOST, port: int = PORT) -> None:
        self._host = host
        self._port = port

    def run(self) -> None:
        server = ThreadingHTTPServer((self._host, self._port), UiRequestHandler)
        LOGGER.info("UI is available at http://%s:%s", self._host, self._port)
        server.serve_forever()


class UiRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        prompts = load_prompts()
        self._send_html(render_page(DEFAULT_EMAIL_TEXT, prompts_to_text(prompts), "", ""))


    def do_POST(self) -> None:
        content_length = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(content_length).decode(UTF8)
        form = urllib.parse.parse_qs(raw_body, keep_blank_values=True)
        action = form.get(FORM_ACTION, [ACTION_ENRICH])[0]
        api_key = form.get(FORM_API_KEY, [""])[0].strip()
        email_text = form.get(FORM_EMAIL_TEXT, [""])[0].strip()

        prompts_text = form.get(FORM_PROMPTS, [""])[0]
        result = form.get(FORM_RESULT, [""])[0]
        status = ""

        try:
            prompts = parse_prompts(prompts_text)
            if action == ACTION_SEND_EMAIL:
                if not result.strip():
                    result = enrich_article_for_ui(email_text, prompts, api_key)
                send_digest_from_ui(result)

                status = "Дайджест успешно отправлен на почту."
            else:
                result = enrich_article_for_ui(email_text, prompts, api_key)
                status = "Краткая справка по письму сформирована."

        except Exception as error:
            LOGGER.exception("UI action failed")
            status = f"Ошибка: {error}"

        self._send_html(render_page(email_text, prompts_text, result, status))


    def log_message(self, format: str, *args: object) -> None:
        LOGGER.info("UI request: " + format, *args)

    def _send_html(self, body: str) -> None:
        encoded_body = body.encode(UTF8)
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded_body)))
        self.end_headers()
        self.wfile.write(encoded_body)


def prompts_to_text(prompts: list[AnalysisPrompt]) -> str:
    return "\n".join(f"{prompt.title}: {prompt.question}" for prompt in prompts)


def parse_prompts(prompts_text: str) -> list[AnalysisPrompt]:
    prompts = []
    for index, line in enumerate(prompts_text.splitlines(), start=1):
        clean_line = line.strip()
        if not clean_line:
            continue
        if ":" in clean_line:
            title, question = clean_line.split(":", 1)
            title = title.strip() or f"Промт {index}"
            question = question.strip()
        else:
            title = f"Промт {index}"
            question = clean_line
        if question:
            prompts.append(
                AnalysisPrompt(
                    prompt_id=f"ui_prompt_{index}",
                    title=title,
                    question=question,
                )
            )
    if not prompts:
        raise ValueError("Добавьте хотя бы один промт")
    return prompts


def enrich_article_for_ui(
    email_text: str,

    prompts: list[AnalysisPrompt],
    api_key: str = "",
) -> str:
    if not email_text.strip():
        raise ValueError("Добавьте текст письма")

    settings = load_settings()
    llm_settings = settings.llm
    if api_key:
        llm_settings = replace(llm_settings, api_key=api_key)
    analyzer = ArticleAnalyzer(llm_settings)
    answers = [
        PromptAnswer(
            title=prompt.title,
            question=prompt.question,
            answer=analyzer.answer_prompt(email_text, prompt),

        )
        for prompt in prompts
    ]
    return render_enriched_article(email_text, answers)



def send_digest_from_ui(digest_text: str) -> None:
    if not digest_text.strip():
        raise ValueError("Нет текста дайджеста для отправки")
    settings = load_settings()
    validate_email_settings(settings)
    EmailSender(settings.email).send(DIGEST_EMAIL_SUBJECT, digest_text)


def validate_email_settings(settings: AppSettings) -> None:
    email = settings.email
    required_values = [
        email.smtp_host,
        email.username,
        email.password,
        email.from_address,
    ]
    if not email.enabled:
        raise ValueError("Включите email.enabled в config/settings.json")
    if not all(required_values) or not email.to_addresses:
        raise ValueError("Заполните SMTP-настройки и получателей в config/settings.json")


def render_page(email_text: str, prompts: str, result: str, status: str) -> str:

    escaped_status = html.escape(status)
    return f"""<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <title>Email Summary Agent</title>

  <style>
    body {{ font-family: Arial, sans-serif; margin: 24px; background: #f6f7f9; color: #1f2933; }}
    h1 {{ margin-top: 0; }}
    form {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }}
    label {{ font-weight: 700; display: block; margin-bottom: 8px; }}
    input, textarea {{ width: 100%; box-sizing: border-box; padding: 12px; border: 1px solid #ccd2dc; border-radius: 8px; font-family: Consolas, monospace; }}
    textarea {{ min-height: 280px; }}
    .wide {{ grid-column: 1 / 3; }}
    .result {{ min-height: 360px; background: #ffffff; }}
    .actions {{ display: flex; gap: 12px; align-items: center; }}
    button {{ padding: 12px 20px; border: 0; border-radius: 8px; background: #1d4ed8; color: white; font-weight: 700; cursor: pointer; }}
    button.email {{ background: #047857; }}
    .hint {{ color: #52616f; font-size: 13px; margin-top: 4px; }}
    .status {{ padding: 10px 12px; border-radius: 8px; background: #ffffff; border: 1px solid #ccd2dc; }}
  </style>
</head>
<body>
  <h1>Краткая справка по письму через LLM</h1>

  <form method="post">
    <section class="wide">
      <label for="api_key">API-ключ LLM</label>
      <input id="api_key" name="api_key" type="password" autocomplete="off" placeholder="Вставьте ключ DeepSeek/LLM для текущего запроса">
      <div class="hint">Ключ используется только для текущего запроса и не сохраняется в файлы проекта.</div>
    </section>
    <section>
      <label for="email_text">Исходное письмо или текст вложения</label>
      <textarea id="email_text" name="email_text">{html.escape(email_text)}</textarea>
      <div class="hint">Сюда можно вставить письмо, фрагмент переписки или извлечённый текст вложения.</div>

    </section>
    <section>
      <label for="prompts">Промты для анализа</label>
      <textarea id="prompts" name="prompts">{html.escape(prompts)}</textarea>
      <div class="hint">Формат: Заголовок: вопрос. Можно добавлять строки.</div>
    </section>
    <section class="wide actions">
      <button type="submit" name="action" value="{ACTION_ENRICH}">Сформировать справку</button>

      <button class="email" type="submit" name="action" value="{ACTION_SEND_EMAIL}">Отправить дайджест на почту</button>
      <span class="status">{escaped_status}</span>
    </section>
    <section class="wide">
      <label for="result">Краткая справка перед отправкой</label>

      <textarea class="result" id="result" name="result">{html.escape(result)}</textarea>
      <div class="hint">Этот текст будет отправлен как дайджест. Его можно поправить перед отправкой.</div>
    </section>
  </form>
</body>
</html>"""


def run_ui() -> None:
    UiServer().run()
