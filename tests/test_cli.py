import json
import socket

import pytest

from portpulse import cli


@pytest.fixture
def free_port():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


class TestCheckCommand:
    def test_check_free_port_exit_zero(self, free_port, capsys):
        code = cli.main(["check", str(free_port), "--no-color"])
        assert code == cli.EXIT_OK
        out = capsys.readouterr().out
        assert "FREE" in out

    def test_check_invalid_port_exit_two(self, capsys):
        code = cli.main(["check", "70000"])
        assert code == cli.EXIT_INVALID

    def test_check_json_output_is_valid(self, free_port, capsys):
        code = cli.main(["check", str(free_port), "--json"])
        assert code == cli.EXIT_OK
        out = capsys.readouterr().out
        parsed = json.loads(out)
        assert parsed["ports"][0]["port"] == free_port


class TestScanCommand:
    def test_scan_default_ports(self, capsys):
        code = cli.main(["scan", "--no-color"])
        assert code == cli.EXIT_OK
        out = capsys.readouterr().out
        assert "PortPulse" in out

    def test_scan_custom_ports(self, free_port, capsys):
        code = cli.main(["scan", "--ports", str(free_port), "--no-color"])
        assert code == cli.EXIT_OK
        out = capsys.readouterr().out
        assert str(free_port) in out


class TestRangeCommand:
    def test_range_reports_correct_count(self, capsys):
        code = cli.main(["range", "9000", "9004", "--json"])
        assert code == cli.EXIT_OK
        out = capsys.readouterr().out
        parsed = json.loads(out)
        assert len(parsed["ports"]) == 5

    def test_range_invalid_order_exit_two(self, capsys):
        code = cli.main(["range", "9000", "8000"])
        assert code == cli.EXIT_INVALID


class TestKillCommand:
    def test_kill_free_port_reports_nothing_to_kill(self, free_port, capsys):
        code = cli.main(["kill", str(free_port), "--yes"])
        assert code == cli.EXIT_PROBLEM
        out = capsys.readouterr().out
        assert "already free" in out


class TestArgparse:
    def test_missing_command_exits_nonzero(self):
        with pytest.raises(SystemExit) as exc_info:
            cli.main([])
        assert exc_info.value.code != 0

    def test_unknown_command_exits_nonzero(self):
        with pytest.raises(SystemExit):
            cli.main(["frobnicate"])
