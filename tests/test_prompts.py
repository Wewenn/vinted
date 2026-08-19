from vinted_assistant.prompts import SYSTEM_PROMPT, build_user_prompt


def test_system_prompt_encodes_best_practices():
    low = SYSTEM_PROMPT.lower()
    assert "vinted" in low
    assert "taille" in low  # 1re ligne « Marque • Taille • État »
    assert "mots-clés" in low or "mots-cles" in low
    assert "invente" in low  # honnêteté / pas d'invention


def test_user_prompt_singular_plural():
    assert "1 photo " in build_user_prompt(1)
    assert "3 photos" in build_user_prompt(3)


def test_user_prompt_text_only_mode():
    prompt = build_user_prompt(0, "maillot SM Caen taille XL")
    assert "Aucune photo" in prompt
    assert "maillot SM Caen taille XL" in prompt


def test_user_prompt_includes_context():
    prompt = build_user_prompt(2, "taille M, porté 2 fois")
    assert "taille M, porté 2 fois" in prompt


def test_user_prompt_without_context_notes_absence():
    prompt = build_user_prompt(0, "   ")
    assert "pas ajouté d'informations" in prompt
