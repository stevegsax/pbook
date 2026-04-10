# pbook

Prevent LLM agents from repeating mistakes by surfacing relevant, hard-won lessons at the moment they are needed

**Audience**: Engineers integrating pbook into their projects or operating it as a service

## Why pbook exists

LLM agents repeat mistakes. When an agent encounters a library quirk, an
undocumented API behavior, or a subtle configuration pitfall, the lesson
disappears at the end of the session. The next invocation starts from scratch,
makes the same wrong first attempt, and burns the same debugging cycles.

This is the problem that **Agentic Context Engineering** addresses. Research
(Zhang et al., "Agentic Context Engineering," ICLR 2026) demonstrates that
treating an LLM's context as an evolving **playbook** — a structured collection
of strategies, pitfalls, and domain-specific knowledge that accumulates over
time — yields large improvements over static prompts. On agent benchmarks, the
approach improved accuracy by 10.6% over strong baselines. The key insight is
that contexts should function as comprehensive, detailed playbooks rather than
compressed summaries. Monolithic context rewriting leads to **brevity bias**
(collapsing toward generic advice) and **context collapse** (eroding detailed
knowledge through iterative summarization). Structured, incremental updates
avoid both failure modes.

pbook is an implementation of this principle. It stores lessons extracted from
real project experience and surfaces them at the moment they are relevant —
giving the LLM the specific, hard-won knowledge it needs before it starts
working. Every entry must clear a strict quality bar: it must be **unexpected**
(the default approach would have been wrong) and **actionable** (there is
specific advice that helps next time). Generic advice like "use proper error
handling" is rejected. Specific advice like "Mistral OCR returns base64 with a
`data:` URI prefix — strip it before decoding" is kept. See
[why the quality bar exists](explanation/quality-bar.html) for the reasoning
behind this constraint.

In practice, pbook runs as a Temporal worker alongside your project. Client
workflows push experience data (what went wrong, how it was fixed), and pbook's
extraction pipeline distills it into structured entries tagged by language,
library, domain, and project. When the LLM needs context — writing new code or
debugging a failure — the [retrieval system](explanation/retrieval-ranking.html)
ranks entries by tag overlap and intent mode, packing the most relevant ones
within a token budget. The result is a focused playbook section injected into
the LLM's context: not a summary of everything pbook knows, but the specific
entries that match the current task.

pbook manages two content types: **pitfalls** extracted from experience and
**curated advice** submitted by humans. All entries are managed through a
[CLI](reference/cli.html) or [Temporal workflows](reference/workflows.html)
and stored in a [SQLite database](reference/data-model.html) with
[namespaced tags](reference/tags.html) for retrieval. Each entry carries a
vector embedding for semantic deduplication and similarity search, preventing
the redundant entries that lead to context collapse.

The system includes a **feedback loop** inspired by ACE's helpfulness tracking.
Every time entries are served in a retrieval result, the system records which
entries were delivered. Clients can then report whether entries were helpful or
harmful via `pbook feedback`. This feedback flows back into the
[ranking algorithm](explanation/retrieval-ranking.html): entries with strong
helpful ratios float higher, while consistently harmful entries sink. A
[pruning mechanism](howto/manage-entries.html) flags entries that are
consistently harmful or never retrieved for human review. A scheduled
**maintenance workflow** consolidates semantically similar entries using LLM
merging, keeping the playbook lean without losing knowledge.

## Sections

- [Tutorials](tutorials/index.html) — Learn by doing
- [How-to Guides](howto/index.html) — Accomplish specific tasks
- [Reference](reference/index.html) — Technical descriptions
- [Explanation](explanation/index.html) — Background and context
