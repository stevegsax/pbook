# Architecture and Design

pbook is a knowledge playbook service that stores curated advice and extracted pitfalls for LLM-assisted workflows. This document explains the design decisions behind its architecture.

## Why a separate database

pbook maintains its own SQLite database, independent of any client project's data. This separation serves three purposes.

First, isolation. Client workflows cannot corrupt playbook data through accidental writes, schema migrations, or test teardown. The playbook store is append-mostly -- entries are added and occasionally updated, but bulk deletes are rare. A client bug that wipes its own database does not affect the shared knowledge base.

Second, sharing. Multiple projects query the same playbook. Forge, pbook itself, and future projects all draw from one store. Duplicating entries per project would create drift -- the same pitfall described slightly differently in each copy, with no single source of truth.

Third, operational independence. The playbook database can be backed up, migrated, or reset without coordinating with client project lifecycles. Alembic manages schema migrations. The database path follows XDG conventions (`~/.local/state/pbook/pbook.db`).

## Why a separate Temporal queue

pbook runs its own Temporal worker on the `pbook-task-queue`, separate from client workers. This means pbook can be scaled, restarted, or upgraded without affecting client workflows.

A client workflow calls pbook by executing a child workflow on `pbook-task-queue`. The Temporal server routes the request to the pbook worker. If the pbook worker is down, the request waits in the queue until it comes back. If the pbook worker is upgraded with new activities, client workers do not need to restart.

This also means pbook's activity registrations do not pollute client workers. The pbook worker registers fourteen activities (fetch, save, extract, review, validate, export, compute embedding, find duplicates, prune, consolidate). A client worker does not need to know about any of them -- it only needs to know the workflow names and input models.

## Why a controlled tag vocabulary

Tags determine which entries surface during retrieval. A freeform tag system would require fuzzy matching to equate "py" with "python" or "testing" with "test" -- adding complexity and reducing reliability. Controlled namespaces with predefined value mappings eliminate this ambiguity entirely.

The two-tier design (general vs extracted) reflects different creation patterns. General tags like `lang:python` and `lib:sqlalchemy` are attached to curated advice that applies across projects. Extracted tags like `project:forge` and `pattern:failure-pattern` are attached to pitfalls specific to one codebase. The retrieval ranking system uses this tier distinction to weight results based on intent -- general knowledge for creation, project-specific knowledge for debugging.

See [Tag System Reference](../reference/tags.md) for namespace definitions. See [Retrieval Ranking](retrieval-ranking.md) for how tags affect scoring.

## Two ingestion paths

Entries enter the playbook through two paths, each designed for a different source of knowledge.

**Extraction** is the automated path. A developer pushes raw experience data -- a problem, a resolution, and context -- through the `ExtractionWorkflow`. The LLM analyzes the experience and extracts structured entries, tagging them as pitfalls with `needs_review=True`. Each entry receives a vector embedding for semantic deduplication. This path handles project-specific knowledge: API quirks, framework gotchas, and patterns that failed. The quality bar is enforced by the extraction prompt, which instructs the LLM to extract nothing rather than extract something generic or misleading.

**Direct submission** is the manual path. A developer submits a curated entry through `pbook add`, which triggers the `ManualEntryWorkflow`. The workflow computes an embedding for the proposed entry, checks for semantic duplicates, then runs LLM review (quality assessment informed by duplicate context). The LLM can approve the entry as-is, suggest improvements to the title, content, or tags, or reject it with a reason. This path handles general knowledge: best practices and domain-specific advice that does not come from a specific failure experience.

Both paths produce the same output: `PlaybookEntry` records in the database with validated tags and vector embeddings. The distinction between extraction and direct submission is about input, not output.

## Why embeddings for deduplication

As a playbook grows, similar entries inevitably appear. Two developers may encounter the same SQLite quirk and push near-identical experience reports. Title-based `LIKE` matching catches exact duplicates but misses semantically equivalent entries with different wording.

Vector embeddings solve this. Each entry is embedded using OpenAI's `text-embedding-3-small` model at creation time. The `ManualEntryWorkflow` computes the embedding and runs a cosine similarity check against existing entries before the LLM review step. The `MaintenanceWorkflow` uses embeddings to cluster similar entries for consolidation -- an LLM merges each cluster into a single comprehensive entry, preserving all unique insights while eliminating redundancy. This is the "grow-and-refine" mechanism prescribed by ACE: the playbook expands freely through extraction and submission, then periodically contracts through maintenance, preventing the context collapse that comes from unbounded growth.

## Function Core / Imperative Shell

pbook follows the Function Core / Imperative Shell pattern throughout. Pure functions handle all computation -- building prompts, scoring entries, ranking and packing results, validating tags. Imperative code handles all I/O -- database reads and writes, LLM API calls, Temporal activity registration.

This split makes the system testable without mocking. The scoring algorithm (`score_entry`), ranking logic (`rank_and_pack`), prompt construction (`build_extraction_system_prompt`), and tag validation (`parse_tag`, `validate_tags`) are all pure functions that take data in and return data out. Tests call them directly with constructed inputs and assert on outputs.

The imperative shell is thin. Temporal activities fetch data from the store, call pure functions to process it, and write results back. The LLM call is wrapped in `execute_extraction_call`, which takes a provider as an argument so tests can inject a mock without touching global state.

## LLM integration via sax-llm

pbook uses the `sax-llm` library for all LLM API calls. sax-llm provides a `LLMProvider` protocol with a `build_request_params` / `call` interface, along with structured output support via Pydantic models.

The provider is registered at worker startup. The `_register_llm_provider` function in the worker module calls `sax_llm.get_provider` to create an Anthropic provider instance, then registers it via `pbook.llm.set_provider`. Activities access the provider through `pbook.llm.get_provider`, which raises `RuntimeError` if no provider has been registered.

pbook treats sax-llm as a black box. It does not configure API keys, manage rate limits, or handle provider-specific request formatting -- those are sax-llm's responsibilities. pbook defines its own structured output models (`ExtractionResult`, `ReviewResult`) and passes them to the provider's `build_request_params` as the `output_type`. The provider handles the rest.

See [data model reference](../reference/data-model.md) for the full model definitions and [Temporal workflows reference](../reference/workflows.md) for workflow and activity details.
