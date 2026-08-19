"""Interface web locale : déposer des photos → fiche d'annonce détaillée.

Serveur Flask minimaliste, lié à 127.0.0.1 (usage strictement local). L'utilisateur
dépose des photos et quelques infos ; l'assistant renvoie une fiche complète et
éditable (titre, description, caractéristiques, hashtags, mots-clés, prix indicatif).
Deux actions possibles ensuite : copier la fiche, ou pré-remplir l'annonce dans le
navigateur (jamais de publication automatique).
"""

from __future__ import annotations

import secrets
import shutil
from pathlib import Path
from typing import Callable, List, Optional

from .analysis import IMAGE_EXTENSIONS, AnalysisError, analyze_photos
from .config import Config
from .models import VintedListing

WEB_DIR = Path(__file__).parent / "web"


def _default_client_factory():
    import anthropic

    return anthropic.Anthropic()


def _default_prefill_func(**kwargs):
    from .browser import prefill_listing

    return prefill_listing(**kwargs)


def _safe_name(name: str, index: int) -> str:
    """Nom de fichier sûr, en conservant l'extension d'image."""
    suffix = Path(name).suffix.lower()
    if suffix not in IMAGE_EXTENSIONS:
        suffix = ".jpg"
    return f"{index:02d}{suffix}"


def _friendly_api_error(exc: Exception) -> str:
    """Traduit les erreurs API courantes en messages clairs pour l'utilisateur."""
    text = str(exc)
    low = text.lower()
    if "credit balance is too low" in low or "purchase credits" in low:
        return (
            "Crédits Anthropic insuffisants. Ajoute des crédits sur "
            "console.anthropic.com → Plans & Billing, puis réessaie."
        )
    if "authentication" in low or "invalid x-api-key" in low or "401" in low:
        return "Clé API Anthropic invalide. Vérifie ANTHROPIC_API_KEY dans .env."
    if "rate limit" in low or "429" in low:
        return "Trop de requêtes (limite atteinte). Réessaie dans un instant."
    if "not_found" in low or "model" in low and "404" in low:
        return "Modèle introuvable. Vérifie le nom du modèle dans les options."
    return f"Échec de l'analyse : {text}"


def create_app(
    config: Config,
    client_factory: Optional[Callable] = None,
    prefill_func: Optional[Callable] = None,
):
    """Construit l'application Flask.

    Args:
        config: configuration résolue.
        client_factory: fabrique de client Anthropic (injectable pour les tests).
        prefill_func: fonction de pré-remplissage navigateur (injectable pour les tests).
    """
    from flask import Flask, jsonify, request, send_from_directory

    client_factory = client_factory or _default_client_factory
    prefill_func = prefill_func or _default_prefill_func

    uploads_root = config.app_dir / "uploads"
    uploads_root.mkdir(parents=True, exist_ok=True)

    app = Flask(__name__, static_folder=None)
    app.config["MAX_CONTENT_LENGTH"] = 60 * 1024 * 1024  # 60 Mo au total

    # ------------------------------------------------------------------ #
    # Pages statiques
    # ------------------------------------------------------------------ #
    @app.get("/")
    def index():
        return send_from_directory(WEB_DIR, "index.html")

    @app.get("/api/config")
    def api_config():
        return jsonify(
            {
                "model": config.model,
                "vinted_url": config.base_url,
                "new_listing_url": config.new_listing_url,
            }
        )

    # ------------------------------------------------------------------ #
    # Analyse des photos → fiche
    # ------------------------------------------------------------------ #
    @app.post("/api/analyze")
    def api_analyze():
        files = request.files.getlist("photos")
        files = [f for f in files if f and f.filename]
        context = (request.form.get("context") or "").strip() or None
        model = (request.form.get("model") or "").strip() or config.model

        # Photos FACULTATIVES : il faut au moins des photos OU une description.
        if not files and not context:
            return jsonify(
                {"error": "Ajoute au moins une photo ou une description de l'article."}
            ), 400

        # Sauvegarde des éventuelles photos dans un dossier de session.
        session_id = secrets.token_hex(8)
        session_dir = uploads_root / session_id
        session_dir.mkdir(parents=True, exist_ok=True)

        saved: List[Path] = []
        for i, f in enumerate(files):
            dest = session_dir / _safe_name(f.filename, i)
            f.save(dest)
            saved.append(dest)

        try:
            client = client_factory()
            listing = analyze_photos(
                client, saved, model=model, extra_context=context
            )
        except AnalysisError as exc:
            shutil.rmtree(session_dir, ignore_errors=True)
            return jsonify({"error": str(exc)}), 400
        except Exception as exc:  # erreurs API / réseau
            shutil.rmtree(session_dir, ignore_errors=True)
            return jsonify({"error": _friendly_api_error(exc)}), 502

        return jsonify(
            {
                "session_id": session_id,
                "photo_count": len(saved),
                "listing": listing.model_dump(),
            }
        )

    # ------------------------------------------------------------------ #
    # Pré-remplissage navigateur (ne publie jamais)
    # ------------------------------------------------------------------ #
    @app.post("/api/prefill")
    def api_prefill():
        data = request.get_json(silent=True) or {}
        session_id = data.get("session_id")
        listing_data = data.get("listing")
        upload_images = bool(data.get("upload_images", True))

        if not listing_data:
            return jsonify({"error": "Fiche manquante."}), 400

        try:
            listing = VintedListing.model_validate(listing_data)
        except Exception as exc:
            return jsonify({"error": f"Fiche invalide : {exc}"}), 400

        image_paths: List[Path] = []
        if session_id:
            session_dir = uploads_root / session_id
            if session_dir.is_dir():
                image_paths = sorted(
                    p for p in session_dir.iterdir()
                    if p.suffix.lower() in IMAGE_EXTENSIONS
                )

        try:
            report = prefill_func(
                cdp_url=config.cdp_url,
                new_listing_url=config.new_listing_url,
                listing=listing,
                image_paths=image_paths,
                upload_images=upload_images,
            )
        except Exception as exc:
            return jsonify({"error": str(exc)}), 502

        return jsonify(
            {
                "photos_uploaded": getattr(report, "photos_uploaded", 0),
                "title_filled": getattr(report, "title_filled", False),
                "description_filled": getattr(report, "description_filled", False),
                "notes": getattr(report, "notes", []),
            }
        )

    return app


