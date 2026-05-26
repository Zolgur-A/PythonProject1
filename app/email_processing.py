from __future__ import annotations

from dataclasses import dataclass, field
from email import policy
from email.message import Message

from email.parser import BytesParser
from pathlib import Path


PLAIN_TEXT_CONTENT_TYPE = "text/plain"
HTML_CONTENT_TYPE = "text/html"
ATTACHMENT_DISPOSITION = "attachment"
DEFAULT_UNKNOWN_VALUE = "unknown"
UTF8_ENCODING = "utf-8"
HTML_BREAK_MARKERS = ("<br>", "<br/>", "<br />", "</p>", "</div>")
HTML_BLOCK_MARKERS = ("<p>", "<div>")
SUPPORTED_INPUT_SUFFIXES = (".txt", ".eml")


@dataclass(frozen=True)
class NormalizedAttachment:
    filename: str
    content_type: str
    size_bytes: int
    extracted_text: str = ""


@dataclass(frozen=True)
class NormalizedEmail:
    subject: str
    sender: str
    recipients: list[str]
    body_text: str
    source_name: str
    attachments: list[NormalizedAttachment] = field(default_factory=list)

    def has_extractable_content(self) -> bool:
        return bool(self.body_text.strip() or self._attachment_texts())

    def to_analysis_text(self) -> str:
        attachment_lines = self._format_attachment_lines()
        return "\n".join(

            [
                f"Тема: {self.subject}",
                f"Отправитель: {self.sender}",
                f"Получатели: {', '.join(self.recipients) if self.recipients else DEFAULT_UNKNOWN_VALUE}",
                "",
                "Текст письма:",
                self.body_text.strip(),
                "",
                "Вложения:",
                *attachment_lines,
            ]
        ).strip()

    def _format_attachment_lines(self) -> list[str]:
        if not self.attachments:
            return ["- нет вложений"]
        lines = []
        for attachment in self.attachments:
            lines.append(f"- {attachment.filename} ({attachment.content_type}, {attachment.size_bytes} bytes)")
            if attachment.extracted_text:
                lines.append(f"  Текст вложения: {attachment.extracted_text}")
        return lines

    def _attachment_texts(self) -> list[str]:
        return [attachment.extracted_text for attachment in self.attachments if attachment.extracted_text.strip()]


def load_normalized_email(source_path: Path) -> NormalizedEmail:

    suffix = source_path.suffix.lower()
    if suffix == ".eml":
        return _load_eml_email(source_path)
    return _load_plain_text_email(source_path)


def is_supported_input_file(source_path: Path) -> bool:
    return source_path.is_file() and source_path.suffix.lower() in SUPPORTED_INPUT_SUFFIXES


def _load_plain_text_email(source_path: Path) -> NormalizedEmail:
    body_text = source_path.read_text(encoding=UTF8_ENCODING).strip()
    return NormalizedEmail(
        subject=source_path.stem,
        sender=DEFAULT_UNKNOWN_VALUE,
        recipients=[],
        body_text=body_text,
        source_name=source_path.name,
    )


def _load_eml_email(source_path: Path) -> NormalizedEmail:
    with source_path.open("rb") as file:
        message = BytesParser(policy=policy.default).parse(file)

    body_text = _extract_body_text(message)
    attachments = _extract_attachments(message)
    return NormalizedEmail(
        subject=_header_to_text(message.get("subject")),
        sender=_header_to_text(message.get("from")),
        recipients=_split_recipients(_header_to_text(message.get("to"))),
        body_text=body_text.strip(),
        source_name=source_path.name,
        attachments=attachments,
    )


def _extract_body_text(message: Message) -> str:
    if not message.is_multipart():
        payload = message.get_payload(decode=True)
        content_type = message.get_content_type()
        return _decode_payload(payload, message.get_content_charset(), content_type)

    html_fallback = ""
    for part in message.walk():
        if part.get_content_disposition() == ATTACHMENT_DISPOSITION:
            continue
        content_type = part.get_content_type()
        payload = part.get_payload(decode=True)
        decoded_payload = _decode_payload(payload, part.get_content_charset(), content_type)
        if content_type == PLAIN_TEXT_CONTENT_TYPE and decoded_payload.strip():
            return decoded_payload
        if content_type == HTML_CONTENT_TYPE and decoded_payload.strip() and not html_fallback:
            html_fallback = decoded_payload
    return html_fallback


def _extract_attachments(message: Message) -> list[NormalizedAttachment]:
    attachments: list[NormalizedAttachment] = []
    for part in message.walk():
        if part.get_content_disposition() != ATTACHMENT_DISPOSITION:
            continue
        payload = part.get_payload(decode=True) or b""
        content_type = part.get_content_type()
        filename = part.get_filename() or f"attachment-{len(attachments) + 1}"
        extracted_text = ""
        if content_type == PLAIN_TEXT_CONTENT_TYPE:
            extracted_text = _decode_payload(payload, part.get_content_charset(), content_type)
        attachments.append(
            NormalizedAttachment(
                filename=filename,
                content_type=content_type,
                size_bytes=len(payload),
                extracted_text=extracted_text.strip(),
            )
        )
    return attachments


def _decode_payload(payload: bytes | None, charset: str | None, content_type: str) -> str:
    if not payload:
        return ""
    decoded = payload.decode(charset or UTF8_ENCODING, errors="replace")
    if content_type == HTML_CONTENT_TYPE:
        return _strip_basic_html(decoded)
    return decoded


def _strip_basic_html(value: str) -> str:
    result = value
    for marker in HTML_BREAK_MARKERS:
        result = result.replace(marker, "\n")
    for marker in HTML_BLOCK_MARKERS:
        result = result.replace(marker, "")
    is_inside_tag = False
    characters = []
    for character in result:
        if character == "<":
            is_inside_tag = True
            continue
        if character == ">":
            is_inside_tag = False
            continue
        if not is_inside_tag:
            characters.append(character)
    return "".join(characters)


def _header_to_text(value: object) -> str:
    text = str(value or "").strip()
    return text or DEFAULT_UNKNOWN_VALUE


def _split_recipients(value: str) -> list[str]:
    if value == DEFAULT_UNKNOWN_VALUE:
        return []
    return [recipient.strip() for recipient in value.split(",") if recipient.strip()]
