+++
title = "Explanation"
weight = 10
description = "Background, context, and design rationale."
+++
Explanation documents discuss the why — the reasoning, design decisions, and trade-offs behind pbook. Read these to deepen understanding of how the system fits together, not to accomplish a specific task.

- [How Retrieval Ranking Works](retrieval-ranking/) — why retrieval has two modes, how tag overlap and feedback feed into scoring, and why entries are ranked rather than just filtered.
- [Understanding the Quality Bar](quality-bar/) — the "unexpected + actionable" principle, why generic advice is excluded, and how the extraction prompt enforces it.
- [Architecture and Design](architecture/) — why pbook has its own database and Temporal worker, why tags are namespaced, and why transcript ingestion routes through forge's batch API.
