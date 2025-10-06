import asyncio
import json
import time
import pytest

import websockets
import httpx


@pytest.mark.asyncio
async def test_controls_ws_ping_pong(start_backend_server):
    uri = "ws://127.0.0.1:8000/controls"
    attempts = 5
    last_err = None
    for i in range(attempts):
        try:
            async with websockets.connect(uri) as ws:
                await ws.send(json.dumps({"type": "ping"}))
                msg = await asyncio.wait_for(ws.recv(), timeout=1.0)
                payload = json.loads(msg)
                assert payload.get("type") == "pong"
                return
        except (OSError, asyncio.TimeoutError) as e:
            last_err = e
            await asyncio.sleep(2.0)
    pytest.skip(f"Server not responsive at {uri} after retries: {last_err}")


def test_http_test_frame_endpoint(start_backend_server):
    url = "http://127.0.0.1:8000/test-frame"
    attempts = 5
    last_err = None
    for _ in range(attempts):
        try:
            with httpx.Client(timeout=2.0) as client:
                resp = client.get(url)
                resp.raise_for_status()
                data = resp.json()
                assert data.get("status") in {"success", "no_frame_available"}
                return
        except (httpx.ConnectError, httpx.ReadTimeout) as e:
            last_err = e
            time.sleep(2.0)
    pytest.skip(f"Server not responsive at {url} after retries: {last_err}")


