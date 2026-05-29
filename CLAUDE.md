# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

All Python invocations go through `uv` — never call `python` or `pytest` directly.

```bash
uv run pytest                         # full suite (coverage gate: 84%)
uv run pytest tests/test_store.py     # one file
uv run pytest tests/test_store.py::test_save_entries_persists  # one test
uv run pytest -k "duplicate"          # match by substring
uv run ruff check src tests           # lint
uv run ruff format src tests          # format
uv run pbook <subcommand>             # CLI

export PBOOK_DATABASE_URL=postgresql+psycopg://user:pass@host:5432/pbook  # Supabase/Postgres DSN
uv run pbook migrate                  # create the schema (runs Alembic against PBOOK_DATABASE_URL)
uv run pbook worker                   # start the Temporal worker on pbook-task-queue
```

The store is PostgreSQL (with the `pgvector` extension), e.g. a Supabase project. `PBOOK_DATABASE_URL` is the single source of truth for which DB is used; `postgres://`/`postgresql://` URLs are auto-coerced to the `postgresql+psycopg` driver. For Supabase, use a direct/session connection (port 5432) and append `?sslmode=require`. Setting `PBOOK_DATABASE_URL=""` (or leaving it unset) disables the store.

`pytest` runs with `asyncio_mode = "auto"` and a session-scoped event loop. `tests/conftest.py` spins up an ephemeral local PostgreSQL cluster for the session (see `tests/_pgcluster.py`), migrates one database, and per test truncates the tables and points `PBOOK_DATABASE_URL` at it — tests never touch the developer's real database. The local server needs the pgvector extension (`apt-get install postgresql-16-pgvector`); set `PBOOK_TEST_DATABASE_URL` to run against an existing Postgres+pgvector instead. Engines are disposed after every test.

`sax-llm` is a git dependency pinned to a release tag in `[tool.uv.sources]` (currently `rev = "v0.1.0"` against `github.com/stevegsax/sax-llm`). Local edits to a `../sax-llm` checkout are no longer picked up — to change `sax-llm` types or providers, cut a new tag there and bump the pin with `uv add "sax-llm @ git+https://github.com/stevegsax/sax-llm.git@<tag>"`, or temporarily switch the source to an editable path for local iteration.

## Architecture

pbook is a knowledge playbook service: it stores curated advice and LLM-extracted "pitfalls" tagged for retrieval into other agents' contexts. Three things define the shape of the codebase.

**Temporal worker on its own queue.** All orchestration runs as Temporal workflows on `pbook-task-queue` (see `src/pbook/worker.py`). Workflows live in `src/pbook/workflows/`, activities in `src/pbook/activities/`. Clients call pbook via cross-queue workflow execution — they never share the queue. The `TranscriptIngestionWorkflow` is the exception: it runs on `forge-task-queue` (forge-side) and calls back into `pbook-task-queue` for extraction. When adding a new workflow, register it in `worker.py` alongside its activities, or it won't be reachable.

**Function Core / Imperative Shell, enforced.** Every module separates pure logic from I/O. Examples: `store.build_entry_dict` (pure) vs `store.save_entries` (I/O); `activities/retrieval.rank_and_pack` (pure) vs `activities/retrieval.fetch_candidates` (I/O). Tests exercise the pure functions directly — they don't mock the database. Keep this split when adding code: a pure function the test can import and call beats a method that requires fixture setup.

**Pluggable LLM provider via `pbook.llm`.** `pbook/llm.py` holds a global `_provider` registered via `set_provider()`; the generic chat activity calls `get_provider()`. The worker registers a `sax-llm` provider at startup. Tests inject mock providers. Activities that don't need an LLM (list, get, approve, prune candidate detection) must not call `get_provider()` so they stay testable without a mock.

**Generic LLM/embedding workflow steps via `pbook.workflow_steps`.** Every LLM call goes through `llm_chat` (structured-output chat) or `llm_embed` (text-to-vector) — see `src/pbook/workflow_steps/`. Workflows resolve their model via `pbook.models.resolve_model()` in workflow body, build prompts (pure functions in `src/pbook/prompts/`) via `workflow.unsafe.imports_passed_through()`, call `llm_chat` with an `output_type_name` registered at worker startup (`_register_output_types()`), and validate the returned `tool_input` against their own Pydantic class. When adding a new structured output type, register it in `pbook/worker.py::_register_output_types()` or `llm_chat` raises `KeyError`.

### Data model essentials

One `entries` table holds both `pitfall` (extracted) and `curated` (human-submitted) entries — `entry_type` is the discriminator. Tags are namespaced with a controlled vocabulary (`lang:`, `lib:`, `domain:`, `project:`, `pattern:`); see `src/pbook/tags.py` for valid values. Tag validation is enforced on the CLI write path; LLM-extracted tags are tolerated even if imperfect. Each entry stores a `pgvector` embedding (`embedding vector(1536)`) used for semantic deduplication (via the cosine distance operator `<=>`, backed by an HNSW index) and the `MaintenanceWorkflow`'s consolidation pass. The code passes embeddings around as float32 `bytes` (the base64 wire format across Temporal activities); `store.py` converts to/from `vector` at the DB boundary (`pbook.embeddings.bytes_to_vector` / `vector_to_bytes`).

`needs_review=True` is "optimistic review": LLM-extracted entries are visible by default; consumers who don't want them pass `approved_only=True` to retrieval. There is no separate staging table.

The DB connection comes from `$PBOOK_DATABASE_URL` (a PostgreSQL DSN, e.g. a Supabase connection string). Setting it to `""` — or leaving it unset — disables the store entirely (some CLI commands exit with an error).

### Retrieval modes

`RetrievalInput.mode` is `CREATE` (boost general knowledge: `lang:`, `lib:`, `domain:`) or `FIX` (boost project-specific pitfalls: `project:`, `pattern:`). Mode reweights ranking only — it never filters. The retrieval workflow packs ranked candidates within a token budget (default 5,000) and records which entries were served so feedback (`pbook feedback`) can later boost or sink them.

### Quality bar (load-bearing)

The extraction prompt is built around: **better to extract nothing than to extract a misleading entry.** Generic advice ("use proper error handling") is rejected; only the unexpected-and-actionable signal counts. When changing extraction or review prompts (`src/pbook/activities/extraction.py`, `src/pbook/activities/review.py`, `src/pbook/ingestion_prompts.py`), preserve this constraint — relaxing it for any one case will degrade the playbook globally.

## Authoritative documentation

Source-of-truth design notes live in `design/` (OVERVIEW, DECISIONS, DATA_MODEL, WORKFLOWS, CLI, INTEGRATION). Read them before changing architecture; update them in the same change as the code.

## Diataxis Documentation

The `diataxis/` directory contains generated, human-facing documentation built with Hugo. It is an output artifact — disposable and never authoritative. Do not use it as input for design decisions, code generation, or development work. If the code and the diataxis docs disagree, the code is right.
