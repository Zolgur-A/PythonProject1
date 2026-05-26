from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SETTINGS_PATH = PROJECT_ROOT / "config" / "settings.json"
DEFAULT_PROMPTS_PATH = PROJECT_ROOT / "config" / "prompts.json"


@dataclass(frozen=True)
class LlmSettings:
    provider: str
    api_key: str
    model: str
    base_url: str


@dataclass(frozen=True)
class TelegramSettings:
    enabled: bool
    bot_token: str
    chat_ids: list[str]


@dataclass(frozen=True)
class EmailSettings:
    enabled: bool
    smtp_host: str
    smtp_port: int
    username: str
    password: str
    from_address: str
    to_addresses: list[str]


@dataclass(frozen=True)
class AppSettings:
    article_input_dir: Path
    outbox_dir: Path
    processed_dir: Path
    failed_dir: Path
    database_path: Path
    run_once: bool
    poll_interval_seconds: int
    llm: LlmSettings
    telegram: TelegramSettings
    email: EmailSettings


@dataclass(frozen=True)
class AnalysisPrompt:
    prompt_id: str
    title: str
    question: str


def read_json_file(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Configuration file not found: {path}")
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def resolve_project_path(value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return PROJECT_ROOT / path


def load_settings(path: Path = DEFAULT_SETTINGS_PATH) -> AppSettings:
    raw = read_json_file(path)
    llm = raw.get("llm", {})
    telegram = raw.get("telegram", {})
    email = raw.get("email", {})

    return AppSettings(
        article_input_dir=resolve_project_path(str(raw["article_input_dir"])),
        outbox_dir=resolve_project_path(str(raw.get("outbox_dir", "data/outbox"))),
        processed_dir=resolve_project_path(str(raw["processed_dir"])),
        failed_dir=resolve_project_path(str(raw["failed_dir"])),
        database_path=resolve_project_path(str(raw["database_path"])),
        run_once=bool(raw.get("run_once", True)),
        poll_interval_seconds=int(raw.get("poll_interval_seconds", 60)),
        llm=LlmSettings(
            provider=str(llm.get("provider", "stub")),
            api_key=str(llm.get("api_key", "")),
            model=str(llm.get("model", "")),
            base_url=str(llm.get("base_url", "")),
        ),
        telegram=TelegramSettings(
            enabled=bool(telegram.get("enabled", False)),
            bot_token=str(telegram.get("bot_token", "")),
            chat_ids=[str(chat_id) for chat_id in telegram.get("chat_ids", [])],
        ),
        email=EmailSettings(
            enabled=bool(email.get("enabled", False)),
            smtp_host=str(email.get("smtp_host", "smtp.office365.com")),
            smtp_port=int(email.get("smtp_port", 587)),
            username=str(email.get("username", "")),
            password=str(email.get("password", "")),
            from_address=str(email.get("from_address", "")),
            to_addresses=[str(address) for address in email.get("to_addresses", [])],
        ),
    )


def load_prompts(path: Path = DEFAULT_PROMPTS_PATH) -> list[AnalysisPrompt]:
    raw = read_json_file(path)
    prompts = []
    for item in raw.get("prompts", []):
        prompts.append(
            AnalysisPrompt(
                prompt_id=str(item["id"]),
                title=str(item["title"]),
                question=str(item["question"]),
            )
        )
    if not prompts:
        raise ValueError("At least one analysis prompt is required")
    return prompts
