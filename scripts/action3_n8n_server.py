"""One confirmed Action 3 n8n run; shared ledger, exact deployed backend."""
import asyncio
import json
from decimal import Decimal
from pathlib import Path
import sys
import time
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.action2_n8n_server import OneShotGuard, install_admission
from scripts.evaluation_budget import EvaluationBudget

QUESTION = "Do randomized studies of working from home agree on productivity effects? Compare the Chinese CTrip call-center experiment with the Indian data-entry experiment, preserve population and work-arrangement qualifiers, and distinguish genuine contradictions from contextual differences."
SOURCE_URLS = ["https://www.nber.org/papers/w18871", "https://www.nber.org/papers/w31515"]
PAYLOAD = {"question": QUESTION, "source_urls": SOURCE_URLS, "max_rounds": 2}


class EvaluationBlockedBeforeDispatch(RuntimeError):
    pass


class Action3Guard(OneShotGuard):
    def __init__(self, root):
        self.root=Path(root)
        self.marker=self.root/'action3-admitted.json'
        if self.marker.exists():
            raise RuntimeError('Action 3 already admitted; inspect existing run, never retry')
        self.initial=EvaluationBudget(self.root/'budget.json')
        self.initial_reserved=self.initial.reserved
        self.run_limit=self.initial_reserved+Decimal('0.65')
        if self.initial.cap!=Decimal('3.50') or self.run_limit>self.initial.cap:
            raise RuntimeError('Insufficient preserved budget for Action 3 ceiling')


    def event(self, **data):
        import os
        with (self.root/'action3-transport.jsonl').open('a',encoding='utf-8') as stream:
            stream.write(json.dumps({'time':time.time(),**data})+'\n')
            stream.flush();os.fsync(stream.fileno())

    def admit(self, payload):
        import os
        from app.models.schemas import ResearchRequest
        request=ResearchRequest.model_validate(payload)
        if (request.question!=QUESTION or request.source_urls!=SOURCE_URLS or request.max_rounds!=2
                or request.confidence_threshold not in (None,.7)):
            raise ValueError('Only the single approved bounded Action 3 question is admitted')
        with self.marker.open('x',encoding='utf-8') as stream:
            json.dump({'payload':PAYLOAD,'prior_reserved_usd':str(self.initial_reserved),
                'planned_reservation_usd':'0.62','max_new_reservation_usd':'0.65',
                'max_total_sources':2,'max_active_claims':2,'max_output_tokens':2048,
                'billing_verified':False,'admitted_at':time.time()},stream)
            stream.flush();os.fsync(stream.fileno())

    def reserve(self, kind, kwargs=None):
        try:
            return super().reserve(kind,kwargs)
        except (RuntimeError,ValueError,TypeError) as exc:
            self.event(kind=kind,event='reservation_refused',error_type=type(exc).__name__)
            raise EvaluationBlockedBeforeDispatch('Evaluation reservation refused before HTTP dispatch') from None

    async def mesh_create(self, real_create, **kwargs):
        from app.agents import prompts
        messages=kwargs.get('messages',[])
        if messages and messages[0].get('content')==prompts.CLAIM_DRAFTER_PROMPT:
            payload=json.loads(messages[1]['content'])
            self.event(event='drafter_input',revision_feedback=payload.get('revision_feedback',[]),
                       feedback_is_evidence=payload.get('feedback_is_evidence'),
                       evidence_count=len(payload.get('evidence',[])))
        return await super().mesh_create(real_create,**kwargs)


def mark_unsent_guard_refusal(call):
    if call.error=='EvaluationBlockedBeforeDispatch':
        call.request_sent=False
        call.usage_source='evaluation_guard_no_dispatch'
    return call


async def main():
    import fcntl
    import uvicorn
    from app.core.config import settings
    from app.core.mesh_gateway import mesh
    from app.services import orchestrator, retrieval
    from app.main import app
    root=Path('/app/data/evaluation-20261024')
    with (root/'process.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        guard=Action3Guard(root)
        if not settings.brave_search_api_key or not settings.mesh_api_key:
            raise RuntimeError('Required credentials missing; no paid calls sent')
        real_create=mesh.client.chat.completions.create
        async def create(**kwargs):return await guard.mesh_create(real_create,**kwargs)
        mesh._client=SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
        original_record=mesh._record_call
        def record(call):return original_record(mark_unsent_guard_refusal(call))
        mesh._record_call=record
        real_search=orchestrator.search_web
        async def search(query):return await guard.search(real_search,query)
        orchestrator.search_web=search
        real_fetch=orchestrator.fetch_sources
        retained=set()
        async def fetch(urls):
            if len(retained)>=2:
                for url in urls:retrieval.record_fetch_event(url,'evaluation_limit','max_total_sources_2')
                return []
            sources=await real_fetch(urls)
            for source in sources:retained.add(source.url)
            return sources
        orchestrator.fetch_sources=fetch
        settings.max_claims=2
        settings.max_sources_per_round=2
        settings.max_fetch_attempts_per_round=4
        settings.max_search_queries_per_round=1
        settings.max_contradiction_batches=1
        settings.mesh_max_output_tokens=2048
        settings.mesh_json_attempts=2
        settings.mesh_run_cache=True
        settings.confidence_threshold=.7
        install_admission(app,guard)
        guard.event(event='guard_ready',initial_reserved_usd=str(guard.initial_reserved),
                    planned_reservation_usd='0.62',max_new_reservation_usd='0.65')
        await uvicorn.Server(uvicorn.Config(app,host='0.0.0.0',port=8000,workers=1)).serve()

if __name__=='__main__':asyncio.run(main())
