"""Chargement de la configuration de l'assistant Vinted.

La configuration provient des variables d'environnement (et d'un fichier
`.env` optionnel chargé automatiquement). Aucun identifiant Vinted n'est jamais
demandé ni stocké : l'authentification Vinted se fait uniquement dans le
navigateur de l'utilisateur.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

try:  # python-dotenv est recommandé mais optionnel.
    from dotenv import load_dotenv
except Exception:  # pragma: no cover - fallback si dotenv absent
    def load_dotenv(*_args, **_kwargs):  # type: ignore
        return False


# Répertoire de travail de l'assistant (profil Chrome dédié, brouillons...).
APP_DIR = Path(
    os.environ.get("VINTED_AI_HOME", Path.home() / ".vinted-assistant")
).expanduser()

# Valeurs par défaut.
DEFAULT_MODEL = "claude-opus-5"
DEFAULT_BASE_URL = "https://www.vinted.fr"
DEFAULT_CDP_URL = "http://localhost:9222"
DEFAULT_DEBUG_PORT = 9222


@dataclass
class Config:
    """Paramètres résolus de l'assistant."""

    anthropic_api_key: str | None
    model: str
    base_url: str
    cdp_url: str
    debug_port: int
    app_dir: Path
    chrome_profile_dir: Path
    drafts_dir: Path
    web_password: str | None = None
    web_secret: str | None = None

    @property
    def new_listing_url(self) -> str:
        """URL de la page 'nouvel article' de Vinted."""
        return f"{self.base_url.rstrip('/')}/items/new"

    def ensure_dirs(self) -> None:
        """Crée les répertoires de travail si nécessaire."""
        self.app_dir.mkdir(parents=True, exist_ok=True)
        self.chrome_profile_dir.mkdir(parents=True, exist_ok=True)
        self.drafts_dir.mkdir(parents=True, exist_ok=True)


def load_config() -> Config:
    """Construit la configuration à partir de l'environnement / `.env`."""
    load_dotenv()

    app_dir = APP_DIR
    debug_port = int(os.environ.get("VINTED_DEBUG_PORT", DEFAULT_DEBUG_PORT))
    cdp_url = os.environ.get("VINTED_CDP_URL", f"http://localhost:{debug_port}")

    return Config(
        anthropic_api_key=os.environ.get("ANTHROPIC_API_KEY"),
        model=os.environ.get("VINTED_AI_MODEL", DEFAULT_MODEL),
        base_url=os.environ.get("VINTED_BASE_URL", DEFAULT_BASE_URL),
        cdp_url=cdp_url,
        debug_port=debug_port,
        app_dir=app_dir,
        chrome_profile_dir=app_dir / "chrome-profile",
        drafts_dir=app_dir / "drafts",
        web_password=os.environ.get("VINTED_WEB_PASSWORD") or None,
        web_secret=os.environ.get("VINTED_WEB_SECRET") or None,
    )
