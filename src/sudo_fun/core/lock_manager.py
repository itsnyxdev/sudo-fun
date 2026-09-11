"""Persistent lock and failure counter management with SQLite."""

from __future__ import annotations

import os
import sqlite3
import time
from pathlib import Path
from typing import Optional


DEFAULT_LOCK_DURATION_SECONDS = 600.0  # 10 minutes
MAX_CONSECUTIVE_FAILURES = 3


def get_default_state_dir() -> Path:
    """Returns the XDG-compliant state directory for sudo-fun with 0700 permissions."""
    xdg_state_home = os.environ.get("XDG_STATE_HOME")
    if xdg_state_home:
        base = Path(xdg_state_home)
    else:
        base = Path.home() / ".local" / "state"

    state_dir = base / "sudo-fun"
    state_dir.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(state_dir, 0o700)
    except OSError:
        pass
    return state_dir


class LockManager:
    """Thread-safe and process-safe persistent failure and lock manager."""

    def __init__(self, db_path: Optional[Path] = None):
        if db_path is None:
            self.db_path = get_default_state_dir() / "state.db"
        else:
            self.db_path = Path(db_path)
            self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(
            str(self.db_path),
            timeout=10.0,
            isolation_level=None,  # Autocommit mode, we manage transactions explicitly
        )
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA busy_timeout=5000;")
        return conn

    def _init_db(self) -> None:
        """Initializes database schema and secures file permissions."""
        if not self.db_path.exists():
            # Create file with restrictive permissions (0600)
            self.db_path.touch(mode=0o600, exist_ok=True)
        try:
            os.chmod(self.db_path, 0o600)
        except OSError:
            pass

        with self._get_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS command_state (
                    command_identity TEXT PRIMARY KEY,
                    consecutive_fails INTEGER NOT NULL DEFAULT 0,
                    lock_until REAL,
                    active_audio_pid INTEGER,
                    last_attempt REAL NOT NULL
                );
                """
            )

    def get_lock_remaining(self, command_identity: str) -> Optional[float]:
        """Checks if the command is currently locked.

        Returns:
            Remaining lock time in seconds, or None if not locked / expired.
        """
        now = time.time()
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT lock_until FROM command_state WHERE command_identity = ?",
                (command_identity,),
            )
            row = cursor.fetchone()
            if not row or row[0] is None:
                return None

            lock_until = float(row[0])
            if lock_until > now:
                return lock_until - now

            # Lock has expired. Clean up lock state and reset failure count
            conn.execute(
                """
                UPDATE command_state
                SET lock_until = NULL, consecutive_fails = 0, active_audio_pid = NULL
                WHERE command_identity = ?
                """,
                (command_identity,),
            )
            return None

    def record_failure(
        self,
        command_identity: str,
        lock_duration: float = DEFAULT_LOCK_DURATION_SECONDS,
    ) -> tuple[int, bool, float]:
        """Records a challenge failure atomically.

        Returns:
            tuple: (new_fail_count, is_locked, lock_remaining_seconds)
        """
        now = time.time()
        with self._get_connection() as conn:
            conn.execute("BEGIN IMMEDIATE;")
            cursor = conn.execute(
                "SELECT consecutive_fails, lock_until FROM command_state WHERE command_identity = ?",
                (command_identity,),
            )
            row = cursor.fetchone()

            if row is None:
                current_fails = 0
            else:
                current_fails = int(row[0])
                # If there was an expired lock, reset count
                if row[1] is not None and float(row[1]) <= now:
                    current_fails = 0

            new_fails = current_fails + 1
            is_locked = False
            lock_until = None
            lock_remaining = 0.0

            if new_fails >= MAX_CONSECUTIVE_FAILURES:
                is_locked = True
                lock_until = now + lock_duration
                lock_remaining = lock_duration

            conn.execute(
                """
                INSERT INTO command_state (command_identity, consecutive_fails, lock_until, last_attempt)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(command_identity) DO UPDATE SET
                    consecutive_fails = excluded.consecutive_fails,
                    lock_until = excluded.lock_until,
                    last_attempt = excluded.last_attempt
                """,
                (command_identity, new_fails, lock_until, now),
            )
            conn.execute("COMMIT;")

            return new_fails, is_locked, lock_remaining

    def record_success(self, command_identity: str) -> None:
        """Resets the consecutive failure counter on successful challenge completion."""
        now = time.time()
        with self._get_connection() as conn:
            conn.execute("BEGIN IMMEDIATE;")
            conn.execute(
                """
                INSERT INTO command_state (command_identity, consecutive_fails, lock_until, active_audio_pid, last_attempt)
                VALUES (?, 0, NULL, NULL, ?)
                ON CONFLICT(command_identity) DO UPDATE SET
                    consecutive_fails = 0,
                    lock_until = NULL,
                    active_audio_pid = NULL,
                    last_attempt = excluded.last_attempt
                """,
                (command_identity, now),
            )
            conn.execute("COMMIT;")

    def get_active_audio_pid(self, command_identity: str) -> Optional[int]:
        """Returns active audio player PID if currently alive, otherwise cleans up."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT active_audio_pid FROM command_state WHERE command_identity = ?",
                (command_identity,),
            )
            row = cursor.fetchone()
            if not row or row[0] is None:
                return None

            pid = int(row[0])
            if self._is_pid_alive(pid):
                return pid

            # Stale PID, clear it
            conn.execute(
                "UPDATE command_state SET active_audio_pid = NULL WHERE command_identity = ?",
                (command_identity,),
            )
            return None

    def set_active_audio_pid(self, command_identity: str, pid: int) -> None:
        """Stores the active background audio player process ID."""
        with self._get_connection() as conn:
            conn.execute(
                "UPDATE command_state SET active_audio_pid = ? WHERE command_identity = ?",
                (pid, command_identity),
            )

    def clear_lock(self, command_identity: str) -> None:
        """Administratively clears a command lock and resets failure count."""
        with self._get_connection() as conn:
            conn.execute(
                """
                UPDATE command_state
                SET lock_until = NULL, consecutive_fails = 0, active_audio_pid = NULL
                WHERE command_identity = ?
                """,
                (command_identity,),
            )

    @staticmethod
    def _is_pid_alive(pid: int) -> bool:
        """Checks if a process with the given PID is alive."""
        if pid <= 0:
            return False
        try:
            os.kill(pid, 0)
            return True
        except (ProcessLookupError, PermissionError):
            return False
