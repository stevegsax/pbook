+++
title = "How-to Guides"
weight = 30
description = "Task-focused recipes for operating pbook."
+++
How-to guides answer "how do I do X?" for someone already familiar with pbook. They assume you have completed the tutorial and skip teaching in favor of direct instructions.

- [How to Manage Playbook Entries](manage-entries/) — add, update, review, approve, reject, give feedback on, and prune entries.
- [How to Retrieve Playbook Entries](retrieve-entries/) — query entries by tag via CLI or Temporal workflow, choose between create and fix mode, and control the token budget.
- [How to Push Experience Data](push-experience/) — submit experience reports to the LLM extraction pipeline via CLI or Temporal.
- [How to Ingest Claude Code Transcripts](ingest-transcripts/) — preview, ingest, batch-process, and reprocess Claude Code session transcripts.
- [How to Import Claude Code Conversations into pbook](import-claude-conversations/) — end-to-end procedure for starting services, importing transcripts, and reviewing extracted entries.
- [How to Integrate pbook with a Temporal Workflow](temporal-integration/) — call pbook workflows from another worker, set up cross-queue execution, or use pbook as a Python library.
- [How to Use pbook as a Claude Code Skill Substrate](use-as-skill-substrate/) — compose `search`, `sources`, `session-text`, `tags`, and `skill-prompt` to power a Claude Code skill that queries, discusses, reviews, and adds entries.
