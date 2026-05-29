"""Shared test fixtures for pbook.

Tests run against a real PostgreSQL server. By default an ephemeral local
cluster is started for the session (see ``tests/_pgcluster.py``); set
``PBOOK_TEST_DATABASE_URL`` to point the suite at an existing Postgres
instance (which must have the pgvector extension available) instead.

A single database is migrated once per session; each test gets a clean
slate via ``TRUNCATE`` and has ``PBOOK_DATABASE_URL`` pointed at it.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

import psycopg
import pytest
import sqlalchemy as sa

from pbook.store import get_database_url, get_engine, normalize_database_url, run_migrations

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

_TABLES = ("entries", "ingested_sessions", "entry_sources")


def _libpq_url(url: str) -> str:
    """Strip the SQLAlchemy driver suffix for a raw psycopg connection."""
    return url.replace("postgresql+psycopg://", "postgresql://")


@pytest.fixture(scope="session")
def _database_url() -> Iterator[str]:
    """Provide a migrated Postgres database URL for the whole session."""
    override = os.environ.get("PBOOK_TEST_DATABASE_URL")
    if override:
        url = normalize_database_url(override)
        run_migrations(url)
        yield url
        return

    from tests._pgcluster import PostgresCluster

    cluster = PostgresCluster()
    cluster.start()
    try:
        url = cluster.create_database("pbook_test")
        run_migrations(url)
        yield url
    finally:
        cluster.stop()


@pytest.fixture(autouse=True)
def _isolate_db(_database_url: str, monkeypatch: pytest.MonkeyPatch) -> None:
    """Point PBOOK_DATABASE_URL at a freshly-truncated database per test."""
    with psycopg.connect(_libpq_url(_database_url), autocommit=True) as conn:
        conn.execute(
            "TRUNCATE " + ", ".join(_TABLES) + " RESTART IDENTITY CASCADE",
        )
    monkeypatch.setenv("PBOOK_DATABASE_URL", _database_url)


@pytest.fixture(autouse=True)
def _dispose_store_engines(monkeypatch: pytest.MonkeyPatch):
    """Dispose SQLAlchemy engines created via pbook.store.get_engine after each test."""
    original_create_engine = sa.create_engine
    created_engines = []

    def tracking_create_engine(*args, **kwargs):
        engine = original_create_engine(*args, **kwargs)
        created_engines.append(engine)
        return engine

    monkeypatch.setattr(sa, "create_engine", tracking_create_engine)

    yield

    for engine in created_engines:
        engine.dispose()


@pytest.fixture(autouse=True)
def _bypass_cli_workflows(monkeypatch: pytest.MonkeyPatch):
    """Make ``pbook.cli._execute_workflow`` dispatch to the activity in-process.

    Production CLI commands submit workflows to a Temporal server. Tests
    don't want to spin one up; the activity-level path runs the same DB
    code, so behavior is faithful. This fixture replaces the workflow
    submission with a direct activity call keyed off the workflow's
    ``.run`` method.

    Workflows whose ``.run`` isn't in the map (e.g. RetrievalWorkflow,
    which has multiple activities) fall through to the real
    ``_execute_workflow`` and tests that need them spin up a real
    ``WorkflowEnvironment``.
    """
    import asyncio

    from pbook import cli
    from pbook.activities import cli_ops as activities
    from pbook.workflows import cli_ops as workflows

    mapping = {
        workflows.GetEntryWorkflow.run: activities.get_entry_activity,
        workflows.ListEntriesWorkflow.run: activities.list_entries_activity,
        workflows.ListSourcesWorkflow.run: activities.list_sources_activity,
        workflows.ListTagsWorkflow.run: activities.list_tags_activity,
        workflows.ReviewQueueWorkflow.run: activities.review_queue_activity,
        workflows.ListSessionsWorkflow.run: activities.list_sessions_activity,
        workflows.GetSessionTextWorkflow.run: activities.get_session_text_activity,
        workflows.CheckDuplicateWorkflow.run: activities.check_duplicate_activity,
        workflows.AddEntryWorkflow.run: activities.add_entry_activity,
        workflows.ApproveEntryWorkflow.run: activities.approve_entry_activity,
        workflows.RejectEntryWorkflow.run: activities.reject_entry_activity,
        workflows.UpdateEntryWorkflow.run: activities.update_entry_activity,
        workflows.RecordFeedbackWorkflow.run: activities.record_feedback_activity,
        workflows.PruneWorkflow.run: activities.prune_activity,
        workflows.FilterAlreadyIngestedWorkflow.run: activities.filter_already_ingested_activity,
        workflows.RecordStartedSessionsWorkflow.run: activities.record_started_sessions_activity,
    }

    real_execute = cli._execute_workflow

    def bypassed(workflow_fn, arg, *, id_prefix="pbook", temporal_address=""):
        activity_fn = mapping.get(workflow_fn)
        if activity_fn is None:
            return real_execute(
                workflow_fn, arg,
                id_prefix=id_prefix, temporal_address=temporal_address,
            )
        payload = arg.model_dump() if hasattr(arg, "model_dump") else arg
        return asyncio.run(activity_fn(payload))

    monkeypatch.setattr(cli, "_execute_workflow", bypassed)


def setup_db(tmp_path: Path):
    """Return ``(engine, url)`` for the per-test database.

    Kept for backward compatibility with tests that call it. The database
    is already migrated and truncated by the autouse fixtures; ``tmp_path``
    is accepted but unused.
    """
    url = get_database_url()
    assert url is not None
    engine = get_engine(url)
    return engine, url
