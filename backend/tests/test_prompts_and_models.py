from app.models import MODELS, TIERS, cost_usd
from app.prompts import build_quiz_prompt, build_system_prompt


def test_system_prompt_has_grade_and_language():
    prompt = build_system_prompt("Math", 3, "Hindi")
    assert prompt.startswith("Reply in simple Hindi")
    assert "Grade 3 student" in prompt
    assert "Grade 3 level" in prompt
    assert "Never use LaTeX" in prompt


def test_english_prompt_has_no_language_prefix():
    assert build_system_prompt("Science", 7, "English").startswith("You are EduReach")


def test_quiz_prompt_language_line_only_for_non_english():
    assert "Write the questions in" not in build_quiz_prompt("Math", 5, "English", "x")
    assert "Write the questions in French." in build_quiz_prompt("Math", 5, "French", "x")


def test_every_tier_model_is_priced():
    for chain in TIERS.values():
        assert chain, "empty tier"
        for model_id in chain:
            assert model_id in MODELS


def test_cost_math():
    # 1M input at $0.25 + 1M output at $1.50
    assert cost_usd("gemini-3.1-flash-lite", 1_000_000, 1_000_000) == 1.75
    assert round(cost_usd("gemini-3.1-flash-lite", 2500, 150), 6) == 0.00085
