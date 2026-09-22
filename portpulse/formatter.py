"""
formatter.py — Turns PortResult / ProcessInfo objects into human-readable
tables or machine-readable JSON. No scanning or process logic lives here.
"""

from __future__ import annotations

import json

# ANSI colors. Kept minimal and disabled entirely by --no-color or when
# stdout isn't a terminal (handled by the caller).
_GREEN = "\033[32m"
_RED = "\033[31m"
_DIM = "\033[2m"
_BOLD = "\033[1m"
_RESET = "\033[0m"


def _status_text(in_use: bool, color: bool) -> str:
    label = "IN USE" if in_use else "FREE"
    if not color:
        return label
    return f"{_RED if in_use else _GREEN}{label}{_RESET}"


def format_table(rows: list[dict], color: bool = True) -> str:
    """Render a list of row-dicts (port, status, process, pid) as a boxed table.

    Each row dict may have keys: port, status(bool: in_use), process, pid.
    Missing process/pid render as "-".
    """
    headers = ["PORT", "STATUS", "PROCESS", "PID"]
    display_rows = []
    for r in rows:
        display_rows.append(
            [
                str(r.get("port", "-")),
                _status_text(bool(r.get("in_use")), color=False),  # measure without color codes
                r.get("process") or "-",
                str(r.get("pid")) if r.get("pid") else "-",
            ]
        )

    widths = [len(h) for h in headers]
    for row in display_rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(cell))

    def sep(left: str, mid: str, right: str, fill: str = "─") -> str:
        return left + mid.join(fill * (w + 2) for w in widths) + right

    def fmt_row(cells: list[str], bold: bool = False) -> str:
        parts = []
        for cell, w in zip(cells, widths):
            padded = f" {cell:<{w}} "
            parts.append(padded)
        line = "│" + "│".join(parts) + "│"
        if bold and color:
            return f"{_BOLD}{line}{_RESET}"
        return line

    lines = []
    title = " PortPulse "
    total_width = sum(w + 2 for w in widths) + (len(widths) - 1)
    lines.append("╭" + title.center(total_width, "─") + "╮")
    lines.append(fmt_row(headers, bold=True))
    lines.append(sep("├", "┼", "┤"))
    for r, row in zip(rows, display_rows):
        if color:
            status_colored = _status_text(bool(r.get("in_use")), color=True)
            pad = " " * max(0, widths[1] - len(row[1]))
            row = [row[0], status_colored + pad, row[2], row[3]]
        lines.append(fmt_row(row))
    lines.append("╰" + "─" * total_width + "╯")
    return "\n".join(lines)


def format_json(rows: list[dict]) -> str:
    """Render rows as pretty-printed JSON: {"ports": [...]}."""
    payload = {"ports": rows}
    return json.dumps(payload, indent=2)


def format_check(row: dict, color: bool = True) -> str:
    """Render a single-port `check` result as a short human-readable block."""
    lines = [f"Port {row.get('port')}"]
    lines.append(f"Status: {_status_text(bool(row.get('in_use')), color=color)}")
    if row.get("process"):
        lines.append(f"Process: {row['process']}")
    if row.get("pid"):
        lines.append(f"PID: {row['pid']}")
    if row.get("user"):
        lines.append(f"User: {row['user']}")
    if row.get("command") and row.get("command") != row.get("process"):
        lines.append(f"Command: {row['command']}")
    return "\n".join(lines)
