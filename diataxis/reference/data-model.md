# Data Model Reference

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
| `tags`            | `list[str]`    | `[]`       | Namespaced tags (see [Tag System Reference](tags.md))  |
| `entry_type`      | `EntryType`    | `curated`  | Content type discriminator                       |
| `source_project`  | `str`          | `""`       | Project that generated this entry                |
| `source_task_id`  | `str`          | `""`       | Task ID that generated this entry                |
| `needs_review`    | `bool`         | `False`    | Whether the entry awaits human review            |
| `helpful_count`   | `int`          | `0`        | Times marked helpful via feedback                |
| `harmful_count`   | `int`          | `0`        | Times marked harmful via feedback                |
| `retrieval_count` | `int`          | `0`        | Times served in retrieval results                |
| `embedding`       | `bytes \| None` | `None`     | Vector embedding (float32 blob) for semantic search |

### Example: pitfall

```json
{"title": "OTel set_tracer_provider uses set-once guard", "content": "Reset _done under _lock in tests.", "tags": ["lib:opentelemetry"], "entry_type": "pitfall", "source_project": "forge"}
```

### Example: curated

```json
{"title": "Use WAL mode for SQLite concurrency", "content": "Enable WAL with PRAGMA journal_mode=WAL.", "tags": ["lib:sqlalchemy", "domain:database"], "entry_type": "curated"}
```

For usage examples, see [How to Manage Entries](../howto/manage-entries.md). For tag namespace definitions, see [Tag System Reference](tags.md).

## FeedbackInput

Input for recording feedback on a retrieved entry.

| Field            | Type   | Default  | Description                              |
|------------------|--------|----------|------------------------------------------|
| `entry_id`       | `int`  | required | ID of the entry to give feedback on      |
| `helpful`        | `bool` | required | `True` for helpful, `False` for harmful  |
| `source_project` | `str`  | `""`     | Project context for the feedback         |
| `context`        | `str`  | `""`     | Why the entry was helpful or harmful     |

For how feedback affects ranking, see [Retrieval Ranking](../explanation/retrieval-ranking.md). For the CLI command, see [pbook feedback](cli.md#pbook-feedback).

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

| Field           | Type            | Default   | Description                             |
|-----------------|-----------------|-----------|-----------------------------------------|
| `tags`          | `list[str]`     | `[]`      | Tags to match against entries           |
| `mode`          | `RetrievalMode` | `CREATE`  | `CREATE` boosts general knowledge and API docs; `FIX` boosts project-specific pitfalls |
| `token_budget`  | `int`           | `5000`    | Maximum tokens for packed results       |
| `project`       | `str`           | `""`      | Filter by source project                |
| `approved_only` | `bool`          | `False`   | Exclude entries with `needs_review=True` |

## RetrievalResult

Output from the retrieval workflow.

| Field              | Type         | Description                              |
|--------------------|--------------|------------------------------------------|
| `entries`          | `list[dict]` | Ranked and packed entry dicts            |
| `token_count`      | `int`        | Total estimated tokens in packed entries |
| `total_candidates` | `int`        | Number of candidates before ranking      |

For practical retrieval examples, see [How to Retrieve Entries](../howto/retrieve-entries.md). For how scoring and ranking work, see [Retrieval Ranking](../explanation/retrieval-ranking.md).

## Database schema

The `entries` table stores all playbook entries. Tags are stored as a JSON array string in `tags_json`.

```sql
CREATE TABLE entries (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    title           VARCHAR  NOT NULL,
    content         TEXT     NOT NULL,
    tags_json       TEXT     NOT NULL,
    entry_type      VARCHAR  NOT NULL DEFAULT 'curated',
    source_project  VARCHAR  NOT NULL DEFAULT '',
    source_task_id  VARCHAR  NOT NULL DEFAULT '',
    needs_review    BOOLEAN  NOT NULL DEFAULT 0,
    helpful_count   INTEGER  NOT NULL DEFAULT 0,
    harmful_count   INTEGER  NOT NULL DEFAULT 0,
    retrieval_count INTEGER  NOT NULL DEFAULT 0,
    embedding       BLOB,
    created_at      DATETIME DEFAULT (CURRENT_TIMESTAMP),
    updated_at      DATETIME DEFAULT (CURRENT_TIMESTAMP)
);

CREATE INDEX ix_entries_source_project ON entries (source_project);
CREATE INDEX ix_entries_entry_type ON entries (entry_type);
```

The `embedding` column stores a float32 vector as a binary blob, generated by the `compute_embedding` activity using OpenAI's `text-embedding-3-small` model. It is used for semantic duplicate detection and similarity search.

The feedback counter columns (`helpful_count`, `harmful_count`, `retrieval_count`) track how entries perform after retrieval. `retrieval_count` is incremented automatically each time the entry is served in a retrieval result. `helpful_count` and `harmful_count` are incremented via the `pbook feedback` command. These counters feed into the [retrieval ranking algorithm](../explanation/retrieval-ranking.md).

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

For how to discover and ingest sessions, see [How to Ingest Transcripts](../howto/ingest-transcripts.md).

## ingested_sessions table

The `ingested_sessions` table tracks which Claude Code sessions have been processed, preventing duplicate ingestion.

```sql
CREATE TABLE ingested_sessions (
    session_id      TEXT PRIMARY KEY,
    project_name    TEXT NOT NULL DEFAULT '',
    ingested_at     DATETIME DEFAULT CURRENT_TIMESTAMP,
    experiences_found INTEGER NOT NULL DEFAULT 0,
    entries_created   INTEGER NOT NULL DEFAULT 0
);
```

`session_id` corresponds to the `SessionInfo.session_id` field. `experiences_found` records how many raw experiences were extracted from the transcript, while `entries_created` records how many playbook entries were ultimately created. This distinction captures cases where extraction finds experiences but deduplication or filtering prevents entry creation.

For the ingestion workflow, see [How to Ingest Transcripts](../howto/ingest-transcripts.md).
