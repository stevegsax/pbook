# CLI Reference

All commands are subcommands of `pbook`.

## pbook worker

Start the Temporal worker.

```
pbook worker [--temporal-address ADDR]
```

| Name                 | Type   | Default          | Description              |
|----------------------|--------|------------------|--------------------------|
| `--temporal-address` | string | `localhost:7233` | Temporal server address  |

```
pbook worker --temporal-address localhost:7233
```

For a guided introduction, see [Getting Started](../tutorials/getting-started.md).

## pbook list

List playbook entries.

```
pbook list [--tag TAG]... [--type TYPE] [--project PROJECT] [--limit N] [--json]
```

| Name        | Type    | Default | Description                                |
|-------------|---------|---------|--------------------------------------------|
| `--tag`     | string  | (none)  | Filter by tag; repeatable, OR match        |
| `--type`    | string  | `""`    | Filter by entry type                       |
| `--project` | string  | `""`    | Filter by source project                   |
| `--limit`   | integer | `20`    | Maximum entries to return                  |
| `--json`    | flag    | off     | Machine-readable JSON output               |

```
pbook list --tag lang:python --tag domain:testing --limit 5
```

For querying strategies, see [How to Retrieve Entries](../howto/retrieve-entries.md). For how tags affect ranking, see [Retrieval Ranking](../explanation/retrieval-ranking.md).

## pbook get

Get a single entry by ID.

```
pbook get ENTRY_ID [--json]
```

| Name       | Type    | Default | Description                  |
|------------|---------|---------|------------------------------|
| `ENTRY_ID` | integer | required | Entry primary key           |
| `--json`   | flag    | off     | Machine-readable JSON output |

```
pbook get 42 --json
```

## pbook add

Add a playbook entry from a JSON file.

```
pbook add --file FILE [--schema]
```

| Name       | Type | Default | Description                          |
|------------|------|---------|--------------------------------------|
| `--file`   | path | (none)  | JSON file containing a PlaybookEntry |
| `--schema` | flag | off     | Print the PlaybookEntry JSON schema and exit |

```
pbook add --file entry.json
```

For workflow context, see [How to Manage Entries](../howto/manage-entries.md). For field definitions, see [Data Model Reference](data-model.md).

## pbook update

Update an existing entry by ID.

```
pbook update ENTRY_ID --file FILE
```

| Name       | Type    | Default  | Description                        |
|------------|---------|----------|------------------------------------|
| `ENTRY_ID` | integer | required | Entry primary key                 |
| `--file`   | path    | required | JSON file with fields to update   |

```
pbook update 42 --file updates.json
```

## pbook approve

Clear the `needs_review` flag on an entry.

```
pbook approve ENTRY_ID
```

| Name       | Type    | Default  | Description          |
|------------|---------|----------|----------------------|
| `ENTRY_ID` | integer | required | Entry primary key   |

```
pbook approve 42
```

For the review workflow, see [How to Manage Entries](../howto/manage-entries.md). For why entries need review, see [Understanding the Quality Bar](../explanation/quality-bar.md).

## pbook reject

Delete an entry (reject it).

```
pbook reject ENTRY_ID
```

| Name       | Type    | Default  | Description          |
|------------|---------|----------|----------------------|
| `ENTRY_ID` | integer | required | Entry primary key   |

```
pbook reject 42
```

## pbook check-duplicate

Check for duplicate entries matching a title.

```
pbook check-duplicate --title TITLE [--tag TAG]...
```

| Name      | Type   | Default  | Description                              |
|-----------|--------|----------|------------------------------------------|
| `--title` | string | required | Title to match (case-insensitive LIKE)   |
| `--tag`   | string | (none)   | Tags to refine duplicate ranking; repeatable |

```
pbook check-duplicate --title "WAL mode" --tag lib:sqlalchemy
```

## pbook push

Push experience data for LLM extraction via Temporal.

```
pbook push --file FILE [--temporal-address ADDR]
```

| Name                 | Type   | Default          | Description                                |
|----------------------|--------|------------------|--------------------------------------------|
| `--file`             | path   | required         | JSON file with PushExperienceInput data; accepts a single object or an array |
| `--temporal-address` | string | `localhost:7233` | Temporal server address                    |

```
pbook push --file experience.json
```

For experience data guidelines, see [How to Push Experience](../howto/push-experience.md). For input field definitions, see [Data Model Reference](data-model.md).

## pbook ingest

Ingest Claude session transcripts into the playbook via Temporal.

