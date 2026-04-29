+++
title = "How to Use pbook as a Claude Code Skill Substrate"
weight = 123
description = "Compose pbook commands to power a Claude Code skill"
topic = "skill-substrate"
covers = ["How to fetch the editorial guidance via pbook skill-prompt --json", "How to compose `search` for the query workflow", "How to compose `get` + `sources` + `session-text` for the discuss workflow", "How to iterate the review queue with `review` + `approve` / `reject --reason`", "How to add new entries via stdin with tag discovery from `pbook tags`", "How to consume the JSON error envelope in shell pipelines"]
detail = "Recipe-style how-to. One section per skill workflow (query, discuss, review queue, add)."
+++

The pbook CLI is intentionally primitive. A Claude Code skill (typically built via `/skill-creator`) composes the primitive commands to produce four user-facing workflows: **query**, **discuss**, **review queue**, and **add**. This how-to is the external-facing version of the workflow guidance that `pbook skill-prompt --json` returns at runtime — they stay in sync.

Every command supports `--json`. Always pass it from a skill: success and failure both flow through one parseable stream (success payload on stdout, error envelope `{"error", "code"}` on stdout with non-zero exit). Without `--json` errors go to stderr and the only signal is the exit code.

## How to fetch the editorial guidance

`pbook skill-prompt --json` returns the canonical guidance that `/skill-creator` ingests at build time. The skill agent can also re-fetch at runtime to refresh context.

```bash
pbook skill-prompt | jq '.workflows | keys'
# → ["add", "discuss", "query", "review_queue"]

pbook skill-prompt --operation discuss | jq -r .workflow
# → markdown describing the discuss composition
```

The full payload contains:

- `commands` — per-command description, args summary, and example for every CLI command.
- `workflows` — markdown-formatted guidance for each of the five skill workflows.
- `tags` — canonical namespaces and notes on the tag system.

## How to compose the query workflow

When the user asks "find playbooks about X" or "what do we know about X?", prefer free-text search over tag enumeration.

```bash
# Try semantic search first
pbook search "flaky pytest" --json
```

The output is ranked by cosine similarity. The skill should show the user the top few hits with their `similarity` scores. If the top hit is below ~0.6, treat it as a weak match and say so.

If the user mentioned a tag explicitly, narrow with `--tag` — tag and query are AND-merged:

```bash
pbook search "flaky pytest" --tag lang:python --json
```

For "show me all `<category>`" queries, prefer `pbook list`:

```bash
pbook list --tag lang:python --json
```

`pbook search` requires the worker to be running (it submits a `RetrievalWorkflow` to `pbook-task-queue`). When the worker is down, the command emits the canonical error envelope:

```json
{ "error": "RetrievalWorkflow failed: ...", "code": "worker_unavailable" }
```

Surface that clearly to the user — don't retry silently.

## How to compose the discuss workflow

When the user picks an entry and wants to talk about *why* it exists, compose three commands in order:

```bash
# 1. The entry itself
pbook get 151 --json

# 2. The originating sources
pbook sources 151 --json

# 3. Only when needed: the original transcript
SESSION=$(pbook sources 151 --json | jq -r '.[0].session_id')
pbook session-text "$SESSION"
```

Each `entry_sources` row's `source_context` is the rich situation excerpt forge captured at extraction time. Show those first — they're usually enough. Reach for the transcript only when:

- The user asks something the source contexts don't answer.
- Multiple sources agree on the playbook but the user wants to see one specific case in detail.
- The user is debugging the playbook itself ("was extraction wrong?").

`pbook session-text` resolves the JSONL path by scanning `~/.claude/projects/`. If a session has been archived or moved, override with `--path`:

```bash
pbook session-text "$SESSION" --path /archive/sessions/$SESSION.jsonl
```

A missing transcript surfaces as `{"error": "...", "code": "session_file_missing"}`.

## How to iterate the review queue

When the user wants to triage entries flagged `needs_review`:

```bash
# 1. List the queue
pbook review --json | jq '.[].id' > /tmp/review_ids

# 2. For each id, fetch entry + sources, present to the user, decide
while read -r ID; do
    pbook get "$ID" --json
    pbook sources "$ID" --json
    # ...the skill shows these to the user and waits for a decision...
done < /tmp/review_ids

# 3. Apply the decision
pbook approve 151 --json
# or
pbook reject 151 --reason "advice was specific to v1 API" --json
```

Reject is **soft-mark**, not delete. The row survives for audit; default queries hide it. To recover a mistakenly rejected entry, use `pbook update` to clear `rejected`. To audit rejections, run `pbook list --include-rejected`.

`--reason` is optional but strongly encouraged — the skill should always supply it. The JSON output flags `rejection_reason: null` so consumers can treat unreasoned rejections as suspect.

The skill is the human-in-the-loop — don't auto-approve or auto-reject.

## How to record helpful/harmful feedback

When the user reacts to a playbook the skill just surfaced — positively ("perfect", "exactly", "yes that worked") or negatively ("that's wrong", "didn't help", "outdated") — capture the signal deliberately, only after confirming the user's intent. The skill is the only path that records *why* the user reacted; without that context, the bare counter is weak signal.

Match the strength of the user's reaction to the right command:

```bash
# Soft-negative — entry didn't apply here, but stays in the playbook
pbook feedback 151 --harmful --context "v3 API changed; advice was for v1"

# Hard-negative — entry is wrong or stale; hide from default queries
pbook reject 151 --reason "v3 API changed; advice was for v1" --json

# Positive — entry was a good fit
pbook feedback 151 --helpful --context "matched our flaky-pytest case exactly"
```

Confirm before recording — reflect the cue back as a question ("Sounds like 151 didn't apply here — want me to mark it harmful with the note 'v3 API changed'?") and run the CLI command only after the user agrees. Track which entry IDs the skill surfaced so the feedback attaches to the right row; if multiple entries are in scope, ask which one the user means.

The 3-retrieval threshold gates the signal: feedback only moves ranking after an entry has been retrieved at least three times. When the user gives feedback on a fresh entry, mention this so they don't expect an immediate ranking shift. See [How the Feedback Signal Is Processed](/explanation/feedback/) for the full lifecycle.

## How to add new entries

When the user wants to add a new playbook, compose tag discovery, schema discovery, and the stdin-based `add`:

```bash
# 1. Discover available tags
pbook tags --json | jq '.namespaces, .values_in_use'

# 2. Discover the JSON schema
pbook add --schema | jq '.properties | keys'

# 3. Compose the JSON with the user, then pipe it in
echo '{
  "title": "Quote shell paths in find pipes",
  "content": "Wrap path arguments in double quotes when piping through find...",
  "tags": ["lang:shell", "domain:cli"]
}' | pbook add --json
```

Use `--needs-review` if you want the user to do a final approval pass via the review queue later (otherwise the entry lands as approved):

```bash
echo '{...}' | pbook add --needs-review --json
```

Tag validation runs on the write path. Malformed tags surface as `{"error": "...", "code": "tag_invalid"}`. Unparseable JSON surfaces as `validation_error`. Always pass `--json` to get structured errors instead of stderr text.

The skill is the human-in-the-loop. Don't route through any LLM review path — the skill (with the user) IS the review.

## See also

- [CLI Reference](/reference/cli/) — every command's full surface, options, and error codes.
- [Data Model Reference](/reference/data-model/) — `entry_sources` schema, soft-rejection columns, JSON output contract.
- [Architecture](/explanation/architecture/) — why the CLI is primitive and the skill composes.
