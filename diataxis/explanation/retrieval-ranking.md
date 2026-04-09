# How Retrieval Ranking Works

When you query pbook with tags like `lang:python`, `lib:sqlalchemy`, `project:forge`, the store returns every entry that matches at least one of those tags. With a mature playbook, that could be 50 or more entries. The token budget for the downstream LLM prompt is finite -- typically 5,000 tokens. Only a subset of those entries will fit. The ranking system decides which entries make the cut.

## Why two modes

The same set of entries serves two different purposes depending on what the caller is doing.

When writing new code (create mode), the most useful context is best practices and reference implementations. You want to know the idiomatic way to use SQLAlchemy's session lifecycle, the correct signature for `create_engine`, and the standard patterns for the domain. General-purpose entries and API documentation are most valuable here.

When debugging (fix mode), the most useful context is project-specific gotchas. You want to know that SQLite's default driver enforces same-thread access on connections, that the Mistral OCR API returns base64 with an unexpected prefix, that Temporal's test server retries failed activities indefinitely. These are pitfalls -- entries extracted from real project experience where the obvious approach did not work.

Both modes use the same entry pool. The ranking changes which entries float to the top.

## How scoring works

Every candidate entry receives a score based on two factors: tag overlap and mode-based weighting.

**Base score** is the count of tags shared between the entry and the query. An entry tagged `lang:python, lib:sqlalchemy` queried with `lang:python, lib:sqlalchemy, domain:testing` has a base score of 2 (two tags overlap). An entry with no overlapping tags scores 0 and is excluded entirely.

**Mode-based boosting** adjusts the base score depending on the retrieval intent:

- In create mode, each overlapping tag from a general namespace (`lang`, `lib`, `domain`) adds +0.5 to the score. API doc entries (`entry_type=api_doc`) receive an additional +1.0. This pushes reference material and broadly applicable advice above project-specific pitfalls.

- In fix mode, each overlapping tag from an extracted namespace (`project`, `pattern`) adds +0.5 to the score. Pitfall entries (`entry_type=pitfall`) receive an additional +1.0. This pushes project-specific lessons and failure patterns above generic best practices.

The effect is that an entry tagged `project:forge, pattern:retry-pattern` with type `pitfall` might score 4.0 in fix mode but only 2.0 in create mode. The entry is still returned in both modes -- it just ranks differently.

## Token budget packing

After scoring, entries are sorted highest-score-first and packed greedily into the token budget. Token estimation uses a rough approximation of 4 characters per token, applied to the entry's title and content concatenated.

The packing is greedy, not optimal. If a high-scoring entry is too large to fit in the remaining budget, it is skipped and the next entry is tried. This means a single long entry can be displaced by two shorter entries with lower individual scores. In practice, playbook entries are short (2-4 sentences of content), so this rarely matters.

The retrieval result includes both the packed entries and the total candidate count, so the caller can see how much was filtered out. A result with 5 packed entries from 50 candidates tells you the ranking is doing significant work.

## Why ranking, not filtering

A simpler design would filter entries by mode: create mode shows only general entries, fix mode shows only extracted entries. This would be wrong.

A general entry tagged `lang:python, lib:sqlalchemy` might contain advice about connection pooling that is relevant to a specific bug. A project-specific pitfall might reveal a pattern that applies to new code in the same project. Filtering by mode would lose these cross-cutting entries entirely.

Ranking preserves all matching entries and uses mode only as a scoring signal. An entry tagged only `lang:python` still appears in fix mode results -- it just ranks lower than project-specific pitfalls, and may not fit in the token budget if there are enough higher-scoring entries. This is the right tradeoff: when the budget is tight, mode-relevant entries win; when the budget is generous, everything relevant gets included.

See [tag namespaces](../reference/tags.md) for the full list of namespaces and how they map to tiers. See [how to retrieve entries](../howto/retrieve-entries.md) for CLI and workflow usage.
