import pytest

from app.models.schemas import ResearchRun, Source, _hash
from app.services import retrieval


@pytest.mark.asyncio
async def test_source_metadata_and_snapshot_share_one_fetch_and_old_version_is_immutable(monkeypatch):
    versions = ['Original page says revenue was 10 million.', 'Changed page says revenue was 20 million.']
    calls = []

    async def fetch(url):
        text = versions[len(calls)]
        calls.append(url)
        return {'url':url, 'title':'Changing page', 'content':text, 'content_hash':_hash(text)}

    monkeypatch.setattr(retrieval, 'fetch_url', fetch)
    first = (await retrieval.fetch_sources(['https://fixture.example/changing']))[0]
    assert len(calls) == 1
    assert first.content_snapshot == versions[0]
    assert first.content_snippet == versions[0]
    assert first.content_hash == _hash(versions[0])
    later = (await retrieval.fetch_sources(['https://fixture.example/changing']))[0]
    assert later.id != first.id
    assert later.content_hash != first.content_hash
    assert later.content_snapshot == versions[1]
    assert first.content_snapshot == versions[0]


def test_historical_source_without_snapshot_remains_loadable():
    run = ResearchRun.model_validate({'question':'Historical source', 'sources':[
        {'id':'old','url':'https://fixture.example','content_hash':'historic-hash'}]})
    assert run.sources[0].content_snapshot is None
    assert 'historic-hash' == run.sources[0].content_hash


def test_extraction_window_finds_late_question_terms_without_expanding_budget():
    prefix = "Navigation and unrelated material. " * 400
    relevant = "Metformin intermittent fasting gastrointestinal effects and monitoring. " * 12
    snapshot = prefix + relevant + "Other material. " * 400
    text, start, end = retrieval.select_extraction_window(snapshot, "Metformin intermittent fasting effects")
    assert start > 0
    assert relevant in text
    assert text == snapshot[start:end]
    assert len(text) == 7000


def test_extraction_window_no_match_and_equal_scores_use_earliest_slice():
    snapshot = "Unrelated material. " * 700
    assert retrieval.select_extraction_window(snapshot, "Battery chemistry") == (snapshot[:7000], 0, 7000)
    repeated = "battery " * 1500
    assert retrieval.select_extraction_window(repeated, "battery")[1] == 0


def test_extraction_window_preserves_short_unicode_source_and_rejects_invalid_limit():
    snapshot = "Énergie and battery data."
    assert retrieval.select_extraction_window(snapshot, "énergie") == (snapshot, 0, len(snapshot))
    with pytest.raises(ValueError):
        retrieval.select_extraction_window(snapshot, "battery", limit=0)
