# How to Ingest Claude Code Transcripts

## How to preview sessions with dry-run

Use `--dry-run` to inspect what would be ingested without requiring Temporal or any workers:

```
pbook ingest --all --dry-run
```

Output:

```
Discovered 14 sessions across 3 projects (filtered by min size 10240 bytes)

  forge          8 sessions   2.4 MB total
  pbook          4 sessions   1.1 MB total
  dashboard      2 sessions   0.3 MB total

Already ingested: 6
Would ingest:     8
```

Combine with `--project` to scope the preview:

```
pbook ingest --all --dry-run --project forge
```

## How to ingest a single session

Pass the path to a JSONL session file directly:

```
pbook ingest ~/.claude/projects/-Users-me-repos-forge/sessions/abc123.jsonl
```

Output:

```
Ingesting 1 session...
Extraction complete: 3 entries created.
```

To override the detected project name:

```
pbook ingest ~/.claude/projects/-Users-me-repos-forge/sessions/abc123.jsonl --project my-project
```

Prerequisites: Temporal server, forge worker, and pbook worker must be running. See [architecture](../explanation/architecture.md) for forge integration rationale.

## How to batch-ingest all sessions

Discover and ingest every session under `~/.claude/projects/`:

```
pbook ingest --all
```

Sessions smaller than 10240 bytes are skipped by default. Adjust with `--min-size`:

```
pbook ingest --all --min-size 5000
```

Already-ingested sessions are skipped automatically.

## How to filter by project

Use `--project` with `--all` to restrict ingestion to a single project:

```
pbook ingest --all --project forge
```

Only sessions whose project path matches `forge` are discovered.

## How to reprocess already-ingested sessions

By default, sessions that have already been ingested are skipped. Use `--force` to reprocess them:

```
pbook ingest --all --force
```

Or for a single session:

```
pbook ingest ~/.claude/projects/-Users-me-repos-forge/sessions/abc123.jsonl --force
```

See [CLI reference](../reference/cli.md#pbook-ingest) for full option details.
