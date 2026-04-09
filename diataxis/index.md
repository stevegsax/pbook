# pbook

**Audience**: Engineers integrating pbook into their projects or operating it as a service

## What pbook does

LLMs make the same mistakes twice. When an LLM encounters a library quirk, an
undocumented API behavior, or a subtle configuration pitfall, there is no
mechanism to carry that hard-won lesson into the next session. The same
debugging cycle repeats — costing time and producing the same wrong first
attempts.

pbook solves this by storing lessons extracted from real project experience and
surfacing them at the moment they are relevant. Every entry must clear a strict
quality bar: it must be **unexpected** (the default approach would have been
wrong) and **actionable** (there is specific advice that helps next time).
Generic advice like "use proper error handling" is rejected. Specific advice
like "Mistral OCR returns base64 with a `data:` URI prefix — strip it before
decoding" is kept. See [why the quality bar exists](explanation/quality-bar.html)
for the reasoning behind this constraint.

In practice, pbook runs as a Temporal worker alongside your project. Client
workflows push experience data (what went wrong, how it was fixed), and pbook's
extraction pipeline distills it into entries tagged by language, library, domain,
and project. When the LLM needs context — writing new code or debugging a
failure — the [retrieval system](explanation/retrieval-ranking.html) ranks
entries by tag overlap and intent mode, packing the most relevant ones within a
token budget.

pbook has three content types: **pitfalls** extracted from experience,
**curated advice** submitted by humans, and **API doc records** with method
signatures and examples. All are managed through a
[CLI](reference/cli.html) or [Temporal workflows](reference/workflows.html)
and stored in a [SQLite database](reference/data-model.html) with
[namespaced tags](reference/tags.html) for retrieval.

## Sections

- [Tutorials](tutorials/index.html) — Set up pbook, add entries, and run the extraction pipeline
- [How-to Guides](howto/index.html) — Task-focused instructions for common operations
- [Reference](reference/index.html) — CLI commands, data models, workflows, and tags
- [Explanation](explanation/index.html) — Quality bar, retrieval ranking, and architecture decisions
