from app.adapters.prompts.yaml_prompt_repository import YamlPromptRepository


def test_router_prompt_from_yaml():
    prompts = YamlPromptRepository()
    prompt = prompts.get("router_classify")
    assert prompt.name == "router_classify"
    assert prompt.config.max_tokens == 40
    assert prompt.config.temperature == 0.0
    rendered = prompt.render_system(allowed="general, rag")
    assert "rag" in rendered
    assert "[[allowed]]" not in rendered


def test_rag_answer_prompt_from_yaml():
    prompts = YamlPromptRepository()
    prompt = prompts.get("rag_answer")
    assert prompt.config.max_tokens == 220
    assert prompt.empty_reply
    user = prompt.render_user(question="cuanto tarda?")
    assert "cuanto tarda?" in user
    system = prompt.render_system(context="Plazo 10 dias")
    assert "Plazo 10 dias" in system
