
# PortPulse

### A lightweight CLI for finding, inspecting, and safely freeing occupied ports.

PortPulse is a Python command-line tool that answers a common developer
problem:

> **"Why can't my application start, and which process is using this port?"**

Instead of manually searching through system processes, PortPulse scans
ports, identifies the process using them, displays useful process details,
and can safely terminate the process when explicitly requested.

---

## Demo

```text
╭────────────── PortPulse ──────────────╮
│ PORT │ STATUS │ PROCESS       │ PID   │
├──────┼────────┼───────────────┼───────┤
│ 3000 │ FREE   │ -             │ -     │
│ 5000 │ IN USE │ ControlCenter │ 1138  │
│ 8000 │ IN USE │ Python        │ 30396 │
│ 8080 │ FREE   │ -             │ -     │
╰───────────────────────────────────────╯
````

Example:

```text
$ portpulse kill 8000

Port 8000 is being used by Python (PID 30396)
Terminate this process? [y/N] y
Process terminated.
Port 8000 is now free.
```

---

## Why PortPulse?

A common development problem looks like this:

```text
Address already in use
Port 8000 is already occupied
```

This can happen when:

* a previous development server is still running
* a process crashed without releasing a port
* another application is using the same port
* multiple local servers are running simultaneously

PortPulse makes the investigation simple:

```text
Port
 ↓
Socket
 ↓
Process
 ↓
PID
 ↓
Process details
 ↓
Optional safe termination
```

---

## Features

* **Port scanning** for commonly used development ports
* **Single-port checking** for detailed inspection
* **Port-range scanning** for larger searches
* **TCP support**
* **UDP support**
* **Process identification**
* **PID identification**
* **Process command and user information**
* **Safe process termination**
* **Confirmation before killing processes**
* **Protected-process safeguards**
* **Race-condition protection**
* **SIGTERM before SIGKILL escalation**
* **JSON output for scripting and automation**
* **Predictable CLI exit codes**
* **macOS `lsof` fallback** when socket ownership is restricted
* **Cross-platform design** using Python and `psutil`
* **Automated testing with GitHub Actions**
* **Zero configuration for basic usage**

---

## Architecture

```text
                         ┌─────────────────┐
                         │      User       │
                         └────────┬────────┘
                                  │
                                  ▼
                         ┌─────────────────┐
                         │      CLI        │
                         │     cli.py      │
                         └────────┬────────┘
                                  │
              ┌───────────────────┼───────────────────┐
              │                   │                   │
              ▼                   ▼                   ▼
       ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
       │   Scanner   │     │   Process   │     │  Formatter  │
       │ scanner.py  │     │ process.py  │     │formatter.py │
       └──────┬──────┘     └──────┬──────┘     └─────────────┘
              │                   │
              │                   │
              ▼                   ▼
       ┌────────────────────────────────────┐
       │          Operating System          │
       │                                    │
       │  sockets • processes • networking  │
       └────────────────────────────────────┘
                    │
             ┌──────┴──────┐
             │             │
             ▼             ▼
          psutil         lsof
         primary       macOS fallback
