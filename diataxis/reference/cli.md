+++
title = "CLI Reference"
weight = 104
description = "All pbook commands and their options"
topic = "cli"
covers = ["All pbook commands with synopsis (search, sources, session-text, tags, skill-prompt, plus the existing commands)", "Options, arguments, and defaults for each command", "JSON output contract (parsed tags, ISO 8601 datetimes, error envelope)", "Exit codes"]
detail = "One section per command. Synopsis, options table, example."
+++

All commands are subcommands of `pbook`.

## JSON output contract

Every command that takes `--json` follows the same conventions, so a skill or shell script can parse outputs uniformly.

**Success payloads:**

- `tags` is a parsed list of strings, never the raw `tags_json` column (`["lang:python", "lib:pytest"]`, not `"[\"lang:python\", \"lib:pytest\"]"`).
- Datetimes are ISO 8601 with timezone (`"2026-04-29T12:34:56+00:00"`).
- Binary embedding columns (`embedding`, `source_context_embedding`) are stripped from output.

**Failure payloads:**

When `--json` is set and the command fails, the error envelope is written to **stdout** (not stderr) and the process exits non-zero:

```json
{ "error": "Entry 999 not found.", "code": "not_found" }
```

The `code` field is what callers should branch on. Codes used today:

| Code                       | Meaning                                                             |
|----------------------------|---------------------------------------------------------------------|
| `not_found`                | Entry, session, or other resource does not exist                    |
| `validation_error`         | Input failed schema or argument validation                          |
| `tag_invalid`              | One or more tags failed namespaced-tag validation                   |
| `db_disabled`              | `PBOOK_DB_PATH` is empty (store disabled)                           |
| `worker_unavailable`       | Workflow submission failed (Temporal worker not running)            |
| `session_file_missing`     | Transcript JSONL not found on disk                                  |

Without `--json`, errors go to stderr in human-readable form.

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

For a guided introduction, see [Getting Started](/tutorials/getting-started/).

## pbook list

List playbook entries.

```
pbook list [--tag TAG]... [--type TYPE] [--project PROJECT] [--needs-review] [--include-rejected] [--limit N] [--json]
```

| Name                 | Type    | Default | Description                                          |
|----------------------|---------|---------|------------------------------------------------------|
| `--tag`              | string  | (none)  | Filter by tag; repeatable, OR match                  |
| `--type`             | string  | `""`    | Filter by entry type (`pitfall` or `curated`)        |
| `--project`          | string  | `""`    | Filter by source project                             |
| `--needs-review`     | flag    | off     | Only show entries flagged for review                 |
| `--include-rejected` | flag    | off     | Include soft-rejected entries (excluded by default)  |
| `--limit`            | integer | `20`    | Maximum entries to return                            |
| `--json`             | flag    | off     | Machine-readable JSON output                         |

```
pbook list --tag lang:python --tag domain:testing --json --limit 5
```

