import io

import pytest

from vinted_assistant.analysis import (
    AnalysisError,
    analyze_photos,
    encode_image,
    resolve_image_paths,
)
from vinted_assistant.models import ProductAttributes, VintedListing


# --------------------------------------------------------------------------- #
# resolve_image_paths
# --------------------------------------------------------------------------- #

def _touch_image(path):
    path.write_bytes(b"\x89PNG\r\n\x1a\n")  # en-tête PNG minimal (contenu factice)


def test_resolve_from_files(tmp_path):
    a = tmp_path / "a.jpg"
    b = tmp_path / "b.png"
    _touch_image(a)
    _touch_image(b)
    paths = resolve_image_paths([str(a), str(b)])
    assert [p.name for p in paths] == ["a.jpg", "b.png"]


def test_resolve_from_directory_sorted(tmp_path):
    for name in ["2.jpg", "1.jpg", "notes.txt"]:
        (tmp_path / name).write_bytes(b"x")
    paths = resolve_image_paths([], directory=tmp_path)
    assert [p.name for p in paths] == ["1.jpg", "2.jpg"]  # .txt ignoré, trié


def test_resolve_deduplicates(tmp_path):
    a = tmp_path / "a.jpg"
    _touch_image(a)
    paths = resolve_image_paths([str(a), str(a)])
    assert len(paths) == 1


def test_resolve_missing_file_raises(tmp_path):
    with pytest.raises(AnalysisError):
        resolve_image_paths([str(tmp_path / "missing.jpg")])


def test_resolve_bad_extension_raises(tmp_path):
    bad = tmp_path / "file.txt"
    bad.write_text("hello")
    with pytest.raises(AnalysisError):
        resolve_image_paths([str(bad)])


def test_resolve_empty_raises(tmp_path):
    with pytest.raises(AnalysisError):
        resolve_image_paths([], directory=tmp_path)


# --------------------------------------------------------------------------- #
# encode_image (nécessite Pillow pour générer un vrai JPEG/PNG)
# --------------------------------------------------------------------------- #

def test_encode_image_resizes_large(tmp_path):
    Image = pytest.importorskip("PIL.Image")
    big = tmp_path / "big.jpg"
    Image.new("RGB", (3000, 2000), color="red").save(big)
    media_type, data = encode_image(big, max_dimension=1568)
    assert media_type == "image/jpeg"
    assert data  # base64 non vide
    # Vérifie que l'image ré-encodée est bien redimensionnée.
    import base64

    reopened = Image.open(io.BytesIO(base64.b64decode(data)))
    assert max(reopened.size) <= 1568


# --------------------------------------------------------------------------- #
# analyze_photos (client factice — aucune requête réseau)
# --------------------------------------------------------------------------- #

class _FakeMessages:
    def __init__(self, listing):
        self._listing = listing
        self.calls = []

    def parse(self, **kwargs):
        self.calls.append(kwargs)

        class _Resp:
            parsed_output = self._listing

        return _Resp()


class _FakeClient:
    def __init__(self, listing):
        self.messages = _FakeMessages(listing)


def _listing():
    return VintedListing(
        attributes=ProductAttributes(product_type="robe", brand="Zara"),
        title="Robe Zara",
        description="Jolie robe Zara.",
        hashtags=["zara", "robe"],
        keywords=["robe zara"],
    )


def test_analyze_photos_returns_listing(tmp_path):
    Image = pytest.importorskip("PIL.Image")
    photo = tmp_path / "p.jpg"
    Image.new("RGB", (100, 100), color="blue").save(photo)

    client = _FakeClient(_listing())
    result = analyze_photos(client, [photo], model="claude-opus-5")

    assert isinstance(result, VintedListing)
    assert result.attributes.brand == "Zara"

    # Vérifie que la requête contient bien une image et le bon format de sortie.
    call = client.messages.calls[0]
    assert call["model"] == "claude-opus-5"
    assert call["output_format"] is VintedListing
    content = call["messages"][0]["content"]
    assert any(block.get("type") == "image" for block in content)
    assert any(block.get("type") == "text" for block in content)


def test_analyze_photos_rejects_too_many(tmp_path):
    Image = pytest.importorskip("PIL.Image")
    photos = []
    for i in range(21):
        p = tmp_path / f"{i}.jpg"
        Image.new("RGB", (10, 10)).save(p)
        photos.append(p)
    client = _FakeClient(_listing())
    with pytest.raises(AnalysisError):
        analyze_photos(client, photos, model="claude-opus-5")


def test_analyze_photos_empty_without_context_raises():
    client = _FakeClient(_listing())
    with pytest.raises(AnalysisError):
        analyze_photos(client, [], model="claude-opus-5")


def test_analyze_text_only_works():
    """Sans photo mais avec une description : génération autorisée."""
    client = _FakeClient(_listing())
    result = analyze_photos(
        client, [], model="claude-opus-5", extra_context="robe Zara taille M"
    )
    assert result.attributes.brand == "Zara"
    call = client.messages.calls[0]
    content = call["messages"][0]["content"]
    # Aucun bloc image, uniquement du texte.
    assert all(block.get("type") != "image" for block in content)
    assert any(block.get("type") == "text" for block in content)
