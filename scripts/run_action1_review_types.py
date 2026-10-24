"""Action 1 labelled real-Mesh report review; synthetic component evaluation."""
import asyncio,fcntl,json,sys
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.evaluation_budget import EvaluationBudget
from app.core.mesh_gateway import mesh
from app.models.schemas import ResearchRun,AtomicClaim,Evidence,ClaimJudgement,ClaimVerdict
from app.services.report_grounding import review_report
async def main():
 root=Path('/app/data/evaluation-20261024')
 with (root/'process.lock').open('w') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  marker=root/'action1-types-started.json'
  if marker.exists(): raise RuntimeError('Already started; inspect prior results')
  budget=EvaluationBudget(root/'budget.json')
  original=mesh.client.chat.completions.create
  async def create(**kwargs):
   budget.reserve_mesh(kwargs)
   return await original(**kwargs)
  mesh._client=SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
  run=ResearchRun(question='Summarize fictional Acme findings without adding unverified facts.')
  texts=['Acme reported revenue of 10 million USD for FY2025.',
         'A 2025 Acme observational study reported an association between training and productivity.']
  run.evidence=[Evidence(id='e0',source_id='s0',passage=texts[0]+' Profit was 2 million USD.'),
                Evidence(id='e1',source_id='s1',passage=texts[1]+' It did not establish causation.')]
  run.claims=[AtomicClaim(id='c'+str(i),text=text,evidence_ids=['e'+str(i)]) for i,text in enumerate(texts)]
  run.judgements=[ClaimJudgement(claim_id=c.id,verdict=ClaimVerdict.SUPPORTED,confidence=.95,supporting_evidence_ids=c.evidence_ids) for c in run.claims]
  cases=[('extra_clause',False,'Acme reported revenue of 10 million USD and profit of 2 million USD for FY2025. [claim:c0] [evidence:e0]'),
   ('causal_overreach',False,'Training caused increased productivity. [claim:c1] [evidence:e1]'),
   ('temporal_overreach',False,'Acme earns 10 million USD every year. [claim:c0] [evidence:e0]'),
   ('attribution_error',False,'All observational studies establish an association between training and productivity. [claim:c1] [evidence:e1]'),
   ('valid_paraphrase',True,'Acme reported FY2025 revenue of USD 10 million. [claim:c0] [evidence:e0]'),
   ('supported_factual_heading',True,'## Acme reported FY2025 revenue of USD 10 million [claim:c0] [evidence:e0]'),
   ('unsupported_factual_heading',False,'## Training is proven to cause productivity gains [claim:c1] [evidence:e1]')]
  marker.write_text(json.dumps({'synthetic':True,'prior_reserved_usd':str(budget.reserved)}))
  run.final_report='\n'.join(c[2] for c in cases)
  await review_report(run)
  results=[{'case':c[0],'expected_kept':c[1],'audit':a,'matches_expected':a['kept']==c[1]} for c,a in zip(cases,run.report_grounding_audit)]
  output={'synthetic':True,'results':results,'calls':[c.model_dump() for c in mesh.drain_calls()],'reserved_usd':str(budget.reserved),'billing_verified':False}
  (root/'action1-types-result.json').write_text(json.dumps(output,indent=2))
  print(json.dumps({'results':[(r['case'],r['matches_expected']) for r in results],'reserved_usd':str(budget.reserved)}),flush=True)
asyncio.run(main())
