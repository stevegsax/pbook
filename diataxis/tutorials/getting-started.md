+++
title = "Getting Started with pbook"
weight = 12
description = "First-time setup and basic usage of pbook"
topic = "getting-started"
covers = ["Initializing the database", "Adding a curated entry via CLI", "Listing and retrieving entries", "Checking for duplicates", "Recording feedback on entries", "Identifying prune candidates", "Pushing experience data for extraction (requires Temporal)", "Reviewing and approving extracted entries"]
detail = "Walk through the full lifecycle in two tiers: CLI-only operations first (migrate, add, list, get, check-duplicate, feedback, prune), then the Temporal workflow path (push, review, approve). Use real CLI commands with concrete example JSON files. Show output at every step."
+++
In this tutorial, we will set up pbook and walk through the full entry lifecycle using only the CLI. No Temporal server required.

By the end, we will have entries in the database, recorded feedback, and seen duplicate detection in action.

## Prerequisites

- pbook installed (`uv sync`)

## Step 1: Initialize the database

Run the migration command to create the SQLite database:

```
pbook migrate
```

Output:

```
Migrations complete.
```

This creates the database at the default XDG path (`~/.local/state/pbook/pbook.db`). To use a custom path, set `PBOOK_DB_PATH` before running any commands.

## Step 2: Add a curated entry

We will create a curated advice entry about a real SQLite pitfall. Create a file called `entry.json`:

```json
{
    "title": "SQLite WAL mode prevents reader blocking",
    "content": "Always enable WAL mode on SQLite connections used by concurrent readers. Without it, writers block readers during transactions.",
    "tags": ["lang:python", "lib:sqlite"],
    "entry_type": "curated"
}
```

Add it to the playbook:

```
pbook add --file entry.json
```

Output:

```
Added: SQLite WAL mode prevents reader blocking
```

## Step 3: List and retrieve entries

Verify the entry was stored:

```
pbook list
```

Output:

```
[1] SQLite WAL mode prevents reader blocking
  Type: curated
  Tags: lang:python, lib:sqlite
  Always enable WAL mode on SQLite connections used by concurrent readers. Without it, writers block readers during transactions.
```

Retrieve a single entry by ID:

```
pbook get 1
```

For machine-readable output, add `--json`:

```
pbook get 1 --json
```

## Step 4: Check for duplicates

Before adding a similar entry, check for existing matches:

```
pbook check-duplicate --title "WAL mode"
```

Output:

```
Found 1 potential duplicate(s):

[1] SQLite WAL mode prevents reader blocking
  Type: curated
  Tags: lang:python, lib:sqlite
  Always enable WAL mode on SQLite connections used by concurrent readers. ...
```

The title-based matching catches obvious duplicates. When entries are created through workflows (extraction or manual entry), the system also performs semantic similarity checks using vector embeddings.

## Step 5: Record feedback

After using an entry in practice, record whether it helped:

```
pbook feedback 1 --helpful
```

Output:

```
Recorded helpful feedback for entry 1.
```

Or if the advice was wrong:

```
pbook feedback 1 --harmful
```

Feedback counters accumulate over time and feed into the [retrieval ranking algorithm](/explanation/retrieval-ranking/). Entries with strong helpful ratios rank higher; consistently harmful entries sink.

## Step 6: Identify entries for pruning

Over time, some entries become stale or accumulate negative feedback. The prune command identifies them:

```
pbook prune --dry-run
```

Output (when there are candidates):

```
2 prune candidate(s):

[5] Outdated config format
  Reason: never retrieved and 200 days old (threshold: 180 days)

[8] Wrong retry advice
  Reason: harmful ratio 70% exceeds 50% (7/10 retrievals)
```

To mark candidates for review:

```
pbook prune --apply
```

## Step 7: Push experience through the extraction pipeline

This step requires a running Temporal server and the pbook worker. If you have Temporal available, this demonstrates the full automated extraction path.

Start Temporal and the worker in separate terminals:

```
temporal server start-dev
```

```
OPENAI_API_KEY=... ANTHROPIC_API_KEY=... pbook worker
```

Create an experience report:

```json
{
    "project": "forge",
    "problem": "SQLAlchemy engine leaked connections after hot-reload",
    "resolution": "Added dispose() call in shutdown hook and switched to NullPool for dev"
}
```

Push it:

```
pbook push --file experience.json
```

Output:

```
Extraction complete: 1 entries created.
```

The extraction workflow calls the LLM to analyze the experience, generates a vector embedding for semantic deduplication, and saves the result with `needs_review=True`.

Review and approve:

```
pbook review
pbook approve 2
```

## What we accomplished

We completed the full pbook lifecycle:

- Initialized the database with `pbook migrate`
- Added a curated entry with `pbook add`
- Listed and retrieved entries with `pbook list` and `pbook get`
- Checked for duplicates with `pbook check-duplicate`
- Recorded feedback with `pbook feedback`
- Identified prune candidates with `pbook prune --dry-run`
- Pushed experience through the extraction pipeline with `pbook push`
- Reviewed and approved an extracted entry with `pbook review` and `pbook approve`

## Next steps

- [Quality bar for entries](/explanation/quality-bar/) -- what makes a good playbook entry
- [CLI reference](/reference/cli/) -- full command documentation
- [Retrieval ranking](/explanation/retrieval-ranking/) -- how feedback and modes affect which entries surface