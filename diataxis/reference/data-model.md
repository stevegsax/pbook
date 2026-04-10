# Data Model Reference

All models are Pydantic `BaseModel` subclasses defined in `pbook.models`.

## Entry types

`EntryType` is a `StrEnum` with three values:

| Value     | Description                                      |
|-----------|--------------------------------------------------|
| `pitfall` | Extracted from experience -- unexpected and actionable |
| `curated` | Human-submitted general advice                   |
| `api_doc` | Library documentation record                     |

## PlaybookEntry

The universal write model for all entry types.

| Field            | Type        | Default    | Description                                      |
|------------------|-------------|------------|--------------------------------------------------|
| `title`          | `str`       | required   | Short descriptive title                          |
| `content`        | `str`       | required   | Entry body; for `api_doc` entries, holds serialized `ApiDocRecord` JSON |
| `tags`           | `list[str]` | `[]`       | Namespaced tags (see [Tag System Reference](tags.md))  |
| `entry_type`     | `EntryType` | `curated`  | Content type discriminator                       |
| `source_project` | `str`       | `""`       | Project that generated this entry                |
| `source_task_id` | `str`       | `""`       | Task ID that generated this entry                |
| `needs_review`   | `bool`      | `False`    | Whether the entry awaits human review            |

### Example: pitfall

```json
{"title": "OTel set_tracer_provider uses set-once guard", "content": "Reset _done under _lock in tests.", "tags": ["lib:opentelemetry"], "entry_type": "pitfall", "source_project": "forge"}
```

### Example: curated

```json
{"title": "Use WAL mode for SQLite concurrency", "content": "Enable WAL with PRAGMA journal_mode=WAL.", "tags": ["lib:sqlalchemy", "domain:database"], "entry_type": "curated"}
```

### Example: api_doc

```json
{"title": "sqlalchemy.create_engine", "content": "{\"library\": \"sqlalchemy\", \"method\": \"sqlalchemy.create_engine\", \"summary\": \"Create a new Engine instance.\", \"signature\": \"create_engine(url, **kwargs) -> Engine\"}", "tags": ["lib:sqlalchemy"], "entry_type": "api_doc"}
```

For usage examples, see [How to Manage Entries](../howto/manage-entries.md). For tag namespace definitions, see [Tag System Reference](tags.md).

## ApiDocRecord

Structured API documentation for a single library method. Stored as the `content` of a `PlaybookEntry` with `entry_type=api_doc`.

| Field       | Type        | Default  | Description                              |
|-------------|-------------|----------|------------------------------------------|
| `library`   | `str`       | required | Library name (e.g. `sqlalchemy`)         |
| `method`    | `str`       | required | Fully qualified method (e.g. `sqlalchemy.create_engine`) |
| `summary`   | `str`       | required | 1-2 sentence description                |
| `signature` | `str`       | required | Method signature with type hints         |
| `examples`  | `list[str]` | `[]`     | Usage examples                           |
| `doc_url`   | `str`       | `""`     | Link to official documentation           |

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
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    title          VARCHAR  NOT NULL,
    content        TEXT     NOT NULL,
    tags_json      TEXT     NOT NULL,
    entry_type     VARCHAR  NOT NULL DEFAULT 'curated',
    source_project VARCHAR  NOT NULL DEFAULT '',
    source_task_id VARCHAR  NOT NULL DEFAULT '',
    needs_review   BOOLEAN  NOT NULL DEFAULT 0,
    created_at     DATETIME DEFAULT (CURRENT_TIMESTAMP),
    updated_at     DATETIME DEFAULT (CURRENT_TIMESTAMP)
);

CREATE INDEX ix_entries_source_project ON entries (source_project);
CREATE INDEX ix_entries_entry_type ON entries (entry_type);
```

Database path resolution order:

1. `PBOOK_DB_PATH` environment variable
2. `$XDG_STATE_HOME/pbook/pbook.db`
3. `~/.local/state/pbook/pbook.db`

Setting `PBOOK_DB_PATH` to an empty string disables the store.
