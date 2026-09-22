"""
cli.py — PortPulse's command-line interface.

Commands:
    portpulse scan  [--ports P [P ...]] [--protocol tcp|udp] [--json] [--no-color]
    portpulse check <port> [--protocol tcp|udp] [--json] [--no-color]
    portpulse range <start> <end> [--protocol tcp|udp] [--json] [--no-color]
    portpulse kill  <port> [--yes] [--force] [--allow-protected] [--protocol tcp|udp]

Exit codes:
    0 -> success / port free / kill succeeded
    1 -> port in use (check) / process or port problem (kill)
    2 -> invalid arguments
    3 -> permission or system error
"""

from __future__ import annotations

import argparse
import sys

from . import formatter, process, scanner

EXIT_OK = 0
EXIT_PROBLEM = 1
EXIT_INVALID = 2
EXIT_SYSTEM_ERROR = 3


def _use_color(args: argparse.Namespace) -> bool:
    if args.no_color:
        return False
    return sys.stdout.isatty()


def _enrich_row(result: scanner.PortResult) -> dict:
    """Attach process name/command/user to a scan result, when available."""
    row = result.to_dict()
    row["in_use"] = result.in_use
    row["process"] = None
    row["command"] = None
    row["user"] = None
    if result.in_use and result.pid:
        try:
            info = process.get_process_info(result.pid)
            row["process"] = info.name
            row["command"] = info.command
            row["user"] = info.user
        except process.ProcessNotFoundError:
            # Process exited between the scan and this lookup; report
            # what we know rather than crashing.
            pass
    return row


def _print_rows(rows: list[dict], args: argparse.Namespace) -> None:
    if args.json:
        print(formatter.format_json(rows))
    else:
        print(formatter.format_table(rows, color=_use_color(args)))


def cmd_scan(args: argparse.Namespace) -> int:
    ports = args.ports or scanner.DEFAULT_PORTS
    try:
        results = scanner.scan_ports(ports, protocol=args.protocol)
    except scanner.InvalidPortError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return EXIT_INVALID
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return EXIT_SYSTEM_ERROR

    rows = [_enrich_row(r) for r in results]
    _print_rows(rows, args)
    return EXIT_OK


def cmd_range(args: argparse.Namespace) -> int:
    try:
        results = scanner.scan_range(args.start, args.end, protocol=args.protocol)
    except scanner.InvalidPortError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return EXIT_INVALID
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return EXIT_SYSTEM_ERROR

    rows = [_enrich_row(r) for r in results]
    _print_rows(rows, args)
    return EXIT_OK


def cmd_check(args: argparse.Namespace) -> int:
    try:
        result = scanner.scan_port(args.port, protocol=args.protocol)
    except scanner.InvalidPortError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return EXIT_INVALID
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return EXIT_SYSTEM_ERROR

    row = _enrich_row(result)
    if args.json:
        print(formatter.format_json([row]))
    else:
        print(formatter.format_check(row, color=_use_color(args)))
    return EXIT_PROBLEM if result.in_use else EXIT_OK


def cmd_kill(args: argparse.Namespace) -> int:
    try:
        result = scanner.scan_port(args.port, protocol=args.protocol)
    except scanner.InvalidPortError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return EXIT_INVALID

    if not result.in_use or not result.pid:
        print(f"Port {args.port} is already free. Nothing to kill.")
        return EXIT_PROBLEM

    try:
        info = process.get_process_info(result.pid)
    except process.ProcessNotFoundError:
        print(
            f"Port {args.port} was in use by PID {result.pid}, but that "
            "process has already exited."
        )
        return EXIT_PROBLEM

    print(f"Port {args.port} is being used by {info.name} (PID {info.pid})")

    is_protected = process.is_protected(info.pid, info.name)
    if is_protected and not args.allow_protected:
        print(
            f"\n{info.name} (PID {info.pid}) looks like a critical system "
            "process. PortPulse refuses to kill it.\n"
            "If you're absolutely sure, re-run with --allow-protected.",
            file=sys.stderr,
        )
        return EXIT_PROBLEM

    if not args.yes:
        prompt = "Terminate this process? [y/N] "
        if is_protected:
            prompt = (
                f"⚠️  {info.name} looks like a critical system process.\n"
                "Terminate it anyway? [y/N] "
            )
        answer = input(prompt).strip().lower()
        if answer not in ("y", "yes"):
            print("Aborted. No process was terminated.")
            return EXIT_OK

    try:
        process.kill_process(
            pid=info.pid,
            port=args.port,
            protocol=args.protocol,
            force=args.force,
            allow_protected=args.allow_protected,
        )
    except process.ProcessNotFoundError:
        print(f"PID {info.pid} had already exited. Port {args.port} is free.")
        return EXIT_OK
    except process.ProtectedProcessError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return EXIT_PROBLEM
    except process.StalePidError as exc:
        print(
            f"Error: {exc}\nRun 'portpulse check {args.port}' again to see "
            "who owns it now.",
            file=sys.stderr,
        )
        return EXIT_PROBLEM
    except process.PermissionDeniedError as exc:
        print(f"\n{exc}", file=sys.stderr)
        return EXIT_SYSTEM_ERROR
    except TimeoutError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return EXIT_PROBLEM

    print("Process terminated.")
    print(f"Port {args.port} is now free.")
    return EXIT_OK


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="portpulse",
        description="Find out what's using your ports, and free them up.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument(
        "--protocol", choices=["tcp", "udp"], default="tcp", help="protocol to scan (default: tcp)"
    )
    common.add_argument("--json", action="store_true", help="output as JSON")
    common.add_argument("--no-color", action="store_true", help="disable colored output")

    p_scan = sub.add_parser("scan", parents=[common], help="scan a set of ports")
    p_scan.add_argument(
        "--ports", type=int, nargs="+", default=None, metavar="PORT",
        help=f"ports to scan (default: {scanner.DEFAULT_PORTS})",
    )
    p_scan.set_defaults(func=cmd_scan)

    p_check = sub.add_parser("check", parents=[common], help="check a single port")
    p_check.add_argument("port", type=int, help="port number to check")
    p_check.set_defaults(func=cmd_check)

    p_range = sub.add_parser("range", parents=[common], help="scan a range of ports")
    p_range.add_argument("start", type=int, help="first port in range")
    p_range.add_argument("end", type=int, help="last port in range (inclusive)")
    p_range.set_defaults(func=cmd_range)

    p_kill = sub.add_parser("kill", parents=[common], help="terminate the process using a port")
    p_kill.add_argument("port", type=int, help="port whose process should be killed")
    p_kill.add_argument("--yes", action="store_true", help="skip the confirmation prompt")
    p_kill.add_argument(
        "--force", action="store_true",
        help="escalate to SIGKILL if the process doesn't exit after SIGTERM",
    )
    p_kill.add_argument(
        "--allow-protected", action="store_true",
        help="allow killing processes PortPulse flags as critical system processes",
    )
    p_kill.set_defaults(func=cmd_kill)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except KeyboardInterrupt:
        print("\nInterrupted.", file=sys.stderr)
        return EXIT_SYSTEM_ERROR
    except Exception as exc:  # last-resort guard: never show a raw traceback
        print(f"Unexpected error: {exc}", file=sys.stderr)
        return EXIT_SYSTEM_ERROR


if __name__ == "__main__":
    sys.exit(main())
