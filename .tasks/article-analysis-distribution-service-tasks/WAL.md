# WAL: Email Summary Agent

## Read Order

Future sessions must read in this order:

1. `AGENTS.md`
2. `.tasks/article-analysis-distribution-service-tasks/WAL.md`
3. `.tasks/article-analysis-distribution-service-tasks/PLAN.md`
4. `Arcitecture.py`

## Current Phase

Email summary agent MVP: IN PROGRESS.

## Product Goal

Build a local Windows-friendly MVP of the `Arcitecture.py` target pipeline: ingest email-like files, normalize them, summarize with an LLM using editable prompts, save a short structured brief, and optionally deliver it to Telegram/email recipients.

## Hard Constraints

- Must run on the user's Windows laptop.
- Startup must remain available from Windows-suitable files.
- Do not require heavy databases; use local files and/or SQLite only.
- Keep secrets outside source code.
- Do not modify `.venv/`, `.git/`, or IDE files unless explicitly requested.

## Implemented Architecture Slice

- Manual/on-demand MVP from `Arcitecture.py` stage 1.
- Input files: `.txt` and `.eml` in `data/inbox/`.
- Normalization layer: `app/email_processing.py` creates a unified email representation with subject, sender, recipients, body and attachment metadata.
- Summarization prompts: `config/prompts.json` now targets summary, key facts, actions/deadlines, risks and attachments.
- Rendered briefs: `data/outbox/*.md` with email metadata, original body, attachments and structured LLM answers.
- Processed source files: moved to `data/processed/`.
- Failed source files: moved to `data/failed/`.
- Local state: SQLite file `data/service.sqlite3` prevents duplicate processing by normalized input hash.

## Provider Decisions

- Supported LLM providers remain: `stub`, `deepseek`, `ollama`, `veai`.
- If no usable LLM API is configured, deterministic local JSON-like stub responses keep the pipeline testable.
- Missing Telegram/email credentials must not crash processing.

## Known Gaps vs Full `Arcitecture.py`

- No Gmail API, Microsoft Graph, IMAP polling, webhooks or real queue yet.
- No PDF/DOCX/OCR extraction yet; `.eml` text attachments are listed and plain text may be extracted.
- No PostgreSQL/object storage; local files and SQLite only by current hard constraint.
- No production audit log beyond logging and SQLite idempotency.

## Open Questions for User

1. Which mailbox/provider should be implemented first: Gmail, Microsoft 365 Graph, IMAP, or local Outlook automation?
2. Should the next mode be manual upload UI, polling inbox folder, or real email connector?
3. Which attachment types are mandatory first: PDF, DOCX, XLSX, PNG/JPG OCR, EML?
4. Should delivery go to Telegram, email digest, dashboard/UI, or all of them?

## Next Recommended Step

Run tests, then process a sample `.txt` or `.eml` file from `data/inbox/`. Next implementation step: add a real mail connector or attachment extraction module based on the user's chosen provider.
