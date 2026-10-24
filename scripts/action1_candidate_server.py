"""One guarded real HTTP API research test, then read-only browser candidate."""
import asyncio,fcntl,json,sys
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import httpx,uvicorn
from scripts.evaluation_budget import EvaluationBudget
from app.core.config import settings
from app.core.mesh_gateway import mesh
from app.services import orchestrator
from app.storage import database
from app.main import app
from starlette.responses import JSONResponse

async def main():
 root=Path('/app/data/evaluation-20261024')
 with (root/'process.lock').open('w') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  marker=root/'action1-http-started.json'
  if marker.exists(): raise RuntimeError('Already started; inspect existing process and data')
  budget=EvaluationBudget(root/'budget.json')
  create_original=mesh.client.chat.completions.create
  async def create(**kwargs):
   budget.reserve_mesh(kwargs)
   return await create_original(**kwargs)
  mesh._client=SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
  original_search=orchestrator.search_web
  async def search(query):
   budget.reserve_search()
   return await original_search(query)
  orchestrator.search_web=search
  settings.max_claims=2
  settings.max_sources_per_round=2
  settings.max_search_queries_per_round=1
  database.DB_PATH=str(root/'action1-candidate.db')
  settings.database_path=database.DB_PATH
  allow_post=True
  @app.middleware('http')
  async def read_only_after_start(request,call_next):
   nonlocal allow_post
   if request.method!='GET':
    if not (allow_post and request.method=='POST' and request.url.path=='/research'):
     return JSONResponse({'detail':'Candidate read-only; paid research disabled'},status_code=405)
    allow_post=False
   return await call_next(request)
  marker.write_text(json.dumps({'max_claims':2,'max_rounds':1,'max_sources':2,'prior_reserved_usd':str(budget.reserved)}))
  server=uvicorn.Server(uvicorn.Config(app,host='0.0.0.0',port=8873,log_level='warning'))
  task=asyncio.create_task(server.serve())
  while not server.started:
   if task.done(): await task
   await asyncio.sleep(.1)
  async with httpx.AsyncClient(base_url='http://127.0.0.1:8873',timeout=20) as client:
   response=await client.post('/research',json={'question':'In SQLite WAL mode, can multiple writers write simultaneously?',
     'source_urls':['https://www.sqlite.org/wal.html'],'max_rounds':1})
   response.raise_for_status()
   run_id=response.json()['run_id']
   print(json.dumps({'action1_run_id':run_id,'http_api_started':True}),flush=True)
   while True:
    workspace=(await client.get('/runs/'+run_id+'/workspace')).json()
    if workspace['current_state'] in ['END','FAILED']: break
    await asyncio.sleep(2)
   saved=await database.load_run(run_id)
   assert saved is not None
   (root/'action1-http-workspace.json').write_text(json.dumps(workspace,indent=2))
   print(json.dumps({'run_id':run_id,'state':workspace['current_state'],'review_units':len(workspace.get('report_grounding_audit',[])),
     'review_status':workspace.get('report_grounding_status'),'reserved_usd':str(budget.reserved),'read_only_browser_ready':True}),flush=True)
  await task
asyncio.run(main())
