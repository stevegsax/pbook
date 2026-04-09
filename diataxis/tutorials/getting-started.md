# Getting Started with pbook

In this tutorial, we will set up pbook and add our first knowledge entries.

By the end, we will have a running pbook worker, curated entries in the database, and experience with the review workflow for LLM-extracted entries.

## Prerequisites

- pbook installed (`uv sync`)
- A Temporal server running locally on `localhost:7233`

## Start the worker

The pbook worker listens on the `pbook-task-queue` for extraction, retrieval, and export requests. Start it in a terminal:

```
pbook worker
```

We will see log output confirming the worker is running:

```
pbook worker starting on queue pbook-task-queue
```

Leave this terminal open. We will use a second terminal for the remaining steps.

## Add a curated entry

We will create a curated advice entry about a common SQLAlchemy testing pitfall. Create a file called `entry.json`:

```json
{
    "title": "Call engine.dispose() in test teardown",
    "content": "SQLAlchemy engines hold connection pools open. In tests, always call engine.dispose() in teardown (or use a fixture with addcleanup) to avoid ResourceWarning and leaked connections across test boundaries.",
    "tags": ["lib:sqlalchemy", "domain:testing"],
    "entry_type": "curated"
}
```

Add it to the playbook:

```
pbook add --file entry.json
```

Output:

```
Added: Call engine.dispose() in test teardown
```

## List entries

Now we will verify the entry was stored:

```
pbook list
```

Output:

```
[1] Call engine.dispose() in test teardown
  Type: curated
  Tags: lib:sqlalchemy, domain:testing
  SQLAlchemy engines hold connection pools open. In tests, always call engine.dispose() in teardown (or use a fixture with addcleanup) to avoid ResourceWarning and leaked connections across test boundaries.
```

## Get a single entry

We can retrieve a specific entry by its ID:

```
pbook get 1
```

Output:

```
[1] Call engine.dispose() in test teardown
  Type: curated
  Tags: lib:sqlalchemy, domain:testing
  SQLAlchemy engines hold connection pools open. In tests, always call engine.dispose() in teardown (or use a fixture with addcleanup) to avoid ResourceWarning and leaked connections across test boundaries.
```

## Push experience data

Now we will push raw experience data through the extraction pipeline. The LLM will analyze the experience and create entries automatically. Create a file called `experience.json`:

```json
{
    "project": "forge",
    "problem": "SQLite raises ProgrammingError: SQLite objects created in a thread can only be used in that same thread when sharing a connection across Temporal activity threads.",
    "resolution": "Pass connect_args={'check_same_thread': False} to create_engine when building the SQLAlchemy engine for SQLite in multi-threaded contexts.",
    "context": "Temporal activities run in a thread pool. The default SQLite driver enforces same-thread access on connections."
}
```

Push it to the extraction workflow:

```
pbook push --file experience.json
```

Output:

```
Extraction complete: 1 entries created.
```

The extraction workflow sent the experience to an LLM, which distilled it into a structured playbook entry. Extracted entries are flagged for review before they become part of the active knowledge base.

## Review extracted entries

We will check which entries need review:

```
pbook review
```

Output:

```
1 entry/entries need review:

[2] Use check_same_thread=False for SQLite in threaded contexts [needs-review]
  Type: pitfall
  Tags: lib:sqlalchemy, lib:sqlite, domain:concurrency
  Project: forge
  SQLite's default driver enforces same-thread access on connections. Pass connect_args={'check_same_thread': False} to create_engine when ...
```

The entry looks correct. We will approve it:

```
pbook approve 2
```

Output:

```
Approved entry 2: Use check_same_thread=False for SQLite in threaded contexts
```

The entry is now part of the active knowledge base and will be included in retrieval results.

## What we accomplished

We completed the full pbook lifecycle:

- Started the pbook worker on `pbook-task-queue`
- Added a curated entry manually with `pbook add`
- Listed and retrieved entries with `pbook list` and `pbook get`
- Pushed raw experience data through the LLM extraction pipeline with `pbook push`
- Reviewed and approved an extracted entry with `pbook review` and `pbook approve`

## Next steps

- [Quality bar for entries](../explanation/quality-bar.md) -- what makes a good playbook entry
- [CLI reference](../reference/cli.md) -- full command documentation
