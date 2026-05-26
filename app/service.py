from __future__ import annotations

import logging
import shutil
import time
from pathlib import Path

from app.config import AppSettings, load_prompts, load_settings
from app.delivery import DeliveryService, EmailSender, TelegramSender
from app.email_processing import is_supported_input_file, load_normalized_email
from app.llm import ArticleAnalyzer
from app.rendering import PromptAnswer, render_enriched_email_summary
from app.state import ProcessingState


LOGGER = logging.getLogger(__name__)
UTF8_ENCODING = "utf-8"



class ArticleProcessingService:
    def __init__(
        self,
        settings: AppSettings,
        analyzer: ArticleAnalyzer,
        delivery: DeliveryService,
        state: ProcessingState,
    ) -> None:
        self._settings = settings
        self._analyzer = analyzer
        self._delivery = delivery
        self._state = state
        self._prompts = load_prompts()

    def run(self) -> None:
        self._ensure_directories()
        while True:
            processed_count = self.process_pending_articles()
            LOGGER.info("Processing cycle finished. Emails processed: %s", processed_count)

            if self._settings.run_once:
                return
            time.sleep(self._settings.poll_interval_seconds)

    def process_pending_articles(self) -> int:
        processed_count = 0
        input_files = sorted(
            source_path
            for source_path in self._settings.article_input_dir.iterdir()
            if is_supported_input_file(source_path)
        )
        for article_path in input_files:
            try:
                self._process_article(article_path)
                processed_count += 1
            except Exception:
                LOGGER.exception("Failed to process email input: %s", article_path)
                self._move_file(article_path, self._settings.failed_dir)

        return processed_count

    def _process_article(self, article_path: Path) -> None:
        normalized_email = load_normalized_email(article_path)
        analysis_text = normalized_email.to_analysis_text()
        if not normalized_email.has_extractable_content():
            LOGGER.warning("Skipping email input without extractable content: %s", article_path)

            self._move_file(article_path, self._settings.failed_dir)
            return
        if self._state.has_processed(analysis_text):
            LOGGER.info("Skipping duplicate email input: %s", article_path)
            self._move_file(article_path, self._settings.processed_dir)
            return

        answers = [
            PromptAnswer(
                title=prompt.title,
                question=prompt.question,
                answer=self._analyzer.answer_prompt(analysis_text, prompt),
            )
            for prompt in self._prompts
        ]
        enriched_article = render_enriched_email_summary(normalized_email, answers)
        self._save_outbox_article(article_path, enriched_article)
        self._delivery.send_article(normalized_email.subject, enriched_article)
        self._state.mark_processed(article_path, analysis_text)
        self._move_file(article_path, self._settings.processed_dir)


    def _ensure_directories(self) -> None:
        directories = [
            self._settings.article_input_dir,
            self._settings.outbox_dir,
            self._settings.processed_dir,
            self._settings.failed_dir,
            self._settings.database_path.parent,
        ]
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)

    def _save_outbox_article(self, source_path: Path, enriched_article: str) -> Path:
        self._settings.outbox_dir.mkdir(parents=True, exist_ok=True)
        outbox_path = self._settings.outbox_dir / f"{source_path.stem}.md"
        if outbox_path.exists():
            outbox_path = self._settings.outbox_dir / f"{source_path.stem}-{int(time.time())}.md"
        outbox_path.write_text(enriched_article, encoding=UTF8_ENCODING)
        LOGGER.info("Saved enriched article to outbox: %s", outbox_path)
        return outbox_path

    @staticmethod
    def _move_file(source_path: Path, target_dir: Path) -> None:

        target_dir.mkdir(parents=True, exist_ok=True)
        target_path = target_dir / source_path.name
        if target_path.exists():
            target_path = target_dir / f"{source_path.stem}-{int(time.time())}{source_path.suffix}"
        shutil.move(str(source_path), str(target_path))


def build_service() -> ArticleProcessingService:
    settings = load_settings()
    analyzer = ArticleAnalyzer(settings.llm)
    delivery = DeliveryService(
        telegram=TelegramSender(settings.telegram),
        email=EmailSender(settings.email),
    )
    state = ProcessingState(settings.database_path)
    return ArticleProcessingService(settings, analyzer, delivery, state)
