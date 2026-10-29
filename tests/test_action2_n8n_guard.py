import json
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from scripts.action2_n8n_server import OneShotGuard, PAYLOAD, install_admission


@pytest.fixture
def guard(tmp_path):
    (tmp_path / "budget.json").write_text(json.dumps({
        "cap_usd": "3.50", "authorized_total_usd": "4",
        "reserved_usd": "2.138282", "reservations": [
            {"kind": "prior", "reserved_usd": "2.138282"}],
        "cap_changes": [{"reason": "explicit_user_approval"}]}))
    return OneShotGuard(tmp_path)


def test_http_admission_preserves_body_and_blocks_duplicates_and_other_mutations(guard):
    app = FastAPI()
    install_admission(app, guard)

    @app.post("/research")
    def start(payload: dict):
        return payload

    with TestClient(app) as client:
        assert client.post("/research", json=PAYLOAD | {"max_rounds": 5}).status_code == 423
        assert not guard.marker.exists()
        assert client.post("/runs/a/follow-up", json=PAYLOAD).status_code == 423
        result = client.post("/research", json=PAYLOAD)
        assert result.status_code == 200 and result.json() == PAYLOAD
        assert client.post("/research", json=PAYLOAD).status_code == 423
    with pytest.raises(RuntimeError, match="Already admitted"):
        OneShotGuard(guard.root)


@pytest.mark.asyncio
async def test_reservation_is_durable_before_mesh_and_existing_history_preserved(guard):
    guard.admit(PAYLOAD)
    async def create(**kwargs):
        ledger = json.loads((guard.root / "budget.json").read_text())
        assert len(ledger["reservations"]) == 2
        assert ledger["reservations"][0]["reserved_usd"] == "2.138282"
        assert ledger["cap_changes"] == [{"reason": "explicit_user_approval"}]
        return {"ok": True}
    result = await guard.mesh_create(create, model="anthropic/claude-haiku-5.5",
                                    messages=[{"role": "user", "content": "test"}], max_tokens=4096)
    assert result == {"ok": True}


@pytest.mark.asyncio
async def test_both_transports_block_before_admission_and_at_run_limit(guard):
    real = AsyncMock()
    with pytest.raises(RuntimeError, match="No admitted"):
        await guard.search(real, "query")
    real.assert_not_awaited()
    guard.admit(PAYLOAD)
    guard.run_limit = guard.initial_reserved
    with pytest.raises(RuntimeError, match="before sending"):
        await guard.search(real, "query")
    with pytest.raises(RuntimeError, match="before sending"):
        await guard.mesh_create(real, model="anthropic/claude-haiku-5.5",
                                messages=[], max_tokens=4096)
    real.assert_not_awaited()
    assert len(json.loads((guard.root / "budget.json").read_text())["reservations"]) == 1


@pytest.mark.asyncio
async def test_failed_transport_keeps_reservation_and_records_error(guard):
    guard.admit(PAYLOAD)
    real = AsyncMock(side_effect=TimeoutError)
    with pytest.raises(TimeoutError):
        await guard.mesh_create(real, model="anthropic/claude-haiku-5.5",
                                messages=[], max_tokens=4096)
    assert len(json.loads((guard.root / "budget.json").read_text())["reservations"]) == 2
    events = [json.loads(line) for line in (guard.root / "action2-transport.jsonl").read_text().splitlines()]
    assert [e["event"] for e in events] == ["reserved", "dispatch_attempt", "transport_error"]


def test_linux_lock_rejects_second_process(tmp_path):
    fcntl = pytest.importorskip("fcntl")
    with (tmp_path / "process.lock").open("a") as first, (tmp_path / "process.lock").open("a") as second:
        fcntl.flock(first, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with pytest.raises(BlockingIOError):
            fcntl.flock(second, fcntl.LOCK_EX | fcntl.LOCK_NB)
