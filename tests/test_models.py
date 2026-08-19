import json

from vinted_assistant.models import ProductAttributes, VintedListing


def _sample_listing() -> VintedListing:
    return VintedListing(
        attributes=ProductAttributes(
            product_type="jean slim",
            brand="Levi's",
            model="511",
            color="bleu",
            material="coton",
            style="casual",
            size="W32 L34",
            condition="Très bon état",
            defects=["légère usure aux ourlets"],
            highlights=["coupe slim", "coutures rouges"],
        ),
        title="Levi's 511 slim bleu W32",
        description="Jean Levi's 511 slim en coton bleu, taille W32 L34. Très bon état.",
        hashtags=["levis", "jean", "slim", "vintage"],
        keywords=["jean levis", "511 slim", "denim homme"],
        suggested_price_eur=25.0,
        confidence_notes=None,
    )


def test_hashtags_line_prefixes_hash():
    listing = _sample_listing()
    assert listing.hashtags_line() == "#levis #jean #slim #vintage"


def test_hashtags_line_does_not_double_hash():
    listing = _sample_listing()
    listing.hashtags = ["#levis", "jean"]
    assert listing.hashtags_line() == "#levis #jean"


def test_serialization_roundtrip():
    listing = _sample_listing()
    data = json.loads(listing.model_dump_json())
    restored = VintedListing.model_validate(data)
    assert restored.title == listing.title
    assert restored.attributes.brand == "Levi's"
    assert restored.hashtags == listing.hashtags


def test_defaults_are_empty_lists():
    attrs = ProductAttributes()
    assert attrs.defects == []
    assert attrs.highlights == []
    assert attrs.brand is None
