# How to Integrate pbook with a Temporal Workflow

This guide shows how to call pbook from another Temporal worker and how to use pbook as a Python library without Temporal.

## How to call pbook workflows from another Temporal worker

Execute workflows on `pbook-task-queue` using cross-queue invocation. The pbook worker must be running.

```python
from __future__ import annotations

from uuid import uuid4

from temporalio.client import Client

from pbook.models import RetrievalInput, RetrievalMode


async def get_playbook_context(client: Client) -> list[dict]:
    result = await client.execute_workflow(
        "RetrievalWorkflow",
        RetrievalInput(
            tags=["lang:python", "lib:sqlalchemy"],
            mode=RetrievalMode.CREATE,
            token_budget=5000,
        ),
        id=f"pbook-retrieve-{uuid4().hex[:8]}",
        task_queue="pbook-task-queue",
    )
    return result.entries
```

For pushing experience after a task completes:

```python
import json

async def push_experience(client: Client, project: str, problem: str, resolution: str) -> int:
    result = await client.execute_workflow(
        "ExtractionWorkflow",
        json.dumps({
            "experiences": [{
                "project": project,
                "problem": problem,
                "resolution": resolution,
            }],
            "project": project,
        }),
        id=f"pbook-extract-{uuid4().hex[:8]}",
        task_queue="pbook-task-queue",
    )
    return result["entries_created"]
```

For submitting a manual entry with LLM review:

```python
async def submit_entry(client: Client, title: str, content: str, tags: list[str]) -> dict:
    result = await client.execute_workflow(
        "ManualEntryWorkflow",
        json.dumps({"title": title, "content": content, "tags": tags}),
        id=f"pbook-manual-{uuid4().hex[:8]}",
        task_queue="pbook-task-queue",
    )
    return result  # {"approved": bool, "entry": dict, ...}
```

Refer to the [Workflow Reference](../reference/workflows.md) for input/output models and timeouts.

## How to set up cross-queue workflow execution

1. Ensure the pbook worker is running on `pbook-task-queue`:

    ```bash
    pbook worker
    ```

2. Your client connects to the same Temporal server. Use `pydantic_data_converter` if passing Pydantic models:

    ```python
    from temporalio.client import Client
    from temporalio.contrib.pydantic import pydantic_data_converter

    client = await Client.connect(
        "localhost:7233",
        data_converter=pydantic_data_converter,
    )
    ```

3. Execute workflows with `task_queue="pbook-task-queue"`. The pbook worker handles execution; your client just submits and waits.

## How to use pbook as a Python library without Temporal

For lightweight queries that don't need workflow orchestration, call store functions directly:

```python
from __future__ import annotations

from pbook.activities.retrieval import rank_and_pack
from pbook.models import RetrievalMode
from pbook.store import get_db_path, get_engine, get_entries_by_tags, run_migrations

db_path = get_db_path()
run_migrations(db_path)
engine = get_engine(db_path)

entries = get_entries_by_tags(engine, ["lang:python", "lib:sqlalchemy"], limit=20)

packed, token_count = rank_and_pack(
    candidates=entries,
    query_tags=["lang:python", "lib:sqlalchemy"],
    mode=RetrievalMode.CREATE,
    token_budget=5000,
)
```

Tag inference is available as a pure function:

```python
from pbook.tags import infer_tags_from_context

tags = infer_tags_from_context(
    file_extensions=[".py"],
    description="Fix the database migration",
)
# ["domain:bug-fix", "domain:database", "domain:migration", "lang:python"]
```

Refer to the [Data Model Reference](../reference/data-model.md) for model field details.
