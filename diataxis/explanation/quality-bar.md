+++
title = "Understanding the Quality Bar"
weight = 51
description = "Pushing experience data and the LLM extraction pipeline"
topic = "extraction"
covers = ["Why the quality bar exists", "What 'unexpected + actionable' means in practice", "Why generic advice is excluded", "How the extraction prompt enforces quality", "The optimistic review model (needs-review tag)"]
detail = "Discursive. This is the most important concept in pbook."
+++
Playbook entries become LLM context. When a downstream workflow asks pbook for advice, the returned entries are injected directly into the system prompt that shapes code generation, debugging, and design decisions. This makes quality control a load-bearing concern, not a cosmetic one.

A misleading entry is worse than no entry. If a playbook says "always pass `check_same_thread=False` to SQLite" without mentioning that this only matters in multi-threaded contexts, the LLM will apply it everywhere -- including single-threaded test harnesses where it masks real concurrency bugs. The advice was technically correct but contextually wrong, and the resulting error is almost impossible to trace back to the playbook entry that caused it.

An over-prescriptive entry is a different kind of failure. If a playbook says "always use asyncio.Lock for shared state in async code", it prevents the LLM from choosing simpler alternatives (like restructuring to avoid shared state entirely) when those would be better. The LLM follows the advice faithfully, producing correct but unnecessarily complex code.

## What "unexpected + actionable" means

The extraction LLM is not looking for general programming advice. It is looking for situations where the default approach failed -- the kind of thing an experienced developer would get wrong on the first try.

Signals that something is worth extracting:

- Multiple attempts were needed before finding the right approach
- An API behaved differently than its documentation suggests
- A standard pattern fails in a specific context
- A workaround was needed for a library or framework quirk

Consider the difference between these two entries:

- "Always use type hints in Python functions." This is generic advice. Every Python linter already enforces this. It does not tell you *when* type hints matter more than usual, or *which* type hint patterns cause problems. An LLM already knows this.

- "Mistral OCR returns base64 with a `data:image/jpeg;base64,` prefix that must be stripped before `base64.b64decode()`. Without stripping, the prefix decodes into garbage bytes prepended to the image data." This is specific, unexpected, and actionable. The Mistral documentation does not mention the prefix. The failure mode (silent data corruption rather than an error) makes it especially dangerous. An LLM would not know this without being told.

The first entry wastes token budget. The second entry prevents a real bug.

## The optimistic review model

Extracted entries are tagged `needs_review=True` but included in retrieval results by default. This is a deliberate design choice.

The alternative -- requiring human review before entries become active -- creates a review queue that rots. Entries sit unreviewed for days or weeks. By the time someone reviews them, the context that made them relevant has faded. The result is either rubber-stamp approvals or permanent backlogs.

The optimistic model inverts this: entries are live immediately, and review is a quality audit rather than a gate. The `approved_only` flag on retrieval exists as a safety valve for workflows that need higher confidence, but the default path trusts the extraction quality bar.

This works because the extraction prompt enforces quality aggressively. The prompt tells the LLM: "It is better to extract NOTHING than to extract a misleading or overly generic entry." The quality bar is in the extraction, not in the review.

## The extraction prompt

The extraction prompt (see [Temporal workflows reference](/reference/workflows/) for the full workflow) is built from the `build_extraction_system_prompt` function. It instructs the LLM to extract only entries that are both unexpected and actionable. Generic advice, standard rules, and expected outcomes are explicitly excluded.

The prompt lists specific anti-patterns: "use proper error handling", "write tests", entries about normal behavior. It also lists positive signals: multiple retries, API quirks, standard patterns that break in specific contexts. This gives the extraction LLM a concrete decision boundary rather than a vague quality aspiration.

The quality bar applies equally to direct submissions through the manual entry path. When a human submits an entry via `pbook add`, it goes through an LLM review that checks for duplicates, generic advice, and missing specificity. The review can reject entries or suggest improvements. See [how to push experience data](/howto/push-experience/) for both ingestion paths.