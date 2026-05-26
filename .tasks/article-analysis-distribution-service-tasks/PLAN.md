# PLAN: Article Analysis Distribution Service

## Task 01: WAL and Specification

- Create WAL and this plan.
- Capture requirements, constraints, decisions, and open questions.

## Task 02: Integration Requirements

- Use editable JSON files for prompts and settings.
- Keep external providers optional until credentials are configured.
- Start with filesystem input to keep the first version simple.

## Task 03: Local Architecture Without Heavy DB

- Use folders for article flow: `data/inbox`, `data/processed`, `data/failed`.
- Use SQLite from Python standard library for lightweight processing state.
- Use only standard library in the first implementation.

## Task 04: Windows Service Skeleton

- `run_service.bat` starts the service on Windows.
- `main.py` is the main Python entrypoint.
- The implementation is split into small modules under `app/`.

## Task 05: LLM Article Analysis

- `config/prompts.json` contains user-editable prompts.
- Each prompt is applied to each article.
- Without a configured LLM provider, a local stub response is used for safe testing.

## Task 06: Delivery

- Telegram delivery uses Bot API when token/chat ID are configured.
- Outlook/email delivery uses SMTP settings when configured.
- Missing delivery settings do not crash processing.

## Task 07: Tests and Verification

- Add unittest tests for rendering and core pipeline pieces.
- Prefer testable pure functions where possible.
