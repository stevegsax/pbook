+++
title = "How the Feedback Signal Is Processed"
weight = 141
description = "How helpful/harmful signals are recorded and integrated into retrieval"
topic = "feedback"
covers = ["When `pbook feedback` writes to the database (immediate, synchronous)", "When the signal influences ranking (every retrieval, via _helpfulness_adjustment)", "Why a 3-retrieval threshold gates the signal", "How retrieval_count is incremented (best-effort, fire-and-forget activity)", "How feedback survives across runs and ranks fresh per query (no batch pass)", "Connection to the ACE-style insight that playbooks should evolve from usage"]
detail = "Discursive. Trace the lifecycle of a single helpful/harmful click from CLI to subsequent retrievals."
+++

Feedback is the most consequential dial in pbook's ranking, and also the simplest one to misread. The mechanism has only two halves — recording and consumption — but they happen at different times, on different sides of a Temporal workflow, with different reliability guarantees. This document walks one feedback click through the system end to end.

## The recording side: instant, no worker

When a user runs `pbook feedback 151 --helpful`, the CLI calls [`pbook.store.record_feedback`](/reference/data-model/) directly. There is no queue, no Temporal submission, and no worker round-trip. The call is a single SQL UPDATE that increments either `helpful_count` or `harmful_count` by one. By the time the command returns to the shell, the counter on disk has already changed.

This synchrony is deliberate. Feedback is a small, idempotent write — pushing it through Temporal would buy nothing and add latency for the user (who is probably about to give feedback on another entry). The CLI command is also the only way to record feedback today; there is no UI or API surface that batches it.

What this means in practice: feedback is durable the moment the command exits. It does not need a worker running, and it survives independent of any retrieval activity.

## The consumption side: every retrieval, fresh

Feedback influences ranking inside `RetrievalWorkflow`, but only at one step: when [`rank_and_pack`](/reference/workflows/) calls `score_entry` for each candidate, the helpfulness adjustment is added to the tag-overlap and mode-boost score.

The adjustment lives in `_helpfulness_adjustment` (`src/pbook/activities/retrieval.py`):

```python
ratio = (helpful_count - harmful_count) / retrieval_count
adjustment = ratio * _HELPFULNESS_WEIGHT
```

`_HELPFULNESS_WEIGHT` is `2.0`, so the adjustment lands in the range `[-2.0, +2.0]`. The exact bounds matter less than the shape: a strongly negative ratio sinks an entry; a strongly positive ratio boosts it; an entry with no feedback at all contributes zero.

Critically, ranking is recomputed per query. There is no periodic batch job that "applies feedback" or rebuilds an index. The counter columns sit in the entries table; every retrieval reads them fresh and produces a new score. This means a feedback click affects the very next retrieval — but only if the threshold below has been met.

## Why a 3-retrieval threshold

`_helpfulness_adjustment` returns `0.0` when `retrieval_count < _MIN_RETRIEVALS_FOR_SIGNAL`, which is hardcoded to 3. An entry that has been retrieved fewer than three times is treated as having no feedback signal at all, regardless of how many helpful or harmful clicks it has accumulated.

The threshold exists because a fresh entry has volatile statistics. Without it, one stray click on the first retrieval of an entry would produce a `±2.0` swing — large enough to dominate the score and either lock the entry into the top of every result or banish it permanently. With three retrievals as the floor, the signal has to stabilize: at least three different retrieval contexts have surfaced the entry, and the user has had at least three chances to disagree with the assessment of the first.

This is a low bar. It is meant to filter out noise from the very first interaction, not to require statistical significance. The threshold is a constant in the source, not a configurable knob; if a deployment ever wanted a different value, that would be a code change.

## Bookkeeping: how `retrieval_count` gets incremented

The threshold depends on `retrieval_count` being accurate. That count is maintained by `record_retrieval_event`, the final activity step of `RetrievalWorkflow`. After `rank_and_pack` returns, the workflow fires `record_retrieval_event` with the IDs of the entries it actually packed (not the candidates it considered). The activity does a bulk increment on those rows and returns.

Two properties matter here. First, the activity is fire-and-forget: if it fails, the workflow logs a warning and returns the retrieval result anyway — the user gets their entries even if the bookkeeping fails. Second, only packed entries are counted. An entry that was a candidate but ranked low enough to be dropped from the token-budget pack does not get its `retrieval_count` incremented. This keeps the threshold honest: the signal only counts cases where the entry was actually presented to a downstream consumer.

The dependence on best-effort bookkeeping has a subtle implication. An entry whose `record_retrieval_event` failed in the past will reach the 3-retrieval threshold more slowly than its actual usage suggests. The bias is conservative — under-counting delays signal application but does not corrupt it.

## Why ranking, not a batch update

A naive design would batch feedback into a periodic "rerank" job that produces a precomputed ordering. pbook deliberately does not do this.

The reason is that ranking is intent-dependent. `RetrievalInput.mode` (CREATE versus FIX) re-weights the same tag overlaps differently; with the addition of `query`, ranking can become semantic-primary entirely. There is no single "right" ordering to precompute — every query produces its own. Reading counter columns at retrieval time and folding them into the score keeps the design unified: tags, mode, query similarity, and feedback all flow through the same `score_entry` function.

This is also why feedback takes effect immediately. There is no index to rebuild, no cache to invalidate, and no schedule to wait for. The next retrieval that reads the counter sees the new value.

## How this fits the broader playbook design

The feedback loop is what makes pbook a playbook in the [ACE](https://arxiv.org/abs/2510.04618) sense — a knowledge structure that improves with use rather than degrading. Without feedback, every entry would carry equal weight forever; entries that turned out to be misleading would keep getting surfaced, and entries that consistently helped would have no way to rise.

The shape of the integration matches the design constraint. Feedback is a small, low-friction write — the CLI command is one line. The signal is bounded — `±2.0` cannot dominate a strong tag match. The threshold is conservative — three retrievals before the signal counts. Rejection is a stronger statement than "harmful" — it removes the entry from default queries entirely. Together these give pbook a feedback surface that the user can use casually without worrying about over-correcting the playbook.

For the rest of the scoring algorithm, see [How Retrieval Ranking Works](/explanation/retrieval-ranking/). For the CLI surface, see [`pbook feedback`](/reference/cli/#pbook-feedback). For the counter columns, see the [`entries` schema](/reference/data-model/#database-schema).
