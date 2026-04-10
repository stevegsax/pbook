# Temporal Workflows Reference

## Task queue

All workflows and activities run on `pbook-task-queue`.

## RetrievalWorkflow

Fetch, rank, and pack playbook entries within a token budget.

- **Input:** `RetrievalInput`
- **Output:** `RetrievalResult`

| Step | Activity                 | Timeout | Heartbeat | Description                                       |
|------|--------------------------|---------|-----------|---------------------------------------------------|
| 1    | `fetch_candidates`       | 30s     | --        | Query store for entries matching tags              |
| 2    | (in-workflow)            | --      | --        | Rank by score and pack within token budget         |
| 3    | `record_retrieval_event` | 10s     | --        | Record which entries were served (best-effort)     |

Step 3 is non-blocking -- if it fails, the retrieval result is still returned. The recorded retrieval counts feed into helpfulness-aware ranking. See [Retrieval Ranking](../explanation/retrieval-ranking.md) for details.

For usage, see [How to Retrieve Entries](../howto/retrieve-entries.md). For input/output field definitions, see [Data Model Reference](data-model.md).

## ExtractionWorkflow

Extract lessons from pushed experience data via LLM.

- **Input:** JSON `{"experiences": [...], "project": "..."}`
- **Output:** `{"entries_created": int}`

| Step | Activity                   | Timeout | Heartbeat | Description                              |
|------|----------------------------|---------|-----------|------------------------------------------|
| 1    | `extract_from_experience`  | 5m      | 60s       | Call extraction LLM with experience data |
| 2    | `save_extracted_entries`   | 30s     | --        | Save entries with `needs_review=True`    |

All saved entries have `entry_type=pitfall` and `needs_review=True`.

## ManualEntryWorkflow

Validate, review via LLM, and save a manually submitted playbook entry.

- **Input:** PlaybookEntry JSON
- **Output:** `{"approved": bool, "entry": dict, ...}`

| Step | Activity                 | Timeout | Heartbeat | Description                                |
|------|--------------------------|---------|-----------|----------------------------------------------|
| 1    | `validate_entry`         | 30s     | --        | Parse and validate against PlaybookEntry schema |
| 2    | `fetch_existing_entries` | 30s     | --        | Fetch recent entries for duplication context |
| 3    | `review_entry`           | 2m      | 60s       | LLM review for accuracy, specificity, minimality, duplication |
| 4    | `save_extracted_entries`  | 30s     | --        | Save the reviewed entry                    |

Returns early with `approved=False` if validation fails (step 1) or the LLM rejects the entry (step 3).

For usage, see [How to Manage Entries](../howto/manage-entries.md). For the quality review model, see [Understanding the Quality Bar](../explanation/quality-bar.md).

## ExportWorkflow

Fan-out export of matching playbook entries.

- **Input:** JSON `{"tags": [...], "limit": int}`
- **Output:** `{"entries": [...], "count": int}`

| Step | Activity              | Timeout | Heartbeat | Description                          |
|------|-----------------------|---------|-----------|--------------------------------------|
| 1    | `fetch_entry_ids`     | 30s     | --        | Query store for matching entry IDs   |
| 2    | `export_single_entry` | 30s each | --       | Fan-out: one activity per entry ID   |
| 3    | (gather)              | --      | --        | Collect results from all fan-out activities |

## Activity summary

| Activity                   | Module                    | LLM Call | Database | Timeout |
|----------------------------|---------------------------|----------|----------|---------|
| `fetch_candidates`         | `pbook.activities.retrieval`  | No   | Read     | 30s     |
| `record_retrieval_event`   | `pbook.activities.retrieval`  | No   | Write    | 10s     |
| `extract_from_experience`  | `pbook.activities.extraction` | Yes  | None     | 5m      |
| `save_extracted_entries`    | `pbook.activities.extraction` | No   | Write    | 30s     |
| `validate_entry`           | `pbook.activities.review`     | No   | None     | 30s     |
| `fetch_existing_entries`   | `pbook.activities.review`     | No   | Read     | 30s     |
| `review_entry`             | `pbook.activities.review`     | Yes  | None     | 2m      |
| `fetch_entry_ids`          | `pbook.activities.export`     | No   | Read     | 30s     |
| `export_single_entry`      | `pbook.activities.export`     | No   | Read     | 30s     |
