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
