+++
title = "How to Import Claude Code Conversations into pbook"
weight = 73
description = "End-to-end procedure for importing Claude Code conversations into pbook"
topic = "import-workflow"
covers = ["Starting the required services (Temporal, forge worker, pbook worker)", "Discovering Claude Code sessions with dry-run", "Running the batch import", "Reviewing extracted entries", "Handling import failures and re-running"]
detail = "End-to-end workflow walkthrough. Ordered steps that take the reader from zero to extracted entries in the playbook. Assume the reader already has pbook and forge installed."
+++
This guide walks through the full procedure for importing Claude Code conversation transcripts into pbook. The import runs as a batch job: pbook discovers session files under `~/.claude/projects/`, forge analyzes each transcript via its batch LLM API, and pbook extracts the identified experiences into playbook entries.

The procedure requires three services running in parallel: a Temporal server, a forge worker, and a pbook worker. Each gets its own terminal.

## Prerequisites

- `pbook` installed and migrated (`uv run pbook migrate`)
- `forge` installed with `pbook` as a dependency
- `temporal` CLI installed
- `ANTHROPIC_API_KEY` set in the environment
- `OPENAI_API_KEY` set in the environment (for entry embeddings)

## Step 1: Start the Temporal server

In terminal 1:

```
temporal server start-dev
```

Leave it running. The server listens on `localhost:7233` by default.

## Step 2: Start the forge worker

In terminal 2:

```
cd ~/repos-sax/forge
ANTHROPIC_API_KEY=sk-ant-... uv run forge worker
```

Wait for the log line `forge worker starting on queue forge-task-queue`. This worker handles the batch LLM calls that analyze each transcript. See [architecture](/explanation/architecture/) for why forge handles this step.

## Step 3: Start the pbook worker

In terminal 3:

```
cd ~/repos-sax/pbook
ANTHROPIC_API_KEY=sk-ant-... OPENAI_API_KEY=sk-... uv run pbook worker
```

Wait for the log line `pbook worker starting on queue pbook-task-queue`. This worker handles the extraction pipeline (converting identified experiences into playbook entries with embeddings).

## Step 4: Preview what will be imported

In terminal 4:

```
uv run pbook ingest --all --dry-run
```

The output lists discovered sessions grouped by project:

```
Found 111 session(s) to ingest (96.8 MB):

  forge: 18 session(s), 16.7 MB
  pbook: 5 session(s), 17.1 MB
  ...
```

Sessions smaller than 10KB are excluded by default. Already-ingested sessions are skipped automatically.

To preview only one project:

```
uv run pbook ingest --all --dry-run --project forge
```

## Step 5: Run the import

Start with a single project to validate the end-to-end flow:

```
uv run pbook ingest --all --project forge
```

Output:

```
Submitting 18 session(s) for ingestion...
Ingestion complete: 18 sessions processed, 47 experiences found, 32 entries created.
```

The command blocks until all sessions finish. Progress is visible in the forge and pbook worker logs. Once the single-project run succeeds, import everything:

```
uv run pbook ingest --all
```

## Step 6: Review the extracted entries

All extracted entries are marked `needs_review=True`. List them:

```
uv run pbook review
```

Approve good entries:

```
uv run pbook approve 42
```

Reject low-quality or misleading entries:

```
uv run pbook reject 43
```

See [Understanding the Quality Bar](/explanation/quality-bar/) for what makes an entry worth keeping.

## Step 7: Verify the results

List recent entries by project:

```
uv run pbook list --project forge --type pitfall --limit 20
```

Query by tag to confirm retrieval works:

```
uv run pbook list --tag lang:python --tag lib:temporal
```

## Re-running the import

Sessions are deduplicated via the `ingested_sessions` tracking table. Running `pbook ingest --all` again skips everything already processed. To force reprocessing (after fixing a bad run or updating the analysis prompt):

```
uv run pbook ingest --all --force
```

To reprocess a single session:

```
uv run pbook ingest ~/.claude/projects/<project-id>/<session-id>.jsonl --force
```

## Handling failures

If the forge worker crashes or loses a batch result, the failed `TranscriptIngestionWorkflow` instance remains visible in the Temporal UI (`http://localhost:8233`). Temporal automatically retries failed activities. For workflows that cannot recover, cancel them from the Temporal UI and re-run the import — the deduplication logic will skip sessions that were already recorded as ingested.

If a session produces no usable experiences, it is still recorded in `ingested_sessions` with `experiences_found=0` to prevent reprocessing. Use `--force` to retry if the analysis prompt has improved.

See [CLI reference](/reference/cli/#pbook-ingest) for full command options. See [ingest-transcripts](ingest-transcripts/) for task-focused CLI examples.