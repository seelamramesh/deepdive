"""Pytest configuration."""

import pytest


@pytest.fixture
def sample_evidence():
    from app.models.schemas import Evidence
    return [
        Evidence(
            id="ev1", source_id="src1", subquestion_id="sq1",
            passage="Global EV battery market reached $45 billion in 2025.",
            relevance=0.9,
        ),
        Evidence(
            id="ev2", source_id="src2", subquestion_id="sq1",
            passage="Lithium supply chain disruptions pose significant risks.",
            relevance=0.85,
        ),
        Evidence(
            id="ev3", source_id="src3", subquestion_id="sq2",
            passage="China controls approximately 60% of lithium refining capacity.",
            relevance=0.8,
        ),
    ]


@pytest.fixture
def sample_claims():
    from app.models.schemas import AtomicClaim
    return [
        AtomicClaim(
            id="cl1", text="The global EV battery market was valued at $45 billion in 2025.",
            evidence_ids=["ev1"], subquestion_id="sq1",
        ),
        AtomicClaim(
            id="cl2", text="Lithium supply chain disruptions are a major risk factor.",
            evidence_ids=["ev2"], subquestion_id="sq1",
        ),
        AtomicClaim(
            id="cl3", text="China controls approximately 60% of lithium refining.",
            evidence_ids=["ev3"], subquestion_id="sq2",
        ),
    ]


@pytest.fixture(autouse=True)
def forbid_real_http(monkeypatch):
    """All tests must use ASGI/MockTransport; never paid HTTP transports."""
    import httpx
    async def forbidden_async(*args, **kwargs):
        raise AssertionError("Real outbound HTTP forbidden in tests")
    def forbidden_sync(*args, **kwargs):
        raise AssertionError("Real outbound HTTP forbidden in tests")
    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", forbidden_async)
    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", forbidden_sync)
