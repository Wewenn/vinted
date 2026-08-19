from vinted_assistant.cli import _apply_edits, _listing_as_text
from vinted_assistant.models import ProductAttributes, VintedListing


def _listing() -> VintedListing:
    return VintedListing(
        attributes=ProductAttributes(product_type="pull", brand="Uniqlo"),
        title="Pull Uniqlo",
        description="Pull chaud.",
        hashtags=["uniqlo", "pull"],
        keywords=["pull uniqlo"],
    )


def test_apply_edits_updates_fields():
    edited = (
        "# Titre\n"
        "Pull Uniqlo laine mérinos\n\n"
        "# Description\n"
        "Pull en laine mérinos, très chaud.\n"
        "Porté quelques fois.\n\n"
        "# Hashtags (séparés par des espaces)\n"
        "#uniqlo laine merinos\n\n"
        "# Mots-clés (séparés par des virgules)\n"
        "pull laine, mérinos homme\n"
    )
    updated = _apply_edits(_listing(), edited)
    assert updated.title == "Pull Uniqlo laine mérinos"
    assert "mérinos" in updated.description
    assert updated.hashtags == ["uniqlo", "laine", "merinos"]  # '#' retiré
    assert updated.keywords == ["pull laine", "mérinos homme"]


def test_apply_edits_keeps_original_when_section_blank():
    edited = "# Titre\n\n# Description\n\n"
    updated = _apply_edits(_listing(), edited)
    assert updated.title == "Pull Uniqlo"  # inchangé
    assert updated.description == "Pull chaud."  # inchangé


def test_listing_as_text_contains_key_parts():
    text = _listing_as_text(_listing())
    assert "Pull Uniqlo" in text
    assert "#uniqlo #pull" in text
    assert "Mots-clés" in text