For querying strategies, see [How to Retrieve Entries](/howto/retrieve-entries/). For free-text search, see [pbook search](#pbook-search).

## pbook get

Get a single entry by ID.

```
pbook get ENTRY_ID [--json]
```

| Name       | Type    | Default  | Description                  |
|------------|---------|----------|------------------------------|
| `ENTRY_ID` | integer | required | Entry primary key            |
| `--json`   | flag    | off      | Machine-readable JSON output |

```
pbook get 42 --json
```

The JSON payload includes `id`, `title`, `content`, parsed `tags`, `entry_type`, `source_project`, `needs_review`, `rejected`, `rejection_reason`, ISO datetimes, and feedback counters. The `embedding` column is stripped.

## pbook search

Search the playbook by tag and/or free-text query. Submits a `RetrievalWorkflow` on `pbook-task-queue` — the worker must be running.

```
pbook search [QUERY] [--tag TAG]... [--threshold F] [--mode create|fix] [--limit N] [--token-budget N] [--include-rejected] [--include-unapproved] [--temporal-address ADDR] [--json]
```

| Name                   | Type    | Default          | Description                                             |
|------------------------|---------|------------------|---------------------------------------------------------|
| `QUERY`                | string  | `""`             | Free-text query; ranked by cosine similarity when set   |
| `--tag`                | string  | (none)           | Filter by tag; repeatable, AND-merged with query        |
| `--threshold`          | float   | `0.0`            | Drop matches below this similarity                      |
| `--mode`               | choice  | `create`         | Tiebreaker mode (`create` or `fix`)                     |
| `--limit`              | integer | `20`             | Cap on returned entries                                 |
| `--token-budget`       | integer | `5000`           | Token budget for the packed result                      |
| `--include-rejected`   | flag    | off              | Include rejected entries                                |
| `--include-unapproved` | flag    | off              | Include `needs_review` entries (default: approved only) |
| `--temporal-address`   | string  | `localhost:7233` | Temporal server address                                 |
| `--json`               | flag    | off              | Machine-readable JSON output                            |

You must provide either a `QUERY` or at least one `--tag`. When `QUERY` is set, results carry a `similarity` field (cosine similarity in `[0.0, 1.0]`) and ordering is semantic-primary (tag overlap and mode-boost break ties).

```
pbook search "flaky pytest" --tag lang:python --threshold 0.6 --json
pbook search --tag lang:python --tag domain:testing --json
```

For ranking design, see [Retrieval Ranking](/explanation/retrieval-ranking/). For the workflow steps, see [Workflows Reference](/reference/workflows/#retrievalworkflow).

## pbook sources

List the `entry_sources` rows that produced an entry. Each row records one originating Claude Code session and the situation excerpt forge captured during extraction.

```
pbook sources ENTRY_ID [--json]
```

| Name       | Type    | Default  | Description                              |
|------------|---------|----------|------------------------------------------|
| `ENTRY_ID` | integer | required | Entry primary key                        |
| `--json`   | flag    | on       | Machine-readable JSON output (default)  |

The JSON output is a list of source rows. Each row carries `id`, `entry_id`, `session_id`, `project_name`, `experience_hash`, `source_context` (the situation excerpt), and ISO `created_at`. The `source_context_embedding` BLOB is stripped.

```
pbook sources 151
```

For end-to-end "discuss this playbook" composition, see [Use as Skill Substrate](/howto/use-as-skill-substrate/).

## pbook session-text

Render the transcript of a Claude Code session, identified by its session ID. Resolves the `.jsonl` path by scanning `~/.claude/projects/`; falls back to `--path`.

```
pbook session-text SESSION_ID [--path PATH] [--raw] [--json]
```

| Name           | Type | Default  | Description                                                 |
|----------------|------|----------|-------------------------------------------------------------|
| `SESSION_ID`   | string | required | Session UUID (matches the `.jsonl` file's stem)         |
| `--path`       | path | (none)   | Override transcript path when not in `~/.claude/projects/`  |
| `--raw`        | flag | off      | Emit the JSONL bytes verbatim instead of rendered text      |
| `--json`       | flag | off      | Wrap the output as `{session_id, path, raw, text}`          |

Default output is rendered markdown (`USER:` / `ASSISTANT:` form via the transcript renderer used during ingestion). On missing transcripts the error code is `session_file_missing`.

```
pbook session-text abc-def-123-456
pbook session-text abc-def-123-456 --raw | head -20
pbook session-text abc-def-123-456 --path /custom/path.jsonl
```

## pbook tags

Show the canonical tag namespaces and the values currently in use.

```
pbook tags [--json]
```

| Name     | Type | Default | Description                              |
|----------|------|---------|------------------------------------------|
| `--json` | flag | on      | Machine-readable JSON output (default)  |

The JSON payload combines the closed namespace set with values discovered across non-rejected entries:

```json
{
  "namespaces": {
    "general": ["domain", "lang", "lib"],
    "extracted": ["pattern", "project"]
  },
  "values_in_use": {
    "lang": ["python", "typescript"],
    "lib": ["pydantic", "sqlalchemy"],
    "domain": ["cli", "testing"],
    "project": ["forge", "pbook"],
    "pattern": []
  }
}
```

Use `namespaces` to validate user-supplied tags and `values_in_use` to suggest precedent values without enumerating every entry.

For tag namespace details, see [Tags Reference](/reference/tags/).

## pbook add

Add a playbook entry. Reads JSON from stdin by default; pass `--file` to read from a path or `--schema` to print the JSON schema.

```
pbook add [--file FILE] [--needs-review] [--schema] [--json]
```

| Name             | Type | Default | Description                                                       |
|------------------|------|---------|-------------------------------------------------------------------|
| `--file`         | path | (none)  | JSON file containing a `PlaybookEntry`. If omitted, read stdin    |
| `--needs-review` | flag | off     | Flag the entry as needing review (default: stored as approved)    |
| `--schema`       | flag | off     | Print the `PlaybookEntry` JSON schema and exit                    |
| `--json`         | flag | off     | Machine-readable JSON response: `{id, title, approved, needs_review, rejected}` |

```
echo '{"title":"Quote shell paths","content":"...","tags":["lang:shell"]}' \
  | pbook add --json --needs-review
pbook add --file entry.json
pbook add --schema
```

Errors flow through the JSON envelope: invalid JSON → `validation_error`, malformed tags → `tag_invalid`.

For workflow context, see [How to Manage Entries](/howto/manage-entries/). For field definitions, see [Data Model Reference](/reference/data-model/).

## pbook update

Update an existing entry by ID.

```
pbook update ENTRY_ID --file FILE
```

| Name       | Type    | Default  | Description                       |
|------------|---------|----------|-----------------------------------|
| `ENTRY_ID` | integer | required | Entry primary key                 |
| `--file`   | path    | required | JSON file with fields to update   |

```
pbook update 42 --file updates.json
```

## pbook approve

Clear the `needs_review` flag on an entry.

```
pbook approve ENTRY_ID [--json]
```

| Name       | Type    | Default  | Description                  |
|------------|---------|----------|------------------------------|
| `ENTRY_ID` | integer | required | Entry primary key            |
| `--json`   | flag    | off      | Machine-readable JSON output |

```
pbook approve 42 --json
```

The JSON response carries `id`, `title`, `approved: true`, `needs_review: false`, `rejected`, and `rejection_reason`.

For the review workflow, see [How to Manage Entries](/howto/manage-entries/). For why entries need review, see [Understanding the Quality Bar](/explanation/quality-bar/).

## pbook reject

Soft-mark an entry as rejected. The row is preserved for audit (default queries hide rejected entries; surface them via `--include-rejected`).

```
pbook reject ENTRY_ID [--reason TEXT] [--json]
```

| Name       | Type    | Default  | Description                                  |
|------------|---------|----------|----------------------------------------------|
| `ENTRY_ID` | integer | required | Entry primary key                            |
| `--reason` | string  | `""`     | Why the entry was rejected (optional)        |
| `--json`   | flag    | off      | Machine-readable JSON output                 |

The JSON response carries `id`, `title`, `approved: false`, `rejected: true`, and `rejection_reason` (`null` when no reason was provided).

```
pbook reject 42 --reason "advice was specific to v1 API" --json
```

`pbook reject` does **not** delete the row. To recover a mistakenly rejected entry, use `pbook update` to set `rejected=false`. To audit rejections, use `pbook list --include-rejected`.

## pbook check-duplicate

Check for duplicate entries matching a title.

```
pbook check-duplicate --title TITLE [--tag TAG]...
```

| Name      | Type   | Default  | Description                                  |
|-----------|--------|----------|----------------------------------------------|
| `--title` | string | required | Title to match (case-insensitive LIKE)       |
| `--tag`   | string | (none)   | Tags to refine duplicate ranking; repeatable |

```
pbook check-duplicate --title "WAL mode" --tag lib:sqlalchemy
```

## pbook push

Push experience data for LLM extraction via Temporal.

```
pbook push --file FILE [--temporal-address ADDR]
```

| Name                 | Type   | Default          | Description                                                                  |
|----------------------|--------|------------------|------------------------------------------------------------------------------|
| `--file`             | path   | required         | JSON file with `PushExperienceInput` data; accepts a single object or array  |
| `--temporal-address` | string | `localhost:7233` | Temporal server address                                                      |

```
pbook push --file experience.json
```

For experience data guidelines, see [How to Push Experience](/howto/push-experience/). For input field definitions, see [Data Model Reference](/reference/data-model/).

## pbook ingest

Ingest Claude session transcripts into the playbook via Temporal.

```
pbook ingest [TRANSCRIPT_PATH] [--all] [--project PROJECT] [--min-size N] [--dry-run] [--force] [--temporal-address ADDR]
```

| Name                 | Type    | Default          | Description                                  |
|----------------------|---------|------------------|----------------------------------------------|
| `TRANSCRIPT_PATH`    | path    | (none)           | Path to a single JSONL session file          |
| `--all`              | flag    | off              | Discover and ingest all sessions             |
| `--project`          | string  | `""`             | Filter by project (with `--all`) or override |
| `--min-size`         | integer | `10240`          | Minimum session file size in bytes           |
| `--dry-run`          | flag    | off              | Show sessions/stats without ingesting        |
| `--force`            | flag    | off              | Reprocess already-ingested sessions          |
| `--temporal-address` | string  | `localhost:7233` | Temporal server address                      |

```
pbook ingest --all --dry-run
pbook ingest --all
pbook ingest --all --project forge
pbook ingest ~/.claude/projects/<id>/session.jsonl
```

For the ingestion workflow, see [How to Ingest Transcripts](/howto/ingest-transcripts/). For how ingestion fits into the system, see [Architecture](/explanation/architecture/).

## pbook sessions

List sessions previously ingested by `pbook ingest`, newest activity first.

```
pbook sessions [--project PROJECT] [--limit N] [--json]
```

| Name        | Type    | Default | Description                  |
|-------------|---------|---------|------------------------------|
| `--project` | string  | `""`    | Filter by source project     |
| `--limit`   | integer | `20`    | Maximum sessions to return   |
| `--json`    | flag    | off     | Machine-readable JSON output |

Each row carries the session id, project, lifecycle status (`running`, `completed`, `error`), counts of experiences and entries created, and any error message that surfaced during ingestion.

```
pbook sessions --json --limit 5
```

## pbook review

List entries needing review.

```
pbook review [--limit N] [--json]
```

| Name      | Type    | Default | Description                  |
|-----------|---------|---------|------------------------------|
| `--limit` | integer | `20`    | Maximum entries to show      |
| `--json`  | flag    | off     | Machine-readable JSON output |

The JSON output mirrors `pbook list --json` — same shape per entry. Iterate it to drive a review queue (`pbook review --json | jq '.[].id'`).

```
pbook review --json
```

## pbook feedback

Record feedback on a retrieved entry. Increments the entry's `helpful_count` or `harmful_count`, which affects future [retrieval ranking](/explanation/retrieval-ranking/).

```
pbook feedback ENTRY_ID (--helpful | --harmful) [--context TEXT]
```

| Name        | Type    | Default  | Description                                          |
|-------------|---------|----------|------------------------------------------------------|
| `ENTRY_ID`  | integer | required | Entry primary key                                    |
| `--helpful` | flag    | (none)   | Mark as helpful; mutually exclusive with `--harmful` |
| `--harmful` | flag    | (none)   | Mark as harmful; mutually exclusive with `--helpful` |
| `--context` | string  | `""`     | Why the entry was helpful or harmful                 |

Exactly one of `--helpful` or `--harmful` is required.

```
pbook feedback 42 --helpful
pbook feedback 7 --harmful --context "Advice was outdated for v2 API"
```

For how feedback affects scoring, see [Retrieval Ranking](/explanation/retrieval-ranking/). For the input model, see [Data Model Reference](/reference/data-model/#feedbackinput).

## pbook prune

Identify entries that should be reviewed for removal. Entries are flagged if they are consistently harmful (harmful ratio exceeds 50% after 5+ retrievals) or never retrieved and older than 180 days.

```
pbook prune (--dry-run | --apply) [--min-retrievals N] [--max-harmful-ratio F] [--max-stale-days N]
```

| Name                  | Type    | Default | Description                                                                |
|-----------------------|---------|---------|----------------------------------------------------------------------------|
| `--dry-run`           | flag    | (none)  | List candidates without changing anything                                  |
| `--apply`             | flag    | (none)  | Mark candidates with `needs_review=True` and tag `pattern:prune-candidate` |
| `--min-retrievals`    | integer | `5`     | Minimum retrievals before harmful ratio applies                            |
| `--max-harmful-ratio` | float   | `0.5`   | Harmful ratio threshold                                                    |
| `--max-stale-days`    | integer | `180`   | Days before unretrieved entry is considered stale                          |

Exactly one of `--dry-run` or `--apply` is required. Pruning never deletes entries — it marks them for human review.

```
pbook prune --dry-run
pbook prune --apply --min-retrievals 3 --max-harmful-ratio 0.6
```

For the quality review workflow, see [How to Manage Entries](/howto/manage-entries/).

## pbook migrate

Run database migrations.

```
pbook migrate
```

No options. Runs Alembic migrations to head on the resolved database path.

## pbook skill-prompt

Return the editorial guidance payload that drives a Claude Code skill built on pbook. Consumed by `/skill-creator` at build time and (optionally) by the skill agent at runtime to refresh context.

```
pbook skill-prompt [--operation OP] [--json]
```

| Name          | Type   | Default | Description                                                                       |
|---------------|--------|---------|-----------------------------------------------------------------------------------|
| `--operation` | string | `""`    | Limit output to one workflow (`query`, `discuss`, `review_queue`, or `add`)       |
| `--json`      | flag   | on      | Machine-readable JSON output (default)                                            |

The full payload contains:

- `commands` — per-command description, args summary, and example for every CLI command.
- `workflows` — markdown-formatted guidance for the four skill workflows: `query`, `discuss`, `review_queue`, `add`.
- `tags` — canonical namespaces and notes on the tag system.

```
pbook skill-prompt | jq '.workflows | keys'
pbook skill-prompt --operation discuss | jq -r .workflow
```

For the composition recipes, see [Use as Skill Substrate](/howto/use-as-skill-substrate/).

## Exit codes

| Code | Meaning                                                                       |
|------|-------------------------------------------------------------------------------|
| 0    | Success                                                                       |
| 1    | Error (specifics in the JSON `code` field when `--json`, or stderr otherwise) |
| 2    | Usage error (missing required options, unknown command — set by Click)        |

Branch on the JSON `code` field, not the integer exit code — the latter is binary by design.
