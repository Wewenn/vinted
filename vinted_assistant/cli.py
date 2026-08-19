"""Interface en ligne de commande de l'assistant Vinted.

Commandes :
- ``launch`` : lance Chrome avec le débogage distant et un profil dédié.
- ``check``  : vérifie la configuration (clé API, connexion au navigateur).
- ``create`` : analyse des photos, propose une annonce, et — après votre
  validation explicite — pré-remplit l'annonce dans le navigateur (sans jamais
  publier).
"""

from __future__ import annotations

import argparse
import datetime as _dt
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import List, Optional

from . import __version__
from .analysis import AnalysisError, analyze_photos, resolve_image_paths
from .config import Config, load_config
from .display import render_listing
from .models import VintedListing


# --------------------------------------------------------------------------- #
# Utilitaires d'affichage / de saisie
# --------------------------------------------------------------------------- #

def _echo(message: str = "") -> None:
    print(message)


def _prompt(question: str, default: str = "") -> str:
    try:
        answer = input(question).strip()
    except (EOFError, KeyboardInterrupt):
        _echo()
        return default
    return answer or default


def _build_client():
    """Construit un client Anthropic (les identifiants viennent de l'environnement)."""
    try:
        import anthropic
    except ImportError as exc:
        raise SystemExit(
            "Le paquet `anthropic` n'est pas installé. Faites : pip install anthropic"
        ) from exc
    return anthropic.Anthropic()


# --------------------------------------------------------------------------- #
# Commande : launch
# --------------------------------------------------------------------------- #

def cmd_launch(args: argparse.Namespace, config: Config) -> int:
    from .launcher import LauncherError, launch_chrome

    start_url = None if args.no_open else config.base_url
    try:
        launch_chrome(
            profile_dir=config.chrome_profile_dir,
            debug_port=config.debug_port,
            start_url=start_url,
            chrome_path=args.chrome_path,
        )
    except LauncherError as exc:
        _echo(f"❌ {exc}")
        return 1

    _echo("✅ Chrome lancé avec le débogage distant.")
    _echo(f"   Port CDP        : {config.debug_port}")
    _echo(f"   Profil dédié    : {config.chrome_profile_dir}")
    _echo("")
    _echo("👉 Dans cette fenêtre Chrome, connectez-vous à Vinted si ce n'est pas")
    _echo("   déjà fait (la première fois seulement — la session sera mémorisée).")
    _echo("   Laissez ce Chrome ouvert, puis lancez la commande `create`.")
    return 0


# --------------------------------------------------------------------------- #
# Commande : check
# --------------------------------------------------------------------------- #

def cmd_check(args: argparse.Namespace, config: Config) -> int:
    from .browser import check_connection

    _echo("Vérification de la configuration…\n")

    # Clé API.
    if config.anthropic_api_key:
        _echo("✅ Clé API Anthropic détectée (ANTHROPIC_API_KEY).")
    else:
        _echo(
            "⚠️  ANTHROPIC_API_KEY non définie. Définissez-la, ou connectez-vous "
            "via `ant auth login`."
        )

    _echo(f"   Modèle configuré : {config.model}")
    _echo(f"   Vinted           : {config.base_url}")

    # Connexion navigateur.
    _echo(f"\nConnexion au navigateur sur {config.cdp_url} …")
    if check_connection(config.cdp_url):
        _echo("✅ Navigateur accessible (session réutilisable).")
        return 0
    _echo("❌ Navigateur inaccessible. Lancez d'abord : vinted-assistant launch")
    return 1


# --------------------------------------------------------------------------- #
# Commande : create
# --------------------------------------------------------------------------- #

def _save_draft(config: Config, listing: VintedListing) -> Path:
    stamp = _dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    path = config.drafts_dir / f"draft-{stamp}.json"
    path.write_text(listing.model_dump_json(indent=2), encoding="utf-8")
    return path


def _listing_as_text(listing: VintedListing) -> str:
    lines = [
        listing.title,
        "",
        listing.description,
        "",
        listing.hashtags_line(),
    ]
    if listing.keywords:
        lines.append("")
        lines.append("Mots-clés : " + ", ".join(listing.keywords))
    return "\n".join(lines)


def _copy_to_file(config: Config, listing: VintedListing) -> Path:
    stamp = _dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    path = config.drafts_dir / f"annonce-{stamp}.txt"
    path.write_text(_listing_as_text(listing), encoding="utf-8")
    return path


