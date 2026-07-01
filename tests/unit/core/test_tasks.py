"""
PATCH-1-01: Implementasi safe_create_task() helper
PATCH-1-02: Ganti semua bare create_task() dengan safe_create_task()
Verifikasi bahwa safe_create_task ada dan semua create_task sudah diganti.
"""

import pytest
import asyncio
import logging
import inspect
import os
import glob

from core.task_utils import safe_create_task


@pytest.mark.asyncio
class TestSafeCreateTask:
    """Checklist PATCH-1-01 & 1-02:
    - [x] core/task_utils.py ada dengan fungsi safe_create_task(coro, name, on_error)
    - [x] asyncio.create_task langsung (bare) sudah tidak ada kecuali di task_utils.py sendiri
    - [x] Error dalam task muncul di log (bukan silent)
    - [x] CancelledError tidak di-log sebagai error
    """

    async def test_safe_create_task_exists(self):
        """safe_create_task harus ada di core/task_utils.py."""
        assert callable(safe_create_task)

    async def test_safe_create_task_signature(self):
        """safe_create_task harus menerima coro, name, dan on_error."""
        sig = inspect.signature(safe_create_task)
        params = list(sig.parameters.keys())
        assert "coro" in params
        assert "name" in params
        assert "on_error" in params

    async def test_safe_create_task_returns_task(self):
        """safe_create_task harus mengembalikan asyncio.Task."""
        async def dummy_coro():
            return 42

        task = safe_create_task(dummy_coro(), name="test_task")
        assert isinstance(task, asyncio.Task)
        result = await task
        # but the task should complete without error

    async def test_safe_create_task_catches_errors(self, caplog):
        """Error di dalam task harus di-log, bukan silent crash."""
        async def failing_coro():
            raise ValueError("test error")

        with caplog.at_level(logging.ERROR):
            task = safe_create_task(failing_coro(), name="failing_test")
            await task

        assert any("test error" in record.message for record in caplog.records),            "Error harus muncul di log"

    async def test_safe_create_task_on_error_callback(self):
        """on_error callback harus dipanggil saat task crash."""
        error_received = []

        def on_error(e):
            error_received.append(e)

        async def failing_coro():
            raise RuntimeError("callback test")

        task = safe_create_task(failing_coro(), name="callback_test", on_error=on_error)
        await task

        assert len(error_received) == 1
        assert isinstance(error_received[0], RuntimeError)
        assert str(error_received[0]) == "callback test"

    async def test_safe_create_task_on_error_async_callback(self):
        """Async on_error callback harus juga didukung."""
        error_received = []

        async def on_error(e):
            error_received.append(e)

        async def failing_coro():
            raise RuntimeError("async callback test")

        task = safe_create_task(failing_coro(), name="async_callback_test", on_error=on_error)
        await task

        assert len(error_received) == 1
        assert isinstance(error_received[0], RuntimeError)

    async def test_safe_create_task_cancelled_error_not_logged(self, caplog):
        """CancelledError harus ditangani diam-diam (normal cancellation)."""
        async def slow_coro():
            await asyncio.sleep(100)

        with caplog.at_level(logging.ERROR):
            task = safe_create_task(slow_coro(), name="cancel_test")
            await asyncio.sleep(0) # Let the coroutine start before cancelling
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        error_logs = [r for r in caplog.records if "cancel_test" in r.message and r.levelno >= logging.ERROR]
        assert len(error_logs) == 0, "CancelledError TIDAK BOLEH di-log sebagai error"

    async def test_safe_create_task_with_name(self):
        """Task harus memiliki nama yang diset."""
        async def dummy():
            pass

        task = safe_create_task(dummy(), name="my_named_task")
        assert task.get_name() == "my_named_task"


class TestNoBareCreateTask:
    """Verifikasi bahwa semua asyncio.create_task() langsung sudah diganti."""

    def test_no_bare_create_task_in_codebase(self):
        """Tidak boleh ada asyncio.create_task() langsung di codebase
        kecuali di task_utils.py sendiri."""
        project_root = os.path.dirname(os.path.dirname(__file__))

        python_files = []
        for dirpath, dirnames, filenames in os.walk(project_root):
            dirnames[:] = [d for d in dirnames if d not in ("__pycache__", ".git", ".pytest_cache", "docs")]
            for f in filenames:
                if f.endswith(".py"):
                    python_files.append(os.path.join(dirpath, f))

        violations = []
        for filepath in python_files:
            # Skip task_utils.py itself
            if os.path.basename(filepath) == "task_utils.py":
                continue
            if "tests" in filepath.split(os.sep):
                continue
            if "conftest" in filepath:
                continue

            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                for line_no, line in enumerate(f, 1):
                    stripped = line.lstrip()
                    if stripped.startswith("#"):
                        continue
                    if "asyncio.create_task(" in stripped:
                        violations.append(f"{os.path.relpath(filepath, project_root)}:{line_no}: {stripped.strip()}")

        assert len(violations) == 0, (
            f"Ditemukan {len(violations)} bare asyncio.create_task() "
            f"yang belum diganti safe_create_task():\n" +
            "\n".join(violations)
        )
