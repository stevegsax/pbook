# How to Retrieve Playbook Entries

## How to query entries by tag via CLI

Filter entries by one or more tags. Multiple `--tag` flags are OR-matched:

```
pbook list --tag lang:python --tag lib:sqlalchemy
```

Combine with other filters:

```
pbook list --tag domain:testing --type pitfall --limit 10
```

For machine-readable output:

```
pbook list --tag lib:sqlalchemy --json
```

## How to retrieve entries via Temporal workflow

Call `RetrievalWorkflow` from Python to fetch ranked entries within a token budget:

```python
from __future__ import annotations

import asyncio

from temporalio.client import Client

from pbook.models import RetrievalInput, RetrievalResult
from pbook.workflows.retrieval import RetrievalWorkflow

PBOOK_TASK_QUEUE = "pbook-task-queue"


async def retrieve() -> RetrievalResult:
    client = await Client.connect("localhost:7233")
    result = await client.execute_workflow(
        RetrievalWorkflow.run,
        RetrievalInput(
            tags=["lang:python", "lib:sqlalchemy"],
            mode="create",
            token_budget=5000,
        ),
        id="pbook-retrieve-example",
        task_queue=PBOOK_TASK_QUEUE,
        result_type=RetrievalResult,
    )
    return result


result = asyncio.run(retrieve())
print(f"Returned {len(result.entries)} entries ({result.token_count} tokens)")
```

See [workflow reference](../reference/workflows.md) for the full `RetrievalWorkflow` contract.

## How to use create vs fix mode

The `mode` field on `RetrievalInput` controls how entries are ranked:

- **`create`** (default) -- Boosts general knowledge and API documentation. Use when generating new code or starting a new task.
- **`fix`** -- Boosts project-specific pitfalls and past failure records. Use when diagnosing an error or fixing a bug.

Set the mode in `RetrievalInput`:

```python
from __future__ import annotations

from pbook.models import RetrievalInput

# For new code generation
create_input = RetrievalInput(
    tags=["lib:sqlalchemy"],
    mode="create",
)

# For debugging a failure
fix_input = RetrievalInput(
    tags=["lib:sqlalchemy"],
    mode="fix",
    project="forge",
)
```

In fix mode, entries tagged with the same `project` receive additional ranking weight.

## How to control the token budget

`RetrievalInput.token_budget` limits the total token count of returned entries. The retrieval workflow ranks all candidates, then packs entries until the budget is exhausted. The default is 5000 tokens.

```python
from __future__ import annotations

from pbook.models import RetrievalInput

# Tight budget for focused context
small = RetrievalInput(tags=["lib:pydantic"], token_budget=2000)

# Generous budget for broad coverage
large = RetrievalInput(tags=["lang:python"], token_budget=10000)
```

The `RetrievalResult.token_count` field reports the actual token count of the packed entries, which will be at most `token_budget`.

## How to exclude unreviewed entries

Extracted entries are flagged `needs_review=True` until approved. To exclude them from retrieval results, set `approved_only=True`:

```python
from __future__ import annotations

from pbook.models import RetrievalInput

input = RetrievalInput(
    tags=["domain:testing"],
    approved_only=True,
)
```

Via CLI, use `--json` output and filter:

```
pbook list --tag domain:testing --json | jq '[.[] | select(.needs_review == false)]'
```

See [retrieval ranking](../explanation/retrieval-ranking.md) for how ranking scores are computed.
