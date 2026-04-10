# How to Manage Playbook Entries

## How to add a curated advice entry

Create a JSON file conforming to the `PlaybookEntry` schema:

```json
{
    "title": "Prefer factory fixtures over shared state in tests",
    "content": "Create fresh objects per test via factory fixtures rather than module-scoped shared state. Shared state causes ordering dependencies and flaky parallel runs.",
    "tags": ["domain:testing", "pattern:fixture"],
    "entry_type": "curated"
}
```

Add it:

```
pbook add --file entry.json
```

To print the full JSON schema for reference:

```
pbook add --schema
```

See [CLI reference](../reference/cli.md) for all `add` options. See [data model reference](../reference/data-model.md) for field definitions and valid `entry_type` values (`curated`, `pitfall`, `api_doc`).

## How to check for duplicates before adding

Before adding a new entry, check whether a similar one already exists:

```
pbook check-duplicate --title "Prefer factory fixtures over shared state"
```

Narrow the search with tags:

```
pbook check-duplicate --title "Prefer factory fixtures" --tag domain:testing
```

If duplicates are found, the output lists each match with its ID and content preview. If no duplicates are found:

```
No duplicates found.
```

## How to update an existing entry

Create a JSON file containing only the fields to update:

```json
{
    "content": "Updated advice text with more detail.",
    "tags": ["domain:testing", "pattern:fixture", "lang:python"]
}
```

Apply the update by entry ID:

```
pbook update 1 --file updates.json
```

Tag validation runs on updated tags. See [CLI Reference](../reference/cli.md) for details.

## How to review and approve extracted entries

List all entries pending review:

```
pbook review
```

Each entry is displayed with a `[needs-review]` flag, its type, tags, and a content preview. After reading the entry, approve it:

```
pbook approve 3
```

This clears the `needs_review` flag. The entry will now appear in retrieval results.

## How to reject a low-quality entry

If an extracted entry is inaccurate, redundant, or too vague, reject it:

```
pbook reject 3
```

This permanently deletes the entry from the database. Rejection is irreversible -- the experience data that produced the entry is not stored separately and cannot be re-extracted.

See [CLI reference](../reference/cli.md) for all review-related commands.

For why entries need review, see [Understanding the Quality Bar](../explanation/quality-bar.md).

## How to record feedback on retrieved entries

After using entries in a retrieval result, report whether they helped:

```
pbook feedback 42 --helpful
pbook feedback 7 --harmful --context "Advice was outdated for v2 API"
```

Feedback is cumulative -- the same entry can receive multiple helpful and harmful reports over time. These counters adjust the entry's [retrieval ranking](../explanation/retrieval-ranking.md): entries with strong helpful ratios rank higher in future results, while harmful entries sink.

See [CLI reference](../reference/cli.md#pbook-feedback) for all options.

## How to identify and prune harmful or stale entries

List entries that should be reviewed for removal:

```
pbook prune --dry-run
```

This identifies entries that are consistently harmful (>50% harmful ratio after 5+ retrievals) or never retrieved and older than 180 days. To mark them for review:

```
pbook prune --apply
```

This sets `needs_review=True` and adds the tag `pattern:prune-candidate`. Pruning never deletes entries -- use `pbook review` to inspect flagged entries, then approve or reject them individually.

Adjust thresholds as needed:

```
pbook prune --apply --min-retrievals 3 --max-harmful-ratio 0.6 --max-stale-days 90
```

See [CLI reference](../reference/cli.md#pbook-prune) for all options.
