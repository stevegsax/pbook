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
| 2    | `compute_embedding`        | 60s     | --        | Generate vector embedding for each entry |
| 3    | `save_extracted_entries`   | 30s     | --        | Save entries with `needs_review=True`    |

Step 2 runs once per extracted entry. Embeddings are stored alongside the entry for semantic deduplication.

All saved entries have `entry_type=pitfall` and `needs_review=True`.

## ManualEntryWorkflow

Validate, review via LLM, and save a manually submitted playbook entry.

- **Input:** PlaybookEntry JSON
- **Output:** `{"approved": bool, "entry": dict, ...}`

| Step | Activity                 | Timeout | Heartbeat | Description                                |
|------|--------------------------|---------|-----------|----------------------------------------------|
| 1    | `validate_entry`         | 30s     | --        | Parse and validate against PlaybookEntry schema |
| 2    | `compute_embedding`      | 60s     | --        | Generate vector embedding for the proposed entry |
| 3    | `find_duplicates`        | 30s     | --        | Semantic duplicate detection via embedding similarity |
| 4    | `fetch_existing_entries`  | 30s     | --        | Fetch recent entries for broader review context |
| 5    | `review_entry`           | 2m      | 60s       | LLM review for accuracy, specificity, minimality, duplication |
| 6    | `save_extracted_entries`  | 30s     | --        | Save the reviewed entry                    |

Returns early with `approved=False` if validation fails (step 1) or the LLM rejects the entry (step 5). Steps 2-3 provide the reviewer with semantic duplicate context to prevent context collapse.

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

## MaintenanceWorkflow

Prune stale/harmful entries and consolidate semantically similar entries.

- **Input:** none (designed for cron scheduling)
- **Output:** `{"pruned": int, "consolidated": int, "clusters_found": int}`

| Step | Activity                            | Timeout | Heartbeat | Description                                     |
|------|-------------------------------------|---------|-----------|-------------------------------------------------|
| 1    | `fetch_all_entries_for_maintenance` | 60s     | --        | Fetch all entries with feedback counters         |
| 2    | (in-workflow)                       | --      | --        | Identify prune candidates (harmful ratio, stale) |
| 3    | `prune_entries`                     | 60s     | --        | Delete flagged entries                           |
| 4    | (in-workflow)                       | --      | --        | Group remaining entries by embedding similarity  |
| 5    | `consolidate_entries_llm`           | 5m      | --        | LLM merges each cluster into one entry           |
| 6    | `compute_embedding`                 | 60s     | --        | Generate embedding for the merged entry          |
| 7    | `save_extracted_entries`            | 30s     | --        | Save merged entry                                |
| 8    | `prune_entries`                     | 60s     | --        | Delete original cluster entries                  |

Steps 5-8 repeat for each cluster. Consolidation prevents context collapse by merging redundant entries while preserving all unique insights.

## Activity summary

| Activity                            | Module                        | LLM Call | Database | Timeout |
|-------------------------------------|-------------------------------|----------|----------|---------|
| `fetch_candidates`                  | `pbook.activities.retrieval`  | No       | Read     | 30s     |
| `record_retrieval_event`            | `pbook.activities.retrieval`  | No       | Write    | 10s     |
| `extract_from_experience`           | `pbook.activities.extraction` | Yes      | None     | 5m      |
| `compute_embedding`                 | `pbook.activities.extraction` | No       | None     | 60s     |
| `save_extracted_entries`            | `pbook.activities.extraction` | No       | Write    | 30s     |
| `validate_entry`                    | `pbook.activities.review`     | No       | None     | 30s     |
| `fetch_existing_entries`            | `pbook.activities.review`     | No       | Read     | 30s     |
| `find_duplicates`                   | `pbook.activities.review`     | No       | Read     | 30s     |
| `review_entry`                      | `pbook.activities.review`     | Yes      | None     | 2m      |
| `fetch_all_entries_for_maintenance` | `pbook.activities.maintenance`| No       | Read     | 60s     |
| `prune_entries`                     | `pbook.activities.maintenance`| No       | Write    | 60s     |
| `consolidate_entries_llm`           | `pbook.activities.maintenance`| Yes      | None     | 5m      |
| `fetch_entry_ids`                   | `pbook.activities.export`     | No       | Read     | 30s     |
| `export_single_entry`              | `pbook.activities.export`     | No       | Read     | 30s     |

The `compute_embedding` activity calls the OpenAI API (`text-embedding-3-small`) and returns a base64-encoded float32 vector. It is not an LLM call but does require the `OPENAI_API_KEY` environment variable.
