from app.models.schemas import AtomicClaim, ClaimJudgement, ClaimVerdict, ResearchRun
from app.services.orchestrator import _select_claims_for_round


def test_later_topic_gets_slots_without_losing_already_accepted_claims():
    old=[AtomicClaim(id=f'a{i}',text=f'Old claim {i}',subquestion_id='a',evidence_ids=[f'ea{i}']) for i in range(12)]
    new=[AtomicClaim(id=f'b{i}',text=f'New topic claim {i}',subquestion_id='b',evidence_ids=[f'eb{i}']) for i in range(6)]
    run=ResearchRun(question='Balanced fixture',claims=old,research_round=2,judgements=[
        ClaimJudgement(claim_id=f'a{i}',verdict=ClaimVerdict.SUPPORTED,confidence=0.9,supporting_evidence_ids=[f'ea{i}']) for i in range(5)])
    selected=_select_claims_for_round(run,new,12)
    ids={c.id for c in selected}
    assert len(selected)==12
    assert {f'a{i}' for i in range(5)} <= ids
    assert {c.id for c in new} <= ids
    excluded=run.claim_selection_audit[-1]['excluded_from_active_budget']
    assert excluded and all(item['reason']=='active_claim_budget' for item in excluded)
    assert {item['claim']['id'] for item in excluded} | ids == {c.id for c in old+new}


def test_duplicate_text_merges_evidence_without_inventing_new_claim_identity():
    old=AtomicClaim(id='original',text='Same fact',evidence_ids=['old-e'])
    run=ResearchRun(question='Duplicate fixture',claims=[old])
    selected=_select_claims_for_round(run,[AtomicClaim(id='duplicate',text='same fact',evidence_ids=['new-e'])],12)
    assert len(selected)==1 and selected[0].id=='original'
    assert selected[0].evidence_ids==['old-e','new-e']
    assert run.claim_selection_audit[-1]['merged_duplicate_ids']=={'duplicate':'original'}


def test_full_accepted_budget_is_disclosed_and_not_silently_expanded():
    claim=AtomicClaim(id='kept',text='Verified fact',evidence_ids=['e'])
    run=ResearchRun(question='Hard budget fixture',claims=[claim],judgements=[
        ClaimJudgement(claim_id='kept',verdict=ClaimVerdict.SUPPORTED,confidence=0.9,supporting_evidence_ids=['e'])])
    selected=_select_claims_for_round(run,[AtomicClaim(id='new',text='New unverified fact')],1)
    assert [c.id for c in selected]==['kept']
    assert run.claim_selection_audit[-1]['excluded_from_active_budget'][0]['previous_judgement'] is None
