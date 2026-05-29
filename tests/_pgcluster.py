"""Ephemeral local PostgreSQL cluster for the test suite.

Spins up a throwaway PostgreSQL server (with the pgvector extension
available) in a temp directory, so tests run against real Postgres
without Docker. If ``PBOOK_TEST_DATABASE_URL`` is set, the suite uses
that server instead and this module is not needed.

initdb refuses to run as root, so when the test process is root we run
the server as the unprivileged ``postgres`` system user via ``runuser``.
"""

from __future__ import annotations

import contextlib
import os
import shutil
import socket
import subprocess
import tempfile
from pathlib import Path


def _find_pg_bin() -> Path:
    """Locate the PostgreSQL server binaries (initdb, pg_ctl)."""
    for candidate in ("initdb",):
        found = shutil.which(candidate)
        if found:
            return Path(found).parent
    # Debian/Ubuntu install server binaries outside PATH.
    for base in sorted(Path("/usr/lib/postgresql").glob("*/bin"), reverse=True):
        if (base / "initdb").exists():
            return base
    msg = "Could not find PostgreSQL server binaries (initdb/pg_ctl)."
    raise RuntimeError(msg)


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


class PostgresCluster:
    """Manage the lifecycle of a temporary PostgreSQL data directory."""

    def __init__(self) -> None:
        self._bin = _find_pg_bin()
        self._as_postgres_user = os.geteuid() == 0
        # When running as root the server runs as the unprivileged
        # ``postgres`` user, which must be able to traverse to the data
        # directory — the default TMPDIR may be a private (0700) dir, so
        # anchor under world-traversable /tmp in that case.
        base = "/tmp" if self._as_postgres_user else None
        self._datadir = Path(tempfile.mkdtemp(prefix="pbook-pgtest-", dir=base))
        self._port = _free_port()
        self._superuser = "postgres"

    def _run(self, args: list[str], *, capture: bool = True) -> None:
        cmd = [str(a) for a in args]
        if self._as_postgres_user:
            cmd = ["runuser", "-u", self._superuser, "--", *cmd]
        if capture:
            subprocess.run(cmd, check=True, capture_output=True)
        else:
            # The server daemon inherits its parent's stdio; if we left
            # pipes open here, the long-lived daemon would keep the write
            # end open and the call would block forever waiting for EOF.
            # Route to DEVNULL (the server logs go to ``-l`` instead).
            subprocess.run(
                cmd, check=True,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )

    def start(self) -> None:
        if self._as_postgres_user:
            # The unprivileged server user must own the data directory.
            shutil.chown(self._datadir, user=self._superuser, group=self._superuser)
        self._run([
            self._bin / "initdb",
            "-U", self._superuser,
            "-A", "trust",
            "-D", self._datadir,
        ])
        self._run(
            [
                self._bin / "pg_ctl",
                "-D", self._datadir,
                "-l", self._datadir / "server.log",
                "-o", f"-p {self._port} -c listen_addresses=127.0.0.1 "
                      f"-c unix_socket_directories={self._datadir}",
                "-w",
                "start",
            ],
            capture=False,
        )

    def stop(self) -> None:
        with contextlib.suppress(Exception):
            self._run([
                self._bin / "pg_ctl", "-D", self._datadir,
                "-w", "-m", "immediate", "stop",
            ])
        shutil.rmtree(self._datadir, ignore_errors=True)

    def create_database(self, name: str) -> str:
        """Create ``name`` and return its SQLAlchemy URL."""
        self._run([
            self._bin / "createdb",
            "-h", "127.0.0.1",
            "-p", str(self._port),
            "-U", self._superuser,
            name,
        ])
        return (
            f"postgresql+psycopg://{self._superuser}@127.0.0.1:{self._port}/{name}"
        )