def _edit_listing(listing: VintedListing) -> VintedListing:
    """Ouvre le brouillon dans $EDITOR pour édition, puis renvoie la version modifiée."""
    template = (
        "# Titre\n"
        f"{listing.title}\n\n"
        "# Description\n"
        f"{listing.description}\n\n"
        "# Hashtags (séparés par des espaces)\n"
        f"{' '.join(listing.hashtags)}\n\n"
        "# Mots-clés (séparés par des virgules)\n"
        f"{', '.join(listing.keywords)}\n"
    )
    editor = os.environ.get("EDITOR") or ("notepad" if os.name == "nt" else "nano")

    with tempfile.NamedTemporaryFile(
        "w+", suffix=".txt", delete=False, encoding="utf-8"
    ) as tmp:
        tmp.write(template)
        tmp_path = Path(tmp.name)

    try:
        subprocess.call([editor, str(tmp_path)])
        edited = tmp_path.read_text(encoding="utf-8")
    except Exception as exc:
        _echo(f"⚠️  Édition impossible ({exc}). Brouillon inchangé.")
        return listing
    finally:
        try:
            tmp_path.unlink()
        except OSError:
            pass

    return _apply_edits(listing, edited)


def _apply_edits(listing: VintedListing, edited: str) -> VintedListing:
    """Analyse le texte édité (sections `# ...`) et met à jour le brouillon."""
    sections: dict[str, List[str]] = {}
    current: Optional[str] = None
    for line in edited.splitlines():
        if line.startswith("# "):
            current = line[2:].split("(")[0].strip().lower()
            sections[current] = []
        elif current is not None:
            sections[current].append(line)

    def _text(key: str) -> str:
        return "\n".join(sections.get(key, [])).strip()

    title = _text("titre") or listing.title
    description = _text("description") or listing.description
    hashtags_raw = _text("hashtags")
    keywords_raw = _text("mots-clés") or _text("mots-cles")

    updated = listing.model_copy(deep=True)
    updated.title = title
    updated.description = description
    if hashtags_raw:
        updated.hashtags = [
            t.lstrip("#") for t in hashtags_raw.split() if t.strip()
        ]
    if keywords_raw:
        updated.keywords = [k.strip() for k in keywords_raw.split(",") if k.strip()]
    return updated


def _do_prefill(config: Config, listing: VintedListing, paths: List[Path],
                upload_images: bool) -> None:
    from .browser import BrowserError, prefill_listing

    _echo("\nConnexion au navigateur et pré-remplissage…")
    try:
        report = prefill_listing(
            cdp_url=config.cdp_url,
            new_listing_url=config.new_listing_url,
            listing=listing,
            image_paths=paths,
            upload_images=upload_images,
        )
    except BrowserError as exc:
        _echo(f"❌ {exc}")
        _echo("   Astuce : lancez d'abord `vinted-assistant launch`.")
        return

    _echo("\n— Compte rendu —")
    _echo(f"   Photos déposées   : {report.photos_uploaded}")
    _echo(f"   Titre pré-rempli  : {'oui' if report.title_filled else 'non'}")
    _echo(f"   Desc. pré-remplie : {'oui' if report.description_filled else 'non'}")
    for note in report.notes:
        _echo(f"   • {note}")
    _echo(
        "\n✅ Terminé. Vérifiez l'annonce dans Chrome, complétez les champs "
        "restants (catégorie, taille, prix, état) et publiez VOUS-MÊME.\n"
        "   L'assistant ne publie jamais automatiquement."
    )


