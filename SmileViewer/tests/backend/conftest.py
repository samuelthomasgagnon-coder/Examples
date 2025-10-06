import os
import signal
import socket
import subprocess
import sys
import time

import pytest


def _wait_for_port(host: str, port: int, timeout: float = 5.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.25)
            try:
                sock.connect((host, port))
                return True
            except OSError:
                time.sleep(0.1)
    return False


@pytest.fixture(scope="session", autouse=False)
def start_backend_server():
    """Start FastAPI backend (server/server.py) for WS/HTTP tests.

    If the server cannot start (e.g., no camera available), tests using this fixture
    should skip gracefully.
    """
    host = os.environ.get("TEST_BACKEND_HOST", "127.0.0.1")
    port = int(os.environ.get("TEST_BACKEND_PORT", "8000"))

    # If something is already listening, assume it's the app
    if _wait_for_port(host, port, timeout=0.25):
        yield
        return

    env = os.environ.copy()
    # Launch the server from project root so relative imports work
    cmd = [sys.executable, "server/server.py", "--host", host, "--port", str(port)]
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    # Wait for startup (allow extra time for camera init, env warmup)
    if not _wait_for_port(host, port, timeout=12.0):
        # Could not start; dump a bit of output and skip
        try:
            out = proc.stdout.read(512).decode(errors="ignore") if proc.stdout else ""
        except Exception:
            out = ""
        proc.terminate()
        pytest.skip(f"Backend server failed to start on {host}:{port}. Output: {out}")

    try:
        yield
    finally:
        try:
            proc.send_signal(signal.SIGINT)
            try:
                proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                proc.kill()
        except Exception:
            pass