```
pbook ingest [TRANSCRIPT_PATH] [--all] [--project PROJECT] [--min-size N] [--dry-run] [--force] [--temporal-address ADDR]
```

| Name                 | Type    | Default          | Description                                |
|----------------------|---------|------------------|--------------------------------------------|
| `TRANSCRIPT_PATH`   | path    | (none)           | Path to a single JSONL session file        |
| `--all`              | flag    | off              | Discover and ingest all sessions           |
| `--project`          | string  | `""`             | Filter by project (with `--all`) or override |
| `--min-size`         | integer | `10240`          | Minimum session file size in bytes         |
| `--dry-run`          | flag    | off              | Show sessions/stats without ingesting      |
| `--force`            | flag    | off              | Reprocess already-ingested sessions        |
| `--temporal-address` | string  | `localhost:7233` | Temporal server address                    |

```
pbook ingest --all --dry-run
pbook ingest --all
pbook ingest --all --project forge
pbook ingest ~/.claude/projects/<id>/session.jsonl
```

For the ingestion workflow, see [How to Ingest Transcripts](../howto/ingest-transcripts.md). For how ingestion fits into the system, see [Architecture](../explanation/architecture.md).

## pbook review

List entries needing review.

```
pbook review [--limit N]
```

| Name      | Type    | Default | Description                    |
|-----------|---------|---------|--------------------------------|
| `--limit` | integer | `20`    | Maximum entries to show        |

```
pbook review --limit 10
```

## pbook feedback

Record feedback on a retrieved entry. Increments the entry's `helpful_count` or `harmful_count`, which affects future [retrieval ranking](../explanation/retrieval-ranking.md).

```
pbook feedback ENTRY_ID (--helpful | --harmful) [--context TEXT]
```

| Name        | Type    | Default  | Description                              |
|-------------|---------|----------|------------------------------------------|
| `ENTRY_ID`  | integer | required | Entry primary key                        |
| `--helpful` | flag    | (none)   | Mark as helpful; mutually exclusive with `--harmful` |
| `--harmful` | flag    | (none)   | Mark as harmful; mutually exclusive with `--helpful` |
| `--context` | string  | `""`     | Why the entry was helpful or harmful     |

Exactly one of `--helpful` or `--harmful` is required.

```
pbook feedback 42 --helpful
pbook feedback 7 --harmful --context "Advice was outdated for v2 API"
```

For how feedback affects scoring, see [Retrieval Ranking](../explanation/retrieval-ranking.md). For the input model, see [Data Model Reference](data-model.md#feedbackinput).

## pbook prune

Identify entries that should be reviewed for removal. Entries are flagged if they are consistently harmful (harmful ratio exceeds 50% after 5+ retrievals) or never retrieved and older than 180 days.

```
pbook prune (--dry-run | --apply) [--min-retrievals N] [--max-harmful-ratio F] [--max-stale-days N]
```

| Name                   | Type    | Default | Description                                      |
|------------------------|---------|---------|--------------------------------------------------|
| `--dry-run`            | flag    | (none)  | List candidates without changing anything        |
| `--apply`              | flag    | (none)  | Mark candidates with `needs_review=True` and tag `pattern:prune-candidate` |
| `--min-retrievals`     | integer | `5`     | Minimum retrievals before harmful ratio applies  |
| `--max-harmful-ratio`  | float   | `0.5`   | Harmful ratio threshold                          |
| `--max-stale-days`     | integer | `180`   | Days before unretrieved entry is considered stale |

Exactly one of `--dry-run` or `--apply` is required. Pruning never deletes entries -- it marks them for human review.

```
pbook prune --dry-run
pbook prune --apply --min-retrievals 3 --max-harmful-ratio 0.6
```

For the quality review workflow, see [How to Manage Entries](../howto/manage-entries.md).

## pbook migrate

Run database migrations.

```
pbook migrate
```

No options. Runs Alembic migrations to head on the resolved database path.

```
pbook migrate
```

## pbook skill-prompt

Print server-provided instructions for a skill operation (stub -- not yet implemented).

```
pbook skill-prompt [--operation OP]
```

| Name          | Type   | Default | Description                    |
|---------------|--------|---------|--------------------------------|
| `--operation` | string | `add`   | Operation to get instructions for |

```
pbook skill-prompt --operation add
```

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Error (invalid input, entry not found, store disabled, validation failure) |
| 2 | Usage error (missing required options, unknown command) |

Error messages are written to stderr. Normal output goes to stdout.
