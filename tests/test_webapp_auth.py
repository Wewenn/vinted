import io

import pytest

pytest.importorskip("flask")
Image = pytest.importorskip("PIL.Image")

from vinted_assistant.config import Config
from vinted_assistant.models import ProductAttributes, VintedListing
from vinted_assistant.webapp import create_app


def _config(tmp_path, password=None) -> Config:
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
        web_password=password,
        web_secret="test-secret",
    )


def _listing() -> VintedListing:
    return VintedListing(
        attributes=ProductAttributes(product_type="pull", brand="Uniqlo"),
        title="Pull Uniqlo",
        description="Pull chaud.",
        hashtags=["uniqlo"],
        keywords=["pull"],
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


def _client(tmp_path, password):
    app = create_app(
        _config(tmp_path, password=password),
        client_factory=lambda: _FakeClient(_listing()),
        prefill_func=lambda **k: None,
    )
    app.config.update(TESTING=True)
    return app.test_client()


# --------------------------------------------------------------------------- #
# Sans mot de passe : accès libre (comportement historique)
# --------------------------------------------------------------------------- #

def test_no_password_allows_index(tmp_path):
    c = _client(tmp_path, password=None)
    assert c.get("/").status_code == 200


# --------------------------------------------------------------------------- #
# Avec mot de passe : protection active
# --------------------------------------------------------------------------- #

def test_index_redirects_to_login_when_protected(tmp_path):
    c = _client(tmp_path, password="secret")
    r = c.get("/")
    assert r.status_code == 302
    assert "/login" in r.headers["Location"]


def test_login_page_served(tmp_path):
    c = _client(tmp_path, password="secret")
    r = c.get("/login")
    assert r.status_code == 200
    assert "Mot de passe" in r.get_data(as_text=True)


def test_api_unauthenticated_returns_401(tmp_path):
    c = _client(tmp_path, password="secret")
    r = c.post("/api/analyze", data={"context": "robe"})
    assert r.status_code == 401


def test_wrong_password_rejected(tmp_path):
    c = _client(tmp_path, password="secret")
    r = c.post("/login", data={"password": "mauvais"})
    assert r.status_code == 401


def test_correct_password_grants_access(tmp_path):
    c = _client(tmp_path, password="secret")
    r = c.post("/login", data={"password": "secret"})
    assert r.status_code == 302
    # La session est maintenant authentifiée : l'index et l'API répondent.
    assert c.get("/").status_code == 200
    r2 = c.post(
        "/api/analyze",
        data={"context": "robe Zara taille M"},
        content_type="multipart/form-data",
    )
    assert r2.status_code == 200
