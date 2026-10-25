import json
from unittest.mock import AsyncMock
import pytest
from scripts.action3_n8n_server import Action3Guard, PAYLOAD, EvaluationBlockedBeforeDispatch, mark_unsent_guard_refusal
from app.models.schemas import AgentCall

@pytest.fixture
def guard(tmp_path):
    (tmp_path/'budget.json').write_text(json.dumps({'cap_usd':'3.50','authorized_total_usd':'4','reserved_usd':'2.840527','reservations':[{'kind':'prior','reserved_usd':'2.840527'}]}))
    return Action3Guard(tmp_path)

@pytest.mark.asyncio
async def test_action3_ceiling_blocks_before_transport_and_never_resets_history(guard):
    guard.admit(PAYLOAD)
    for _ in range(65):guard.reserve('brave')
    real=AsyncMock()
    with pytest.raises(EvaluationBlockedBeforeDispatch):await guard.search(real,'query')
    real.assert_not_awaited()
    ledger=json.loads((guard.root/'budget.json').read_text())
    assert ledger['reserved_usd']=='3.490527'
    assert ledger['reservations'][0]['reserved_usd']=='2.840527'
    with pytest.raises(FileExistsError):guard.admit(PAYLOAD)
    with pytest.raises(RuntimeError,match='already admitted'):Action3Guard(guard.root)


def test_action3_wrong_topic_and_rounds_are_not_admitted(guard):
    for change in [{'question':'Unapproved question'},{'max_rounds':3},{'source_urls':[]}]:
        with pytest.raises(ValueError):guard.admit(PAYLOAD|change)
    assert not guard.marker.exists()


def test_guard_refusal_is_not_a_sent_mesh_request():
    call=AgentCall(agent='judge',request_sent=True,success=False,error='EvaluationBlockedBeforeDispatch')
    mark_unsent_guard_refusal(call)
    assert call.request_sent is False and call.total_tokens is None
    real=AgentCall(agent='judge',request_sent=True,success=False,error='TimeoutError')
    mark_unsent_guard_refusal(real)
    assert real.request_sent is True
