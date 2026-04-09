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

For querying strategies, see [How to Retrieve Entries](../howto/retrieve-entries.md).

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

For workflow context, see [How to Manage Entries](../howto/manage-entries.md).

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

For experience data guidelines, see [How to Push Experience](../howto/push-experience.md).

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