def cmd_create(args: argparse.Namespace, config: Config) -> int:
    # 1. Résolution des photos.
    try:
        paths = resolve_image_paths(args.photos, directory=args.dir)
    except AnalysisError as exc:
        _echo(f"❌ {exc}")
        return 1

    _echo(f"📸 {len(paths)} photo(s) à analyser :")
    for p in paths:
        _echo(f"   • {p}")

    if not config.anthropic_api_key:
        _echo(
            "\n⚠️  ANTHROPIC_API_KEY non définie — tentative via un profil "
            "`ant auth login` existant."
        )

    # 2. Analyse.
    _echo("\n🔎 Analyse des photos en cours…")
    try:
        client = _build_client()
        listing = analyze_photos(
            client,
            paths,
            model=args.model or config.model,
            extra_context=args.context,
        )
    except AnalysisError as exc:
        _echo(f"❌ {exc}")
        return 1
    except Exception as exc:  # erreurs API / réseau
        _echo(f"❌ Échec de l'analyse : {exc}")
        return 1

    # 3. Sortie JSON éventuelle.
    if args.json:
        _echo(listing.model_dump_json(indent=2))
        _save_draft(config, listing)
        return 0

    # 4. Affichage + sauvegarde du brouillon.
    render_listing(listing, len(paths))
    draft_path = _save_draft(config, listing)
    _echo(f"💾 Brouillon enregistré : {draft_path}")

    if args.no_browser:
        text_path = _copy_to_file(config, listing)
        _echo(f"📝 Texte prêt à copier : {text_path}")
        return 0

    # 5. Boucle de validation (garde-fou : rien n'est publié).
    if args.yes:
        _do_prefill(config, listing, paths, not args.no_photos_upload)
        return 0

    while True:
        _echo(
            "\nQue voulez-vous faire ?\n"
            "  [p] Pré-remplir l'annonce dans le navigateur (sans publier)\n"
            "  [e] Éditer le titre / la description / les tags\n"
            "  [c] Copier le texte dans un fichier\n"
            "  [a] Annuler"
        )
        choice = _prompt("Choix [p/e/c/a] : ", default="a").lower()

        if choice == "p":
            confirm = _prompt(
                "Confirmer le pré-remplissage dans le navigateur ? [o/N] : ",
                default="n",
            ).lower()
            if confirm in ("o", "oui", "y", "yes"):
                _do_prefill(config, listing, paths, not args.no_photos_upload)
                return 0
            _echo("Annulé.")
        elif choice == "e":
            listing = _edit_listing(listing)
            render_listing(listing, len(paths))
            _save_draft(config, listing)
        elif choice == "c":
            text_path = _copy_to_file(config, listing)
            _echo(f"📝 Texte enregistré : {text_path}")
        elif choice in ("a", "q", "annuler"):
            _echo("Annulé. Aucun changement dans le navigateur.")
            return 0
        else:
            _echo("Choix non reconnu.")


# --------------------------------------------------------------------------- #
# Parsing des arguments
# --------------------------------------------------------------------------- #

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="vinted-assistant",
        description="Assistant IA pour créer des annonces Vinted à partir de photos.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    # launch
    p_launch = sub.add_parser(
        "launch", help="Lancer Chrome avec le débogage distant (profil dédié)."
    )
    p_launch.add_argument("--chrome-path", help="Chemin de l'exécutable Chrome.")
    p_launch.add_argument(
        "--no-open", action="store_true", help="Ne pas ouvrir Vinted au démarrage."
    )
    p_launch.set_defaults(func=cmd_launch)

    # check
    p_check = sub.add_parser("check", help="Vérifier la configuration et la connexion.")
    p_check.set_defaults(func=cmd_check)

    # create
    p_create = sub.add_parser(
        "create", help="Analyser des photos et proposer une annonce Vinted."
    )
    p_create.add_argument("photos", nargs="*", help="Chemins des photos de l'article.")
    p_create.add_argument("--dir", help="Dossier contenant les photos de l'article.")
    p_create.add_argument(
        "--context", help="Infos complémentaires (ex. « taille M, porté 2 fois »)."
    )
    p_create.add_argument("--model", help="Modèle Claude à utiliser (surcharge).")
    p_create.add_argument(
        "--no-browser",
        action="store_true",
        help="Ne pas toucher au navigateur : afficher/exporter seulement.",
    )
    p_create.add_argument(
        "--no-photos-upload",
        action="store_true",
        help="Ne pas déposer les photos automatiquement lors du pré-remplissage.",
    )
    p_create.add_argument(
        "--json", action="store_true", help="Sortie JSON brute (usage scripté)."
    )
    p_create.add_argument(
        "--yes",
        action="store_true",
        help="Pré-remplir directement après analyse (toujours sans publier).",
    )
    p_create.set_defaults(func=cmd_create)

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    config = load_config()
    config.ensure_dirs()

    if args.command == "create" and not args.photos and not args.dir:
        parser.error("fournissez des photos ou un dossier via --dir.")

    return args.func(args, config)


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
