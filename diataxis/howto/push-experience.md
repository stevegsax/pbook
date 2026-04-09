# How to Push Experience Data

## How to push experience data via CLI

Create a JSON file with the experience fields:

```json
{
    "project": "forge",
    "problem": "Temporal activities using pydantic-ai run_sync fail with 'event loop already running' inside async activity functions.",
    "resolution": "Replace run_sync() with await agent.run() in async activity implementations. run_sync calls asyncio.run_until_complete(), which cannot be nested inside an existing event loop.",
    "context": "The Temporal Python SDK runs activities in an async event loop. pydantic-ai's run_sync is designed for synchronous call sites only.",
    "metadata": {
        "library": "pydantic-ai",
        "version": "0.1.x"
    }
}
```

Push it to the extraction workflow:

```
pbook push --file experience.json
```

Output:

```
Extraction complete: 1 entries created.
```

The file can also contain a JSON array to push multiple experiences at once:

```json
[
    {
        "project": "forge",
        "problem": "First problem description.",
        "resolution": "First resolution."
    },
    {
        "project": "forge",
        "problem": "Second problem description.",
        "resolution": "Second resolution."
    }
]
```

Extracted entries are created with `needs_review=True`. Use `pbook review` and `pbook approve <id>` to promote them to the active knowledge base.

## How to push experience via Temporal workflow

Call `ExtractionWorkflow` directly from Python:

```python
from __future__ import annotations

import asyncio
import json
import time

from temporalio.client import Client

from pbook.workflows.extraction import ExtractionWorkflow

PBOOK_TASK_QUEUE = "pbook-task-queue"


async def push_experience() -> dict:
    client = await Client.connect("localhost:7233")

    experiences = [
        {
            "project": "forge",
            "problem": "OTel set_tracer_provider uses a set-once guard that prevents resetting in tests.",
            "resolution": "Reset once._done = False under once._lock before calling set_tracer_provider again in test fixtures.",
            "context": "The logfire pytest plugin may also interfere with OTel global state.",
        }
    ]

    result = await client.execute_workflow(
        ExtractionWorkflow.run,
        json.dumps({
            "experiences": experiences,
            "project": "forge",
        }),
        id=f"pbook-extract-{int(time.time())}",
        task_queue=PBOOK_TASK_QUEUE,
    )
    return result


result = asyncio.run(push_experience())
print(f"Entries created: {result['entries_created']}")
```

The workflow input is a JSON string with two keys: `experiences` (a list of experience dicts) and `project` (the source project name).

## How to structure the PushExperienceInput

The quality of extracted entries depends on the quality of the input. `PushExperienceInput` has five fields:

| Field | Required | Description |
|---|---|---|
| `project` | yes | Project that generated this experience |
| `problem` | yes | What unexpected situation occurred |
| `resolution` | yes | How it was resolved |
| `context` | no | Relevant context (code, errors, stack traces) |
| `metadata` | no | Arbitrary key-value pairs (library versions, environment details) |

Structure your input with a specific problem, specific resolution, and relevant context. Vague descriptions like "code didn't work" produce no useful extraction.

For detailed guidance on what makes good experience data, see [Understanding the Quality Bar](../explanation/quality-bar.md). See [data model reference](../reference/data-model.md) for the full `PushExperienceInput` schema.
