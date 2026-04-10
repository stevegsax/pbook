# Adding API Documentation Entries

In this tutorial, we will add an API documentation entry to the playbook. By the end, we will have an `api_doc` entry that surfaces library method signatures and usage examples during retrieval.

## Prerequisites

- pbook installed (`uv sync`)
- A running pbook worker (`pbook worker`)

## Step 1: Create the ApiDocRecord JSON

An `api_doc` entry stores structured API documentation as a JSON-serialized `ApiDocRecord` inside the `content` field. Create a file called `api-entry.json`:

```json
{
    "title": "sqlalchemy.create_engine",
    "content": "{\"library\": \"sqlalchemy\", \"method\": \"sqlalchemy.create_engine\", \"summary\": \"Create a new Engine instance bound to a database URL.\", \"signature\": \"create_engine(url: str | URL, **kwargs) -> Engine\", \"examples\": [\"engine = create_engine('sqlite:///app.db')\", \"engine = create_engine('sqlite:///app.db', connect_args={'check_same_thread': False})\"]}",
    "tags": ["lib:sqlalchemy", "domain:database"],
    "entry_type": "api_doc"
}
```

Notice that the `content` value is itself a JSON string containing the `ApiDocRecord` fields: `library`, `method`, `summary`, `signature`, and `examples`.

## Step 2: Add the entry

```
pbook add --file api-entry.json
```

Output:

```
Added: sqlalchemy.create_engine
```

## Step 3: Verify the entry

```
pbook list --type api_doc
```

Output:

```
[1] sqlalchemy.create_engine
  Type: api_doc
  Tags: lib:sqlalchemy, domain:database
  {"library": "sqlalchemy", "method": "sqlalchemy.create_engine", "summary": "Create a new Engine instance bound to a database URL.", ...
```

We can also retrieve the full entry:

```
pbook get 1
```

## Step 4: See api_doc entries in retrieval

API doc entries receive a scoring boost in create mode. We can see this by querying with matching tags:

```
pbook list --tag lib:sqlalchemy --json
```

The entry will appear alongside any curated or pitfall entries matching the same tags. When retrieved via the `RetrievalWorkflow` in create mode, api_doc entries rank higher because they provide the method signatures and examples most useful when writing new code.

## What we accomplished

We completed the api_doc entry lifecycle:

- Created a JSON file with a serialized `ApiDocRecord` as the `content` field
- Added it to the playbook with `pbook add`
- Verified it with `pbook list --type api_doc` and `pbook get`
- Confirmed it surfaces in tag-based retrieval

## Next steps

- [Data Model Reference](../reference/data-model.md) -- full `ApiDocRecord` and `PlaybookEntry` field definitions
- [How to Retrieve Entries](../howto/retrieve-entries.md) -- querying entries by tag and mode
- [Retrieval Ranking](../explanation/retrieval-ranking.md) -- how api_doc entries are scored differently by mode