```

### Component Responsibilities

#### `cli.py`

Handles:

* command-line arguments
* command routing
* confirmation prompts
* exit codes
* user-facing errors

#### `scanner.py`

Handles:

* port validation
* TCP scanning
* UDP scanning
* port-range scanning
* socket inspection
* macOS `lsof` fallback

#### `process.py`

Handles:

* PID inspection
* process name
* command
* user information
* protected-process detection
* ownership re-checking
* safe process termination

#### `formatter.py`

Handles:

* terminal table output
* JSON output
* color/no-color formatting

---

## Tech Stack

| Category                    | Technology            |
| --------------------------- | --------------------- |
| Language                    | Python                |
| Process & Socket Inspection | psutil                |
| macOS Fallback              | lsof                  |
| CLI                         | Python argparse       |
| Testing                     | pytest                |
| Packaging                   | Python pyproject.toml |
| Version Control             | Git + GitHub          |
| CI/CD                       | GitHub Actions        |
| License                     | MIT                   |

---

## Repository Structure

```text
PortPulse/
│
├── .github/
│   └── workflows/
│       └── tests.yml
│
├── portpulse/
│   ├── __init__.py
│   ├── cli.py
│   ├── formatter.py
│   ├── process.py
│   └── scanner.py
│
├── tests/
│   ├── __init__.py
│   ├── test_cli.py
│   ├── test_formatter.py
│   ├── test_process.py
│   └── test_scanner.py
│
├── main.py
├── pyproject.toml
├── requirements.txt
├── .gitignore
├── LICENSE
└── README.md
```

---

## Installation

### Clone the repository

```bash
git clone https://github.com/pashvithareddy-debug/PortPulse.git
cd PortPulse
```

### Create a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### Install dependencies

```bash
pip install -r requirements.txt
```

For development and testing:

```bash
pip install pytest
```

---

## Usage

### Scan default ports

```bash
python3 main.py scan
```

Default ports:

```text
3000
5000
8000
8080
```

### Scan specific ports

```bash
python3 main.py scan --ports 3000 8000 8080
```

### Check a single port

```bash
python3 main.py check 8000
```

Example:

```text
Port 8000
Status: IN USE
Process: Python
PID: 30396
User: ashvitha
Command: python3 -m http.server 8000
```

### Scan a port range

```bash
python3 main.py range 8000 8100
```

### Scan UDP ports

```bash
python3 main.py scan --protocol udp
```

### Kill the process using a port

```bash
python3 main.py kill 8000
```

PortPulse asks for confirmation:

```text
Port 8000 is being used by Python (PID 30396)
Terminate this process? [y/N] y
Process terminated.
Port 8000 is now free.
```

---

## Command Reference

| Command               | Purpose                                   |
| --------------------- | ----------------------------------------- |
| `scan`                | Scan a set of ports                       |
| `check <port>`        | Inspect a single port                     |
| `range <start> <end>` | Scan an inclusive port range              |
| `kill <port>`         | Safely terminate the process using a port |

### Common Options

```text
--protocol {tcp,udp}
--json
--no-color
```

### Kill Options

```text
--yes
--force
--allow-protected
```

#### `--yes`

Skip the confirmation prompt.

```bash
python3 main.py kill 8000 --yes
```

#### `--force`

Escalate from SIGTERM to SIGKILL if the process does not exit.

```bash
python3 main.py kill 8000 --force
```

#### `--allow-protected`

Explicitly permit termination of a process that PortPulse identifies as
protected.

```bash
python3 main.py kill 8000 --allow-protected
```

---

## JSON Output

PortPulse can produce machine-readable JSON for scripts and automation.

```bash
python3 main.py scan --json
```

Example:

```json
{
  "ports": [
    {
      "port": 8000,
      "protocol": "tcp",
      "status": "IN_USE",
      "pid": 30396,
      "process": "Python",
      "command": "python3 -m http.server 8000",
      "user": "ashvitha"
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

This makes PortPulse useful in:

* shell scripts
* development workflows
* CI pipelines
* automation tools
* debugging utilities

---

## Safety Design

Process termination is destructive, so PortPulse is deliberately
conservative.

### 1. Confirmation by default

The `kill` command asks for confirmation before terminating a process.

```text
Terminate this process? [y/N]
```

### 2. Protected processes

PortPulse maintains a list of known critical process names and protects
PIDs `0` and `1`.

Protected processes require explicit permission before termination.

### 3. Ownership re-check

Before terminating a process, PortPulse verifies that the PID still owns
the requested port.

This protects against a race condition where:

```text
Process A owns port 8000
        ↓
Process A exits
        ↓
Process B takes port 8000
        ↓
User confirms kill
```

PortPulse re-checks ownership before sending the termination signal.

### 4. SIGTERM before SIGKILL

PortPulse first requests a graceful shutdown using SIGTERM.

Only when `--force` is explicitly requested does it escalate to SIGKILL.

### 5. No automatic sudo

PortPulse never automatically requests elevated privileges.

If the operating system denies access, the tool reports the problem rather
than silently attempting privileged execution.

---

## macOS Socket Detection

macOS can restrict access to system socket information through `psutil`.

When this happens, PortPulse uses:

```text
psutil
   ↓
AccessDenied
   ↓
lsof fallback
   ↓
PID + port ownership
```

For example:

```text
Port 8000
    ↓
lsof
    ↓
Python
    ↓
PID 30396
```

This allows PortPulse to continue identifying TCP processes even when
`psutil` cannot access the required socket information.

For UDP, `psutil` remains necessary because UDP does not provide the same
connection handshake available to TCP.

---

## Exit Codes

| Code | Meaning                                                           |
| ---- | ----------------------------------------------------------------- |
| `0`  | Command completed successfully                                    |
| `1`  | Port is in use during `check`, or a process/kill operation failed |
| `2`  | Invalid command-line arguments                                    |
| `3`  | Permission or system-level error                                  |

Example:

```bash
python3 main.py check 8000

if [ $? -eq 0 ]; then
    echo "Port 8000 is free"
fi
```

---

## Testing

PortPulse includes automated tests covering the scanner, process layer,
formatter, and CLI.

Run:

```bash
python3 -m pytest -q
```

Current test result:

```text
47 passed
```

### Test Coverage Areas

#### Scanner

* free ports
* occupied ports
* invalid ports
* port ranges
* multiple ports
* TCP
* UDP

#### Process

* PID lookup
* process information
* missing PIDs
* protected-process detection
* process termination
* stale PID protection
* permission handling

#### Formatter

* terminal table rendering
* JSON formatting
* color/no-color output

#### CLI

* command parsing
* scan
* check
* range
* kill
* JSON mode
* exit codes
* invalid input

---

## Continuous Integration

PortPulse uses **GitHub Actions** to automatically run the test suite when
changes are pushed to the repository.

```text
Git push
   ↓
GitHub Actions
   ↓
Install dependencies
   ↓
Run pytest
   ↓
47 tests
   ↓
Pass / Fail
```

This helps ensure that future changes do not silently break existing
functionality.

---

## Limitations

* UDP detection requires `psutil`; there is no reliable raw-socket fallback
  for determining whether a UDP port is actually in use.
* Operating-system permissions can restrict access to socket ownership
  information.
* On macOS, PortPulse uses `lsof` as a fallback when `psutil` cannot inspect
  the required TCP socket information.
* If socket ownership cannot be determined, PortPulse may still determine
  that a TCP port is reachable without being able to identify its PID.
* The protected-process list is a safety mechanism, not a complete
  guarantee. Users should always inspect the process information before
  confirming termination.
* PortPulse is intended primarily as a local developer utility rather than
  a full network monitoring system.

---

## Future Improvements

Planned improvements include:

* `--watch` mode for continuous monitoring
* `.portpulserc` configuration
* configurable default ports
* configurable output preferences
* richer protected-process detection
* parent-process and session information
* improved cross-platform process discovery
* additional automated integration tests
* package publishing for easier installation

---

## Project Highlights

PortPulse demonstrates practical use of:

* Python
* CLI application design
* TCP/IP networking concepts
* UDP socket concepts
* Operating-system process management
* PID handling
* subprocess execution
* defensive programming
* race-condition prevention
* error handling
* JSON serialization
* automated testing
* Git and GitHub
* CI/CD with GitHub Actions

---

## Version Control

**Git + GitHub | Source code management and version control**

The project uses Git for:

* source-code versioning
* structured commits
* change tracking
* branch management

GitHub is used for:

* remote source-code hosting
* repository management
* collaboration
* continuous integration through GitHub Actions

---

## License

This project is licensed under the MIT License.

See [LICENSE](LICENSE) for details.

---

## Author

**Ashvitha Reddy**

Computer Science & Engineering Student

Built as a practical developer-tool project focused on networking,
operating-system process management, CLI development, and automation.





