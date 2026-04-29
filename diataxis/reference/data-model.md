+++
title = "Data Model Reference"
weight = 94
description = "Entry types, Pydantic models, and database schema"
topic = "data-model"
covers = ["PlaybookEntry model with all fields (including embedding, feedback counters, rejected, rejection_reason)", "FeedbackInput model", "PushExperienceInput model", "RetrievalInput (with query, threshold, include_rejected) and RetrievalResult (with similarity per entry) models", "EntryType enum values", "Database schema (entries table with embedding, feedback counters, rejected/rejection_reason)", "entry_sources table (provenance: session_id, project_name, experience_hash, source_context, source_context_embedding)", "Ingested sessions tracking table (ingested_sessions)", "SessionInfo model for transcript discovery", "JSON output contract (parsed tags, ISO 8601 datetimes, error envelope)"]
detail = "Tabular. Field name, type, default, description for each model."
+++
All models are Pydantic `BaseModel` subclasses defined in `pbook.models`.

## Entry types

`EntryType` is a `StrEnum` with two values:

| Value     | Description                                      |
|-----------|--------------------------------------------------|
| `pitfall` | Extracted from experience -- unexpected and actionable |
| `curated` | Human-submitted general advice                   |

## PlaybookEntry

The universal write model for all entry types.

| Field             | Type           | Default    | Description                                      |
|-------------------|----------------|------------|--------------------------------------------------|
| `title`           | `str`          | required   | Short descriptive title                          |
| `content`         | `str`          | required   | Entry body                                       |
| `tags`            | `list[str]`    | `[]`       | Namespaced tags (see [Tag System Reference](tags/))  |
| `entry_type`      | `EntryType`    | `curated`  | Content type discriminator                       |
| `source_project`  | `str`          | `""`       | Project that generated this entry                |
| `source_task_id`  | `str`          | `""`       | Task ID that generated this entry                |
| `needs_review`    | `bool`         | `False`    | Whether the entry awaits human review            |
| `helpful_count`   | `int`          | `0`        | Times marked helpful via feedback                |
| `harmful_count`   | `int`          | `0`        | Times marked harmful via feedback                |
| `retrieval_count` | `int`          | `0`        | Times served in retrieval results                |
| `embedding`       | `bytes \| None` | `None`    | Vector embedding (float32 blob) for semantic search |
| `rejected`        | `bool`         | `False`    | Soft-rejection flag; default queries hide rejected entries |
| `rejection_reason`| `str \| None`  | `None`     | Optional reason captured by `pbook reject --reason`        |

### Example: pitfall

```json
{"title": "OTel set_tracer_provider uses set-once guard", "content": "Reset _done under _lock in tests.", "tags": ["lib:opentelemetry"], "entry_type": "pitfall", "source_project": "forge"}
```

### Example: curated

```json
{"title": "Use WAL mode for SQLite concurrency", "content": "Enable WAL with PRAGMA journal_mode=WAL.", "tags": ["lib:sqlalchemy", "domain:database"], "entry_type": "curated"}
```

For usage examples, see [How to Manage Entries](/howto/manage-entries/). For tag namespace definitions, see [Tag System Reference](tags/).

## FeedbackInput

Input for recording feedback on a retrieved entry.

| Field            | Type   | Default  | Description                              |
|------------------|--------|----------|------------------------------------------|
| `entry_id`       | `int`  | required | ID of the entry to give feedback on      |
| `helpful`        | `bool` | required | `True` for helpful, `False` for harmful  |
| `source_project` | `str`  | `""`     | Project context for the feedback         |
| `context`        | `str`  | `""`     | Why the entry was helpful or harmful     |

