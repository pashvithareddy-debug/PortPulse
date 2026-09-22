"""
scanner.py — Port detection.
"""

from __future__ import annotations

import socket
import subprocess
from dataclasses import dataclass, field

try:
    import psutil

    HAVE_PSUTIL = True
except ImportError:  # pragma: no cover
    psutil = None  # type: ignore
    HAVE_PSUTIL = False

DEFAULT_PORTS = [3000, 5000, 8000, 8080]
MIN_PORT = 1
MAX_PORT = 65535


class InvalidPortError(ValueError):
    """Raised when a port number is outside the valid 1-65535 range."""


@dataclass
class PortResult:
    port: int
    protocol: str
    in_use: bool
    pid: int | None = None
    local_address: str | None = None

    def to_dict(self) -> dict:
        return {
            "port": self.port,
            "protocol": self.protocol,
            "status": "IN_USE" if self.in_use else "FREE",
            "pid": self.pid,
        }


def validate_port(port: int) -> None:
    if not isinstance(port, int) or isinstance(port, bool):
        raise InvalidPortError(f"port must be an integer, got {port!r}")
    if port < MIN_PORT or port > MAX_PORT:
        raise InvalidPortError(
            f"port must be between {MIN_PORT} and {MAX_PORT}, got {port}"
        )


def _psutil_kind(protocol: str) -> str:
    return "tcp" if protocol == "tcp" else "udp"


def _scan_tcp_with_lsof(ports: list[int]) -> dict[int, PortResult]:
    """Use macOS lsof when psutil cannot expose socket ownership."""
    results = {p: PortResult(p, "tcp", False) for p in ports}

    for port in ports:
        try:
            completed = subprocess.run(
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
            continue

        pids = [
            int(line.strip())
            for line in completed.stdout.splitlines()
            if line.strip().isdigit()
        ]

        if pids:
            results[port] = PortResult(
                port=port,
                protocol="tcp",
                in_use=True,
                pid=pids[0],
            )

    return results


def _scan_via_psutil(
    ports: list[int],
    protocol: str,
) -> dict[int, PortResult]:

    results: dict[int, PortResult] = {
        p: PortResult(p, protocol, False) for p in ports
    }

    wanted = set(ports)
    kind = _psutil_kind(protocol)

    try:
        conns = psutil.net_connections(kind=kind)

    except (psutil.AccessDenied, PermissionError):
        if protocol == "tcp":
            return _scan_tcp_with_lsof(ports)

        return results

    for c in conns:
        if not c.laddr:
            continue

        lport = c.laddr.port

        if lport not in wanted:
            continue

        is_relevant = (
            protocol == "udp"
            or c.status == psutil.CONN_LISTEN
        )

        if is_relevant:
            results[lport] = PortResult(
                port=lport,
                protocol=protocol,
                in_use=True,
                pid=c.pid,
                local_address=f"{c.laddr.ip}:{c.laddr.port}",
            )

    return results


def _probe_tcp_connect(
    port: int,
    host: str = "127.0.0.1",
    timeout: float = 0.3,
) -> PortResult:

    with socket.socket(
        socket.AF_INET,
        socket.SOCK_STREAM,
    ) as sock:

        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        in_use = result == 0

    return PortResult(
        port=port,
        protocol="tcp",
        in_use=in_use,
    )


def scan_ports(
    ports: list[int],
    protocol: str = "tcp",
) -> list[PortResult]:

    if protocol not in ("tcp", "udp"):
        raise ValueError(
            f"protocol must be 'tcp' or 'udp', got {protocol!r}"
        )

    for p in ports:
        validate_port(p)

    if not ports:
        return []

    if HAVE_PSUTIL:
        results = _scan_via_psutil(ports, protocol)

    elif protocol == "tcp":
        results = {
            p: _probe_tcp_connect(p)
            for p in ports
        }

    else:
        raise RuntimeError(
            "UDP scanning requires psutil, which is not installed. "
            "Install it with: pip install psutil"
        )

    return [results[p] for p in ports]


def scan_port(
    port: int,
    protocol: str = "tcp",
) -> PortResult:

    return scan_ports(
        [port],
        protocol=protocol,
    )[0]


def scan_range(
    start: int,
    end: int,
    protocol: str = "tcp",
) -> list[PortResult]:

    validate_port(start)
    validate_port(end)

    if start > end:
        raise InvalidPortError(
            f"range start ({start}) must be <= range end ({end})"
        )

    return scan_ports(
        list(range(start, end + 1)),
        protocol=protocol,
    )