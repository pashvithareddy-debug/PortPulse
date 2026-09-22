# PortPulse

**"Why can't my application start? Which process is using this port?"**

PortPulse is a small Python CLI that answers that question in one command —
and, when you want it to, frees the port up for you.

```text
╭────────── PortPulse ──────────╮
│ PORT │ STATUS │ PROCESS │ PID │
├──────┼────────┼─────────┼─────┤
│ 3000 │ IN USE │ node    │5832 │
│ 5000 │ FREE   │ -       │ -   │
│ 8000 │ IN USE │ uvicorn │4217 │
│ 8080 │ FREE   │ -       │ -   │
╰───────────────────────────────╯
```

## Problem

You run `npm start` or `uvicorn main:app` and get `Address already in
use`. Now what? PortPulse tells you exactly what's squatting on the port —
name, PID, full command, and user — and can terminate it safely, with
confirmation.

## Features

- **Scan** a set of ports, a single port, or a whole range
- **Identify** the exact process (name, PID, command, user) behind a busy port
- **Kill** the offending process, with a confirmation prompt by default
- **Safety first**: refuses to touch known critical system processes, and
  re-verifies a process still owns a port immediately before killing it
- **TCP and UDP** support
- **JSON output** (`--json`) for scripting and CI
- **Predictable exit codes** for shell scripting
- **Zero-config** — sensible defaults, no setup required

## Architecture

```text
                    ┌──────────────┐
                    │    User      │
                    └──────┬───────┘
                           ▼
                    ┌──────────────┐
                    │     CLI      │
                    │   cli.py     │
                    └──────┬───────┘
             ┌─────────────┼─────────────┐
             ▼             ▼             ▼
       ┌──────────┐  ┌───────────┐  ┌───────────┐
       │ Scanner  │  │  Process  │  │ Formatter │
       │scanner.py│  │process.py │  │formatter.py│
       └────┬─────┘  └─────┬─────┘  └───────────┘
            ▼              ▼
       ┌─────────────────────────┐
       │     Operating System    │
       │   sockets / psutil      │
       └─────────────────────────┘
```

- `scanner.py` — decides whether a port is in use
- `process.py` — turns a PID into a name/command/user, and terminates
  processes safely
- `formatter.py` — renders results as a table or JSON
- `cli.py` — argument parsing and command wiring

### A note on the process backend

The original design called for shelling out to `lsof`. This implementation
uses [`psutil`](https://github.com/giampaolo/psutil) instead: it's a single
well-maintained dependency that works identically on Linux, macOS, and
Windows, and it avoids parsing `lsof`'s text output (whose columns differ
across platforms and versions). It also gives PortPulse a reliable way to
detect UDP sockets, which a bare TCP `connect()` probe can't do at all.

## Installation

```bash
git clone <this-repo>
cd PortPulse
pip install .
```

This installs the `portpulse` command. For local development instead:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

and run it as `python3 main.py <command>`.

## Usage

```bash
portpulse scan                        # scan the default ports
portpulse scan --ports 3000 8000      # scan specific ports
portpulse check 8000                  # check a single port, with full detail
portpulse range 8000 8100             # scan a port range
portpulse kill 8000                   # kill whatever is using port 8000
```

## Commands

| Command | Description |
|---|---|
| `scan [--ports P ...]` | Scan a set of ports (default: 3000, 5000, 8000, 8080) |
| `check <port>` | Show full detail for a single port |
| `range <start> <end>` | Scan every port in an inclusive range |
| `kill <port>` | Terminate the process using a port |

Flags available on every command: `--protocol {tcp,udp}` (default `tcp`),
`--json`, `--no-color`.

Flags specific to `kill`: `--yes` (skip confirmation), `--force` (escalate
to `SIGKILL` if the process ignores `SIGTERM`), `--allow-protected` (permit
killing a process PortPulse flags as critical).

## Examples

```bash
$ portpulse check 8000
Port 8000
Status: IN USE
Process: uvicorn
PID: 4217
User: alice
Command: python main.py

$ portpulse kill 8000
Port 8000 is being used by uvicorn (PID 4217)
Terminate this process? [y/N] y
Process terminated.
Port 8000 is now free.
```

## JSON output

```bash
$ portpulse scan --ports 8000 8080 --json
{
  "ports": [
    {
      "port": 8000,
      "protocol": "tcp",
      "status": "IN_USE",
      "pid": 4217,
      "process": "uvicorn",
      "command": "python main.py",
      "user": "alice"
    },
    {
      "port": 8080,
      "protocol": "tcp",
      "status": "FREE",
      "pid": null,
      "process": null,
      "command": null,
      "user": null
    }
  ]
}
```

## Exit codes

| Code | Meaning |
|---|---|
| `0` | Success — port free (`check`), or command completed normally |
| `1` | Port in use (`check`), or a kill/process problem |
| `2` | Invalid arguments (bad port number, unknown command) |
| `3` | Permission or system-level error |

```bash
portpulse check 8000
if [ $? -eq 0 ]; then
    echo "8000 is free, safe to start the server"
fi
```

## Safety

Killing processes is destructive, so PortPulse is conservative by default:

- **Confirms before killing.** `kill` always prompts unless you pass `--yes`.
- **Protects critical processes.** A short list of known system-critical
  process names (`init`, `systemd`, `sshd`, `explorer.exe`, etc.) and PIDs
  0/1 require an extra `--allow-protected` flag, even with `--yes`.
- **Re-checks ownership right before killing.** If the port changed hands
  between scan and kill (a race condition), PortPulse refuses and asks you
  to re-check rather than terminating the wrong process.
- **SIGTERM before SIGKILL.** PortPulse asks the process to exit cleanly
  first, and only escalates to `SIGKILL` if you pass `--force` and it
  doesn't exit in time.
- **Never requests elevated privileges automatically.** If a kill fails with
  a permission error, PortPulse tells you and stops — it won't try `sudo`
  on your behalf.

## Testing

```bash
pip install -r requirements.txt pytest
pytest -v
```

47 tests across the scanner, process, formatter, and CLI layers, including
real (not mocked) sockets and subprocesses:

- **Scanner**: free ports, occupied ports, invalid ports, ranges, multi-port batches
- **Process**: PID lookup, missing PIDs, protected-process refusal, kill,
  stale-PID race protection
- **Formatter**: table rendering, color/no-color, JSON structure
- **CLI**: every command, JSON mode, exit codes, invalid input

## Limitations

- UDP detection requires `psutil`; there's no fallback for it, since a raw
  socket probe can't reliably tell whether anything is listening on a UDP port.
- Listing all system sockets (used by `scan`/`range`/`check`) may require
  elevated privileges on some locked-down systems; PortPulse falls back to
  a slower per-port TCP probe in that case (no PID info) rather than failing.
- The protected-process list is a safety net, not a guarantee — always
  read the process name before confirming a kill.

## Future Improvements

- Optional `.portpulserc` config file for default ports, output format, and color preference
- `--watch` mode to continuously monitor a set of ports
- Richer protected-process detection based on parent PID / session leader status

## License

MIT — see [LICENSE](LICENSE).
