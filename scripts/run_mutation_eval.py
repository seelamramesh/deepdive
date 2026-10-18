"""Run a bounded live citation-mutation evaluation without web search."""

from __future__ import annotations

import argparse
import asyncio
import json

from app.agents.runner import run_defense, run_judge, run_prosecutor
from app.core.config import settings
from app.core.mesh_gateway import mesh
from app.evaluation.benchmark import create_mutation_test_cases, compute_mutation_metrics
from app.models.schemas import AtomicClaim, Evidence, ResearchRun, _hash
from app.storage.database import load_run


def build_eval_artifacts(run: ResearchRun, limit: int) -> tuple[list[dict], list[AtomicClaim], list[Evidence]]:
    supported = run.supported_claims(settings.confidence_threshold)
    cases = create_mutation_test_cases(supported, run.evidence)[:limit]
    claims = []
    evidence = []
    for index, case in enumerate(cases):
        evidence_id = f"mutation-evidence-{index}"
        claim_id = f"mutation-claim-{index}"
        evidence.append(Evidence(
            id=evidence_id,
            source_id="mutation-source",
            passage=case["passage"],
            passage_hash=_hash(case["passage"]),
        ))
        claims.append(AtomicClaim(
            id=claim_id,
            text=case["claim"],
            evidence_ids=[evidence_id],
        ))
        case["claim_id"] = claim_id
    return cases, claims, evidence


async def evaluate(run_id: str, limit: int) -> dict:
    run = await load_run(run_id)
    if run is None:
        raise RuntimeError(f"Run not found: {run_id}")
    cases, claims, evidence = build_eval_artifacts(run, limit)
    if not cases:
        raise RuntimeError("Run has no supported claim/evidence pairs to mutate")

    eval_run = ResearchRun(question=f"Citation mutation evaluation for run {run_id}")
    prosecution = await run_prosecutor(eval_run, claims, evidence)
    defense = await run_defense(eval_run, claims, evidence)
    judgements = await run_judge(
        eval_run,
        claims,
        prosecution,
        defense,
        settings.confidence_threshold,
    )
    verdict_by_claim = {judgement.claim_id: judgement.verdict.value for judgement in judgements}
    results = []
    for case in cases:
        results.append({
            **case,
            "actual_verdict": verdict_by_claim.get(case["claim_id"], "missing"),
        })
    return {
        "run_id": run_id,
        "mesh_calls": len(mesh.drain_calls()),
        "metrics": compute_mutation_metrics(results),
        "results": results,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("run_id")
    parser.add_argument("--limit", type=int, default=8, choices=range(1, 13))
    args = parser.parse_args()
    print(json.dumps(asyncio.run(evaluate(args.run_id, args.limit)), indent=2))


if __name__ == "__main__":
    main()
