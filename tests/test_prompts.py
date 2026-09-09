from app.models import GenerationCreate
from app.prompts import PromptBuilder


def test_prompt_contains_identity_and_custom_constraints():
    request = GenerationCreate(
        scene="A neutral studio portrait",
        idempotency_key="request-001",
        negative_constraints=["oversaturated skin"],
    )
    prompt = PromptBuilder().build(request, 3)
    assert "same adult person's recognizable facial identity" in prompt
    assert "3 authorized reference image(s)" in prompt
    assert "oversaturated skin" in prompt

