"""
process.py — Everything about turning a PID into useful, safe-to-act-on
information: process name, command, owner, and (carefully) termination.

Uses psutil where possible, with an lsof fallback on macOS when the OS
restricts socket/process inspection.
"""

from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass

import psutil


PROTECTED_PROCESS_NAMES = {
    "init",
    "systemd",
    "launchd",
    "kernel_task",
    "wininit.exe",
    "csrss.exe",
    "services.exe",
    "explorer.exe",
    "Xorg",
    "sshd",
    "loginwindow",
}

PROTECTED_PIDS = {0, 1}


class ProcessNotFoundError(Exception):
    """The PID no longer exists."""


class ProtectedProcessError(Exception):
    """Refusing to kill a process PortPulse considers critical."""


class PermissionDeniedError(Exception):
    """The OS refused to let us terminate this process."""


class StalePidError(Exception):
    """The PID no longer owns the port it supposedly owns."""


@dataclass
class ProcessInfo:
    pid: int
    name: str
    command: str
    user: str | None

    def to_dict(self) -> dict:
        return {
            "pid": self.pid,
            "name": self.name,
            "command": self.command,
            "user": self.user,
        }


def get_process_info(pid: int) -> ProcessInfo:
    """Look up name/command/user for a PID."""
    try:
        p = psutil.Process(pid)

        with p.oneshot():
            name = p.name()

            try:
                cmdline = p.cmdline()
                command = " ".join(cmdline) if cmdline else name
            except (psutil.AccessDenied, psutil.ZombieProcess):
                command = name

            try:
                user = p.username()
            except (psutil.AccessDenied, psutil.ZombieProcess):
                user = None

        return ProcessInfo(
            pid=pid,
            name=name,
            command=command,
            user=user,
        )

    except psutil.NoSuchProcess as exc:
        raise ProcessNotFoundError(
            f"No process with PID {pid}"
        ) from exc


def is_protected(pid: int, name: str) -> bool:
    """Whether this process should require extra care before killing."""
    return pid in PROTECTED_PIDS or name in PROTECTED_PROCESS_NAMES


def _lsof_pids_for_port(port: int, protocol: str) -> set[int]:
    """Find PIDs listening on a port using macOS lsof."""
    if protocol != "tcp":
        return set()

    try:
        result = subprocess.run(
            [
                "lsof",
                "-nP",
                f"-iTCP:{port}",
                "-sTCP:LISTEN",
                "-t",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return set()

    pids: set[int] = set()

    for line in result.stdout.splitlines():
        line = line.strip()
        if line.isdigit():
            pids.add(int(line))

    return pids


def _port_still_owned_by(pid: int, port: int, protocol: str) -> bool:
    """Re-check, right before killing, that `pid` still owns `port`."""
    try:
        conns = psutil.net_connections(kind=protocol)

        for c in conns:
            if c.pid == pid and c.laddr and c.laddr.port == port:
                if protocol == "udp" or c.status == psutil.CONN_LISTEN:
                    return True

        return False

    except (psutil.AccessDenied, PermissionError):
        # macOS can restrict psutil socket inspection.
        # Fall back to lsof instead of assuming the port is free.
        if protocol == "tcp":
            return pid in _lsof_pids_for_port(port, protocol)

        return False


def kill_process(
    pid: int,
    port: int | None = None,
    protocol: str = "tcp",
    force: bool = False,
    allow_protected: bool = False,
    timeout: float = 3.0,
) -> None:
    """Terminate a process safely."""
    try:
        p = psutil.Process(pid)
        name = p.name()

    except psutil.NoSuchProcess as exc:
        raise ProcessNotFoundError(
            f"No process with PID {pid}"
        ) from exc

    if is_protected(pid, name) and not allow_protected:
        raise ProtectedProcessError(
            f"PID {pid} ({name}) looks like a critical system process. "
            "Refusing to kill it without explicit confirmation."
        )

    if port is not None and not _port_still_owned_by(
        pid, port, protocol
    ):
        raise StalePidError(
            f"PID {pid} no longer owns port {port}. "
            "Re-scan before killing to avoid terminating "
            "the wrong process."
        )

    try:
        p.terminate()

        try:
            p.wait(timeout=timeout)

        except psutil.TimeoutExpired:
            if force:
                p.kill()
                p.wait(timeout=timeout)
            else:
                raise TimeoutError(
                    f"PID {pid} did not exit within {timeout}s "
                    "after SIGTERM. Retry with force=True "
                    "to send SIGKILL."
                )

    except psutil.NoSuchProcess:
        return

    except psutil.AccessDenied as exc:
        raise PermissionDeniedError(
            f"Permission denied terminating PID {pid} ({name}). "
            "Try running PortPulse with appropriate privileges."
        ) from exc