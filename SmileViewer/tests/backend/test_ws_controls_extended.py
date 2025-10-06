import asyncio
import json
import pytest
import websockets


@pytest.mark.asyncio
async def test_settings_roundtrip_and_broadcast(start_backend_server):
    uri = "ws://127.0.0.1:8000/controls"
    # Connect two clients
    async with websockets.connect(uri) as ws1, websockets.connect(uri) as ws2:
        # Ask for current settings on ws2 to drain initial traffic
        await ws2.send(json.dumps({"type": "get_settings"}))
        # ws1 updates a setting
        await ws1.send(json.dumps({"type": "set_state", "key": "DRAW_FACE_BB", "value": True}))

        # ws2 should receive a settings_update (but ws1 should not echo to itself)
        payload = None
        for _ in range(10):
            try:
                msg = await asyncio.wait_for(ws2.recv(), timeout=1.0)
                obj = json.loads(msg)
                if obj.get("type") == "settings_update" and obj.get("key") == "DRAW_FACE_BB":
                    payload = obj
                    break
            except asyncio.TimeoutError:
                break
        assert payload is not None
        assert payload.get("value") is True


@pytest.mark.asyncio
async def test_type_casting_and_invalid_key_handling(start_backend_server):
    uri = "ws://127.0.0.1:8000/controls"
    async with websockets.connect(uri) as ws:
        # String values for booleans should cast
        await ws.send(json.dumps({"type": "set_state", "key": "DRAW_SMILE_BB", "value": "on"}))
        await ws.send(json.dumps({"type": "get_settings"}))
        obj = json.loads(await asyncio.wait_for(ws.recv(), timeout=2.0))
        assert obj.get("type") == "current_settings"
        assert obj["settings"]["DRAW_SMILE_BB"] is True

        # Invalid key should not crash; we just ensure connection stays alive
        await ws.send(json.dumps({"type": "set_state", "key": "NOT_A_KEY", "value": 123}))
        # Ping to confirm still alive
        await ws.send(json.dumps({"type": "ping"}))
        pong = json.loads(await asyncio.wait_for(ws.recv(), timeout=1.0))
        assert pong.get("type") == "pong"