For how feedback affects ranking, see [Retrieval Ranking](/explanation/retrieval-ranking/). For the CLI command, see [pbook feedback](cli/#pbook-feedback).

## PushExperienceInput

Input for pushing raw experience data to the extraction path.

| Field      | Type   | Default  | Description                              |
|------------|--------|----------|------------------------------------------|
| `project`  | `str`  | required | Project that generated this experience   |
| `problem`  | `str`  | required | What unexpected situation occurred       |
| `resolution` | `str` | required | How it was resolved                     |
| `context`  | `str`  | `""`     | Relevant context (code, errors, etc.)    |
| `metadata` | `dict` | `{}`     | Arbitrary key-value pairs                |

## RetrievalInput

Input for the retrieval workflow.

| Field              | Type            | Default   | Description                                                                            |
|--------------------|-----------------|-----------|----------------------------------------------------------------------------------------|
| `tags`             | `list[str]`     | `[]`      | Tags to match against entries                                                          |
| `mode`             | `RetrievalMode` | `CREATE`  | `CREATE` boosts general knowledge and API docs; `FIX` boosts project-specific pitfalls |
| `token_budget`     | `int`           | `5000`    | Maximum tokens for packed results                                                      |
| `project`          | `str`           | `""`      | Filter by source project                                                               |
| `approved_only`    | `bool`          | `False`   | Exclude entries with `needs_review=True`                                               |
| `query`            | `str`           | `""`      | Free-text query; ranks results semantic-primary when non-empty                         |
| `threshold`        | `float`         | `0.0`     | Drop matches below this cosine similarity (only meaningful when `query` is set)        |
| `include_rejected` | `bool`          | `False`   | Include soft-rejected entries (excluded by default)                                    |

When `query` is non-empty, the workflow embeds the query via the `llm_embed` activity, computes cosine similarity per candidate in the `compute_similarities` activity, and ranks **semantic-primary** with tag/mode score as tiebreaker. When `query` is empty, ranking falls back to the legacy tag-overlap + mode-boost score (forge consumers keep working unchanged).

## RetrievalResult

Output from the retrieval workflow.

| Field              | Type         | Description                                                       |
|--------------------|--------------|-------------------------------------------------------------------|
| `entries`          | `list[dict]` | Ranked and packed entry dicts                                     |
| `token_count`      | `int`        | Total estimated tokens in packed entries                          |
| `total_candidates` | `int`        | Number of candidates before ranking                               |

When the input `query` was non-empty, each entry dict in `entries` carries an additional `similarity: float` field (cosine similarity in `[0.0, 1.0]`). When the input was tag-only, no `similarity` key is set.

For practical retrieval examples, see [How to Retrieve Entries](/howto/retrieve-entries/). For how scoring and ranking work, see [Retrieval Ranking](/explanation/retrieval-ranking/).

## Database schema

The `entries` table stores all playbook entries. Tags are stored as a JSON array string in `tags_json`.

```sql
CREATE TABLE entries (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    title            VARCHAR  NOT NULL,
    content          TEXT     NOT NULL,
    tags_json        TEXT     NOT NULL,
    entry_type       VARCHAR  NOT NULL DEFAULT 'curated',
    source_project   VARCHAR  NOT NULL DEFAULT '',
    source_task_id   VARCHAR  NOT NULL DEFAULT '',
    needs_review     BOOLEAN  NOT NULL DEFAULT 0,
    helpful_count    INTEGER  NOT NULL DEFAULT 0,
    harmful_count    INTEGER  NOT NULL DEFAULT 0,
    retrieval_count  INTEGER  NOT NULL DEFAULT 0,
    embedding        BLOB,
    rejected         BOOLEAN  NOT NULL DEFAULT 0,
    rejection_reason TEXT,
    created_at       DATETIME DEFAULT (CURRENT_TIMESTAMP),
    updated_at       DATETIME DEFAULT (CURRENT_TIMESTAMP)
);

CREATE INDEX ix_entries_source_project ON entries (source_project);
CREATE INDEX ix_entries_entry_type ON entries (entry_type);
```

The `embedding` column stores a float32 vector as a binary blob, generated by the `llm_embed` activity using OpenAI's `text-embedding-3-small` model. It is used for semantic duplicate detection, similarity-ranked retrieval, and the maintenance consolidation pass.

The feedback counter columns (`helpful_count`, `harmful_count`, `retrieval_count`) track how entries perform after retrieval. `retrieval_count` is incremented automatically each time the entry is served in a retrieval result. `helpful_count` and `harmful_count` are incremented via the `pbook feedback` command. These counters feed into the [retrieval ranking algorithm](/explanation/retrieval-ranking/).

The `rejected` and `rejection_reason` columns record soft-rejection state. `pbook reject` sets `rejected=true` and persists the optional reason instead of deleting the row. Default queries (`pbook list`, retrieval, semantic dedup) filter `rejected=true`; pass `--include-rejected` (CLI) or `RetrievalInput.include_rejected=True` (workflow) to surface them.

## entry_sources table

The `entry_sources` table records the originating Claude Code sessions and situations that produced each entry. Granularity is per-experience: one row per (entry, experience). A single session can contribute many distinct situations to the same entry.

```sql
CREATE TABLE entry_sources (
    id                       INTEGER PRIMARY KEY AUTOINCREMENT,
    entry_id                 INTEGER NOT NULL REFERENCES entries(id) ON DELETE CASCADE,
    session_id               TEXT    NOT NULL DEFAULT '',
    project_name             TEXT    NOT NULL DEFAULT '',
    experience_hash          TEXT,
    source_context           TEXT    NOT NULL DEFAULT '',
    source_context_embedding BLOB,
    created_at               DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    UNIQUE (entry_id, session_id, experience_hash)
);

CREATE INDEX ix_entry_sources_session_id ON entry_sources (session_id);
CREATE INDEX ix_entry_sources_entry_id   ON entry_sources (entry_id);
```

| Field                       | Description                                                                                                              |
|-----------------------------|--------------------------------------------------------------------------------------------------------------------------|
| `entry_id`                  | FK to `entries.id`. Cascade-delete: deleting an entry drops its source rows                                              |
| `session_id`                | Claude Code session UUID; matches the `.jsonl` file's stem in `~/.claude/projects/`                                      |
| `project_name`              | Display-friendly project name (e.g. `forge`, `pbook`)                                                                    |
| `experience_hash`           | `sha256(problem + resolution + context)`; nullable for future manual-attribution rows                                    |
| `source_context`            | Rich situation excerpt forge captured during analysis — used by "discuss this playbook" flows                                |
| `source_context_embedding`  | Float32 embedding of `source_context`; for ad-hoc analysis only — **not** consumed by retrieval ranking                  |
| `created_at`                | When the row was written                                                                                                 |

The `UNIQUE (entry_id, session_id, experience_hash)` constraint makes re-ingestion idempotent: identical experiences hash to the same value and the second insert is a no-op (`ON CONFLICT DO NOTHING`). The match-or-attach extraction path enforces an additional source-context dedup: a new row is skipped when its `source_context_embedding` is within `0.92` cosine similarity of an existing row on the same entry.

Use `pbook sources <id> --json` to fetch all source rows for an entry (the CLI strips `source_context_embedding` from the output). For end-to-end "discuss this playbook" composition, see [Use as Skill Substrate](/howto/use-as-skill-substrate/).

Database path resolution order:

1. `PBOOK_DB_PATH` environment variable
2. `$XDG_STATE_HOME/pbook/pbook.db`
3. `~/.local/state/pbook/pbook.db`

Setting `PBOOK_DB_PATH` to an empty string disables the store.

## SessionInfo

`SessionInfo` is a Pydantic `BaseModel` defined in `pbook.transcript`, used for session discovery when scanning Claude Code JSONL transcript files.

| Field             | Type  | Description                                   |
|-------------------|-------|-----------------------------------------------|
| `path`            | `str` | Absolute path to the JSONL session file       |
| `session_id`      | `str` | Session UUID (filename stem)                  |
| `project_dir_name`| `str` | Claude Code project directory name            |
| `project_name`    | `str` | Inferred project name (last path segment)     |
| `size_bytes`      | `int` | File size in bytes                            |

For how to discover and ingest sessions, see [How to Ingest Transcripts](/howto/ingest-transcripts/).

## ingested_sessions table

The `ingested_sessions` table tracks the lifecycle of every Claude Code session submitted to ingestion: pending, in-progress, completed, or errored. It also prevents duplicate ingestion of completed sessions.

```sql
CREATE TABLE ingested_sessions (
    session_id        TEXT PRIMARY KEY,
    project_name      TEXT NOT NULL DEFAULT '',
    ingested_at       DATETIME DEFAULT CURRENT_TIMESTAMP,
    experiences_found INTEGER NOT NULL DEFAULT 0,
    entries_created   INTEGER NOT NULL DEFAULT 0,
    status            TEXT NOT NULL DEFAULT 'completed',
    workflow_id       TEXT,
    run_id            TEXT,
    error_message     TEXT,
    started_at        DATETIME
);
```

`session_id` corresponds to the `SessionInfo.session_id` field. `experiences_found` records how many raw experiences were extracted from the transcript, while `entries_created` records how many playbook entries were ultimately created — different because match-or-attach can route a candidate to an existing entry instead of inserting a new one.

`status` is one of `running`, `completed`, or `error`. `pbook ingest` seeds the row as `running` on submission, the workflow's success callback flips it to `completed`, and forge's failure callback flips it to `error` (with `error_message` populated). `workflow_id` and `run_id` link back to the Temporal execution; `started_at` is the submission timestamp, while `ingested_at` is the most recent state transition. `pbook sessions --json` exposes all of these.

For the ingestion workflow, see [How to Ingest Transcripts](/howto/ingest-transcripts/). For session lifecycle troubleshooting, see [Use as Skill Substrate](/howto/use-as-skill-substrate/) (the discuss workflow consumes session metadata).

## JSON output contract

Every CLI command that takes `--json` follows the same conventions:

| Aspect            | Rule                                                                                       |
|-------------------|--------------------------------------------------------------------------------------------|
| Tag fields        | Emitted as a parsed `tags: list[str]`, never the raw `tags_json` column                    |
| Datetimes         | ISO 8601 with timezone (`"2026-04-29T12:34:56+00:00"`)                                     |
| Binary embeddings | Stripped from output (`embedding`, `source_context_embedding` never appear in JSON)        |
| Errors            | Written to **stdout** as `{"error": "...", "code": "..."}` with non-zero exit              |

The `code` field is the canonical place to branch in shell pipelines:

```
not_found            Entry, session, or other resource does not exist
validation_error     Input failed schema or argument validation
tag_invalid          One or more tags failed namespaced-tag validation
db_disabled          PBOOK_DB_PATH is empty (store disabled)
worker_unavailable   Workflow submission failed (Temporal worker not running)
session_file_missing Transcript JSONL not found on disk
```

Without `--json`, errors go to stderr and the exit code remains the only signal. Skill consumers should always pass `--json` so success and failure flow through one parseable stream.