def _lan_ip() -> Optional[str]:
    """Devine l'adresse IP de la machine sur le réseau local (sans rien envoyer)."""
    import socket

    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(("8.8.8.8", 80))  # n'émet aucun paquet en UDP
            return s.getsockname()[0]
        finally:
            s.close()
    except Exception:
        return None


def _print_qr(url: str) -> bool:
    """Affiche un QR code ASCII de l'URL dans le terminal, si `qrcode` est présent."""
    try:
        import qrcode
    except ImportError:
        return False
    qr = qrcode.QRCode(border=1)
    qr.add_data(url)
    qr.make(fit=True)
    qr.print_ascii(invert=True)
    return True


def run_server(config: Config, host: str = "127.0.0.1", port: int = 5000,
               open_browser: bool = True) -> None:
    """Démarre le serveur web local (et ouvre le navigateur par défaut).

    Si ``host`` n'est pas une adresse de bouclage (ex. ``0.0.0.0`` via l'option
    ``--lan``), l'app est accessible depuis les autres appareils du réseau
    (téléphone sur le même Wi-Fi) : on affiche alors l'URL LAN et un QR code.
    """
    app = create_app(config)
    local_url = f"http://127.0.0.1:{port}"
    exposed = host not in ("127.0.0.1", "localhost", "::1")

    if open_browser:
        import threading
        import webbrowser

        threading.Timer(1.0, lambda: webbrowser.open(local_url)).start()

    print(f"🌐 Interface locale : {local_url}   (Ctrl+C pour arrêter)")

    if exposed:
        ip = _lan_ip()
        if ip:
            lan_url = f"http://{ip}:{port}"
            print(f"📱 Depuis ton téléphone (même Wi-Fi) : {lan_url}")
            print("   Scanne ce QR code avec l'appareil photo de ton téléphone :\n")
            if not _print_qr(lan_url):
                print("   (astuce : `pip install qrcode` pour afficher un QR code)\n")
        else:
            print("📱 Accessible sur le réseau local (IP LAN non détectée).")
        print("\n⚠️  L'app est ouverte sur ton réseau local : utilise-la uniquement")
        print("   sur un Wi-Fi de confiance (chaque génération consomme tes crédits API).")
        print("   macOS peut demander d'autoriser les connexions entrantes → « Autoriser ».\n")

    app.run(host=host, port=port, debug=False)
