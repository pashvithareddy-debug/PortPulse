import json

from portpulse import formatter


SAMPLE_ROWS = [
    {"port": 3000, "in_use": True, "process": "node", "pid": 5832},
    {"port": 5000, "in_use": False, "process": None, "pid": None},
    {"port": 8000, "in_use": True, "process": "uvicorn", "pid": 4217},
]


class TestFormatTable:
    def test_contains_all_ports(self):
        out = formatter.format_table(SAMPLE_ROWS, color=False)
        assert "3000" in out
        assert "5000" in out
        assert "8000" in out

    def test_free_port_shows_dash(self):
        out = formatter.format_table(SAMPLE_ROWS, color=False)
        assert "FREE" in out
        assert "IN USE" in out

    def test_no_color_has_no_ansi_codes(self):
        out = formatter.format_table(SAMPLE_ROWS, color=False)
        assert "\033[" not in out

    def test_color_adds_ansi_codes(self):
        out = formatter.format_table(SAMPLE_ROWS, color=True)
        assert "\033[" in out

    def test_empty_rows_still_renders_headers(self):
        out = formatter.format_table([], color=False)
        assert "PORT" in out
        assert "STATUS" in out


class TestFormatJson:
    def test_valid_json_output(self):
        out = formatter.format_json(SAMPLE_ROWS)
        parsed = json.loads(out)
        assert "ports" in parsed
        assert len(parsed["ports"]) == 3

    def test_round_trips_data(self):
        out = formatter.format_json(SAMPLE_ROWS)
        parsed = json.loads(out)
        assert parsed["ports"][0]["port"] == 3000
        assert parsed["ports"][0]["process"] == "node"


class TestFormatCheck:
    def test_includes_port_and_status(self):
        out = formatter.format_check(SAMPLE_ROWS[0], color=False)
        assert "Port 3000" in out
        assert "IN USE" in out

    def test_free_port_omits_process_fields(self):
        out = formatter.format_check(SAMPLE_ROWS[1], color=False)
        assert "Process:" not in out
        assert "PID:" not in out
