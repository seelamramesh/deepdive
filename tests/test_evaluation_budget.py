import pytest
from scripts.evaluation_budget import EvaluationBudget


def test_budget_reserves_before_send_and_survives_restart(tmp_path):
    path = tmp_path / "budget.json"
    budget = EvaluationBudget(path, "0.02")
    budget.reserve_search()
    budget = EvaluationBudget(path, "0.02")
    budget.reserve_search()
    with pytest.raises(RuntimeError, match="before sending"):
        budget.reserve_search()
    assert len(EvaluationBudget(path, "0.02").entries) == 2


def test_mesh_budget_rejects_unpriced_or_unbounded_requests(tmp_path):
    budget = EvaluationBudget(tmp_path / "budget.json")
    request = {"model":"anthropic/claude-haiku-5.5", "max_tokens":4096,
               "messages":[{"role":"user","content":"évidence"}]}
    budget.reserve_mesh(request)
    assert budget.reserved > 0
    for change in [{"model":"other"}, {"max_tokens":None}, {"max_tokens":True}, {"max_tokens":5000}]:
        with pytest.raises(ValueError):
            budget.reserve_mesh(request | change)
    assert len(budget.entries) == 1


@pytest.mark.parametrize("amount", ["NaN", "Infinity", "-1", "0", "4.01"])
def test_budget_rejects_invalid_caps(tmp_path, amount):
    with pytest.raises(ValueError):
        EvaluationBudget(tmp_path / "budget.json", amount)


def test_explicit_cap_increase_preserves_reservations_and_history(tmp_path):
    path=tmp_path/'budget.json'
    budget=EvaluationBudget(path)
    budget.reserve_search()
    prior=list(budget.entries)
    budget.increase_cap('3.50','4')
    reopened=EvaluationBudget(path)
    assert reopened.entries==prior
    assert str(reopened.reserved)=='0.01'
    assert str(reopened.cap)=='3.50'
    reopened.reserve_search()
    final=EvaluationBudget(path)
    assert len(final.metadata['cap_changes'])==1
    assert final.metadata['authorized_total_usd']=='4'
    assert len(final.entries)==2
    with pytest.raises(ValueError): final.increase_cap('4.50','5')
