import os
import socket
import subprocess
import sys
import time

import psutil
import pytest

from portpulse import process


@pytest.fixture
def child_process():
    """Spawn a real short-lived child process we're allowed to kill in tests."""
    proc = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(30)"],
    )
    time.sleep(0.1)  # let it actually start
    yield proc
    if proc.poll() is None:
        proc.kill()
        proc.wait(timeout=2)


class TestGetProcessInfo:
    def test_current_process(self):
        info = process.get_process_info(os.getpid())
        assert info.pid == os.getpid()
        assert info.name  # non-empty

    def test_child_process(self, child_process):
        info = process.get_process_info(child_process.pid)
        assert info.pid == child_process.pid
        assert "python" in info.name.lower() or "python" in info.command.lower()

    def test_missing_pid_raises(self):
        # A PID that (almost certainly) doesn't exist.
        fake_pid = 999_999
        while psutil.pid_exists(fake_pid):
            fake_pid -= 1
        with pytest.raises(process.ProcessNotFoundError):
            process.get_process_info(fake_pid)


class TestIsProtected:
    def test_pid_zero_protected(self):
        assert process.is_protected(0, "anything") is True

    def test_pid_one_protected(self):
        assert process.is_protected(1, "anything") is True

    def test_known_protected_name(self):
        assert process.is_protected(12345, "systemd") is True

    def test_ordinary_process_not_protected(self):
        assert process.is_protected(12345, "uvicorn") is False


class TestKillProcess:
    def test_kill_ordinary_child(self, child_process):
        process.kill_process(child_process.pid)
        child_process.wait(timeout=3)
        assert child_process.poll() is not None  # it exited

    def test_kill_missing_pid_raises(self):
        fake_pid = 999_999
        while psutil.pid_exists(fake_pid):
            fake_pid -= 1
        with pytest.raises(process.ProcessNotFoundError):
            process.kill_process(fake_pid)

    def test_kill_protected_pid_refused(self):
        with pytest.raises(process.ProtectedProcessError):
            process.kill_process(1)

    def test_kill_with_stale_port_raises(self, child_process):
        # child_process isn't listening on any port, so claiming it owns
        # one should trigger the race-condition guard.
        with pytest.raises(process.StalePidError):
            process.kill_process(child_process.pid, port=59999, protocol="tcp")
