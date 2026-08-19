from vinted_assistant.prompts import SYSTEM_PROMPT, build_user_prompt


def test_system_prompt_mentions_no_invention():
    assert "invente" in SYSTEM_PROMPT.lower()
    assert "vinted" in SYSTEM_PROMPT.lower()


def test_user_prompt_singular_plural():
    assert "1 photo " in build_user_prompt(1)
    assert "3 photos" in build_user_prompt(3)


def test_user_prompt_includes_context():
    prompt = build_user_prompt(2, "taille M, porté 2 fois")
    assert "taille M, porté 2 fois" in prompt


def test_user_prompt_ignores_empty_context():
    prompt = build_user_prompt(2, "   ")
    assert "complémentaires" not in prompt
