import socket
import threading
import time

import pytest

from portpulse import scanner


@pytest.fixture
def free_port():
    """Find a port that's currently free by briefly binding to port 0."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


@pytest.fixture
def occupied_tcp_port():
    """Start a real listening TCP server and yield its port; clean up after."""
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("127.0.0.1", 0))
    server.listen(1)
    port = server.getsockname()[1]

    stop = threading.Event()

    def serve():
        server.settimeout(0.1)
        while not stop.is_set():
            try:
                conn, _ = server.accept()
                conn.close()
            except socket.timeout:
                continue

    t = threading.Thread(target=serve, daemon=True)
    t.start()
    time.sleep(0.05)  # let the listener actually bind before the test uses it

    yield port

    stop.set()
    t.join(timeout=1)
    server.close()


class TestValidatePort:
    def test_valid_port(self):
        scanner.validate_port(8000)  # should not raise

    def test_min_boundary(self):
        scanner.validate_port(1)

    def test_max_boundary(self):
        scanner.validate_port(65535)

    def test_zero_is_invalid(self):
        with pytest.raises(scanner.InvalidPortError):
            scanner.validate_port(0)

    def test_negative_is_invalid(self):
        with pytest.raises(scanner.InvalidPortError):
            scanner.validate_port(-1)

    def test_too_large_is_invalid(self):
        with pytest.raises(scanner.InvalidPortError):
            scanner.validate_port(65536)

    def test_non_int_is_invalid(self):
        with pytest.raises(scanner.InvalidPortError):
            scanner.validate_port("8000")  # type: ignore[arg-type]


class TestScanPort:
    def test_occupied_port_detected(self, occupied_tcp_port):
        result = scanner.scan_port(occupied_tcp_port, protocol="tcp")
        assert result.in_use is True
        assert result.port == occupied_tcp_port

    def test_free_port_detected(self, free_port):
        result = scanner.scan_port(free_port, protocol="tcp")
        assert result.in_use is False

    def test_invalid_port_raises(self):
        with pytest.raises(scanner.InvalidPortError):
            scanner.scan_port(70000)

    def test_invalid_protocol_raises(self):
        with pytest.raises(ValueError):
            scanner.scan_port(8000, protocol="sctp")


class TestScanPorts:
    def test_multiple_ports_mixed(self, occupied_tcp_port, free_port):
        results = scanner.scan_ports([occupied_tcp_port, free_port])
        by_port = {r.port: r for r in results}
        assert by_port[occupied_tcp_port].in_use is True
        assert by_port[free_port].in_use is False

    def test_empty_list_returns_empty(self):
        assert scanner.scan_ports([]) == []

    def test_preserves_order(self, occupied_tcp_port, free_port):
        results = scanner.scan_ports([free_port, occupied_tcp_port])
        assert [r.port for r in results] == [free_port, occupied_tcp_port]


class TestScanRange:
    def test_range_includes_occupied_port(self, occupied_tcp_port):
        start = occupied_tcp_port
        end = occupied_tcp_port + 2
        results = scanner.scan_range(start, end)
        assert len(results) == end - start + 1
        assert any(r.port == occupied_tcp_port and r.in_use for r in results)

    def test_range_start_after_end_raises(self):
        with pytest.raises(scanner.InvalidPortError):
            scanner.scan_range(9000, 8000)

    def test_range_out_of_bounds_raises(self):
        with pytest.raises(scanner.InvalidPortError):
            scanner.scan_range(1, 70000)
