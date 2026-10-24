import pytest

from agent.budget import Budget, BudgetExceeded, RequestSize
from agent.prompts import DIRECTORY, SKILLS, chat_prompt, voice_prompt


@pytest.mark.parametrize("role", ["navigator", "admin"])
def test_voice_prompts_fit_the_dashboard_limit(role):
    assert len(voice_prompt(role)) <= 2500


@pytest.mark.parametrize("name", SKILLS)
def test_each_prompt_recipe_is_short(name):
    assert len((DIRECTORY / "skills" / f"{name}.md").read_text().splitlines()) <= 25


def test_spatial_query_is_available_in_the_chat_prompt():
    assert "spatial_query" in chat_prompt()


def test_budget_reserves_before_a_call():
    with pytest.raises(BudgetExceeded):
        Budget(0.001).reserve(RequestSize("claude-sonnet-5-5", 1000, 2048))


def test_budget_uses_actual_cost_after_a_response():
    budget = Budget(1)
    reserved = budget.reserve(RequestSize("claude-sonnet-5-5", 1000, 2048))
    budget.settle(reserved, 0.001)
    assert budget.spent == pytest.approx(0.001)


@pytest.mark.parametrize("amount", [0, -1, float("inf"), float("nan")])
def test_invalid_paid_budgets_are_rejected(amount):
    with pytest.raises(ValueError):
        Budget(amount)
