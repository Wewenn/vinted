import io

import pytest

pytest.importorskip("flask")
Image = pytest.importorskip("PIL.Image")

from vinted_assistant.config import Config
from vinted_assistant.models import ProductAttributes, VintedListing
from vinted_assistant.webapp import create_app


def _config(tmp_path) -> Config:
    app_dir = tmp_path / "app"
    return Config(
        anthropic_api_key="test",
        model="claude-opus-5",
        base_url="https://www.vinted.fr",
        cdp_url="http://localhost:9222",
        debug_port=9222,
        app_dir=app_dir,
        chrome_profile_dir=app_dir / "chrome-profile",
        drafts_dir=app_dir / "drafts",
    )


def _listing() -> VintedListing:
    return VintedListing(
        attributes=ProductAttributes(product_type="veste", brand="Levi's"),
        title="Veste Levi's",
        description="Belle veste en jean.",
        hashtags=["levis", "veste"],
        keywords=["veste jean"],
        suggested_price_eur=30.0,
    )


class _FakeClient:
    def __init__(self, listing):
        listing_ = listing

        class _Messages:
            def parse(self, **kwargs):
                class _R:
                    parsed_output = listing_
                return _R()

        self.messages = _Messages()


def _png_bytes():
    buf = io.BytesIO()
    Image.new("RGB", (60, 60), color="green").save(buf, format="PNG")
    return buf.getvalue()


@pytest.fixture
def client(tmp_path):
    captured = {}

    def prefill_func(**kwargs):
        captured.update(kwargs)

        class _Report:
            photos_uploaded = len(kwargs.get("image_paths", []))
            title_filled = True
            description_filled = True
            notes = ["ok"]

        return _Report()

    app = create_app(
        _config(tmp_path),
        client_factory=lambda: _FakeClient(_listing()),
        prefill_func=prefill_func,
    )
    app.config.update(TESTING=True)
    c = app.test_client()
    c._captured = captured
    return c


def test_index_served(client):
    r = client.get("/")
    assert r.status_code == 200
    assert b"Assistant Vinted" in r.data


def test_config_endpoint(client):
    r = client.get("/api/config")
    assert r.status_code == 200
    assert r.get_json()["model"] == "claude-opus-5"


def test_analyze_requires_photo_or_text(client):
    r = client.post("/api/analyze", data={})
    assert r.status_code == 400


def test_analyze_text_only(client):
    r = client.post(
        "/api/analyze",
        data={"context": "maillot SM Caen third saison 24/25, taille XL"},
        content_type="multipart/form-data",
    )
    assert r.status_code == 200
    body = r.get_json()
    assert body["photo_count"] == 0
    assert body["listing"]["title"]


def test_analyze_returns_listing(client):
    data = {
        "photos": (io.BytesIO(_png_bytes()), "item.png"),
        "context": "taille M",
    }
    r = client.post("/api/analyze", data=data, content_type="multipart/form-data")
    assert r.status_code == 200
    body = r.get_json()
    assert body["photo_count"] == 1
    assert body["listing"]["attributes"]["brand"] == "Levi's"
    assert body["session_id"]


def test_prefill_uses_saved_photos(client):
    # 1) analyse pour créer une session avec photos sauvegardées.
    data = {"photos": (io.BytesIO(_png_bytes()), "item.png")}
    r = client.post("/api/analyze", data=data, content_type="multipart/form-data")
    session_id = r.get_json()["session_id"]

    # 2) pré-remplissage avec la fiche (éventuellement éditée).
    listing = _listing().model_dump()
    listing["title"] = "Titre édité"
    r2 = client.post(
        "/api/prefill",
        json={"session_id": session_id, "listing": listing, "upload_images": True},
    )
    assert r2.status_code == 200
    body = r2.get_json()
    assert body["photos_uploaded"] == 1
    assert body["title_filled"] is True
    # La fonction de pré-remplissage a bien reçu la fiche éditée.
    assert client._captured["listing"].title == "Titre édité"


def test_prefill_rejects_missing_listing(client):
    r = client.post("/api/prefill", json={"session_id": "x"})
    assert r.status_code == 400


def test_friendly_api_error_credits():
    from vinted_assistant.webapp import _friendly_api_error

    msg = _friendly_api_error(
        Exception("Error code: 400 - Your credit balance is too low to access the Anthropic API")
    )
    assert "Crédits Anthropic insuffisants" in msg
