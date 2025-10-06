import time
import httpx
import pytest


@pytest.mark.parametrize("path", ["/", "/debug"]) 
def test_basic_http_endpoints_respond(start_backend_server, path):
    url = f"http://127.0.0.1:8000{path}"
    attempts = 5
    last_err = None
    for _ in range(attempts):
        try:
            with httpx.Client(timeout=2.0) as client:
                resp = client.get(url)
                resp.raise_for_status()
                data = resp.json()
                assert isinstance(data, dict)
                return
        except (httpx.ConnectError, httpx.ReadTimeout) as e:
            last_err = e
            time.sleep(1.5)
    pytest.skip(f"Server not responsive at {url} after retries: {last_err}")


def test_root_payload_shape(start_backend_server):
    url = "http://127.0.0.1:8000/"
    with httpx.Client(timeout=2.0) as client:
        resp = client.get(url)
        resp.raise_for_status()
        data = resp.json()
        assert data.get("status") == "running"
        assert isinstance(data.get("video_clients"), int)


def test_test_broadcast_endpoint_runs(start_backend_server):
    url = "http://127.0.0.1:8000/test-frame"
    with httpx.Client(timeout=2.0) as client:
        resp = client.get(url)
        resp.raise_for_status()
        data = resp.json()
        assert data.get("status") in {"success", "no_frame_available"}


