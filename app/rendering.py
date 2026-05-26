from __future__ import annotations

from dataclasses import dataclass

from app.email_processing import NormalizedEmail


@dataclass(frozen=True)
class PromptAnswer:
    title: str
    question: str
    answer: str


SUMMARY_HEADER = "## Краткая справка по письму"
ANALYSIS_HEADER = "## Структурированный анализ LLM"
ATTACHMENTS_HEADER = "## Вложения"
NO_ATTACHMENTS_TEXT = "Вложений нет."


def render_enriched_article(article_text: str, answers: list[PromptAnswer]) -> str:
    email = NormalizedEmail(
        subject="Ручной текст",
        sender="unknown",
        recipients=[],
        body_text=article_text,
        source_name="manual.txt",
    )
    return render_enriched_email_summary(email, answers)


def render_enriched_email_summary(email: NormalizedEmail, answers: list[PromptAnswer]) -> str:
    sections = [
        SUMMARY_HEADER,
        f"**Тема:** {email.subject}",
        f"**Отправитель:** {email.sender}",
        f"**Получатели:** {', '.join(email.recipients) if email.recipients else 'unknown'}",
        f"**Источник:** {email.source_name}",
        "",
        "### Текст письма",
        email.body_text.rstrip(),
        "",
        ATTACHMENTS_HEADER,
        _render_attachments(email),
        "",
        ANALYSIS_HEADER,
    ]
    for answer in answers:
        sections.append(
            "\n".join(
                [
                    f"### {answer.title}",
                    f"**Промт:** {answer.question}",
                    f"**Ответ:** {answer.answer}",
                ]
            )
        )
    return "\n".join(sections).rstrip() + "\n"


def _render_attachments(email: NormalizedEmail) -> str:
    if not email.attachments:
        return NO_ATTACHMENTS_TEXT
    lines = []
    for attachment in email.attachments:
        lines.append(f"- {attachment.filename} ({attachment.content_type}, {attachment.size_bytes} bytes)")
        if attachment.extracted_text:
            lines.append(f"  - Извлечённый текст: {attachment.extracted_text}")
    return "\n".join(lines)
