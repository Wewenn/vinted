"""Connexion au navigateur Chrome de l'utilisateur (CDP) et pré-remplissage Vinted.

Principe : l'utilisateur lance Chrome avec le port de débogage distant activé
(voir la commande `launch`). L'assistant s'y connecte via Playwright
(`connect_over_cdp`) et réutilise la session Vinted déjà ouverte — il ne voit
jamais l'identifiant ni le mot de passe.

GARDE-FOU DE SÉCURITÉ
---------------------
Ce module ne clique JAMAIS sur un bouton de publication / envoi. Il se contente
d'ouvrir la page « nouvel article », d'y déposer les photos et de pré-remplir le
titre et la description. La publication reste une action manuelle de
l'utilisateur, après sa validation dans le navigateur.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Sequence

from .models import VintedListing

# Sélecteurs candidats (Vinted fait évoluer son DOM : on essaie plusieurs pistes).
TITLE_SELECTORS = [
    'input[data-testid="title--input"]',
    'input[name="title"]',
    "#title",
    'input[aria-label*="titre" i]',
]
DESCRIPTION_SELECTORS = [
    'textarea[data-testid="description--input"]',
    'textarea[name="description"]',
    "#description",
    'textarea[aria-label*="décri" i]',
]
FILE_INPUT_SELECTORS = [
    'input[type="file"]',
]


class BrowserError(RuntimeError):
    """Erreur liée au navigateur / à la connexion CDP."""


@dataclass
class PrefillReport:
    """Compte rendu de ce qui a été pré-rempli automatiquement."""

    photos_uploaded: int = 0
    title_filled: bool = False
    description_filled: bool = False
    notes: List[str] = field(default_factory=list)

    @property
    def anything_done(self) -> bool:
        return self.photos_uploaded > 0 or self.title_filled or self.description_filled


@dataclass
class BrowserSession:
    """Session Playwright connectée au Chrome de l'utilisateur.

    À utiliser comme gestionnaire de contexte. La fermeture arrête uniquement le
    pilote Playwright : le navigateur de l'utilisateur reste ouvert.
    """

    cdp_url: str
    _pw = None
    _browser = None
    context = None

    def __enter__(self) -> "BrowserSession":
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:  # pragma: no cover - dépend de l'install
            raise BrowserError(
                "Playwright n'est pas installé. Faites : pip install playwright"
            ) from exc

        self._pw = sync_playwright().start()
        try:
            self._browser = self._pw.chromium.connect_over_cdp(self.cdp_url)
        except Exception as exc:
            self._pw.stop()
            raise BrowserError(
                f"Impossible de se connecter au navigateur sur {self.cdp_url}. "
                "Chrome est-il lancé avec le débogage distant ? "
                "Utilisez la commande `launch`.\nDétail : " + str(exc)
            ) from exc

        contexts = self._browser.contexts
        self.context = contexts[0] if contexts else self._browser.new_context()
        return self

    def __exit__(self, *_exc) -> None:
        # On ne ferme PAS le navigateur de l'utilisateur ; on arrête juste le pilote.
        if self._pw is not None:
            try:
                self._pw.stop()
            except Exception:  # pragma: no cover
                pass


def check_connection(cdp_url: str) -> bool:
    """Teste si l'on peut se connecter au navigateur via CDP."""
    try:
        with BrowserSession(cdp_url):
            return True
    except BrowserError:
        return False


def _first_visible(page, selectors: Sequence[str], timeout: float = 4000):
    """Retourne le premier locator visible parmi les sélecteurs, sinon None."""
    for selector in selectors:
        try:
            locator = page.locator(selector).first
            locator.wait_for(state="visible", timeout=timeout)
            return locator
        except Exception:
            continue
    return None


def _find_page_on_vinted(context, base_url: str):
    """Renvoie un onglet déjà ouvert sur Vinted, s'il en existe un."""
    host = base_url.split("//")[-1].split("/")[0].replace("www.", "")
    for page in context.pages:
        try:
            if host in (page.url or ""):
                return page
        except Exception:
            continue
    return None


def open_new_listing(context, new_listing_url: str, reuse_existing: bool = True):
    """Ouvre (ou réutilise) un onglet sur la page « nouvel article » de Vinted."""
    page = None
    if reuse_existing:
        page = _find_page_on_vinted(context, new_listing_url)
    if page is None:
        page = context.new_page()

    try:
        page.goto(new_listing_url, wait_until="domcontentloaded", timeout=30000)
    except Exception as exc:
        raise BrowserError(
            f"Impossible d'ouvrir {new_listing_url} : {exc}"
        ) from exc

    try:
        page.bring_to_front()
    except Exception:  # pragma: no cover
        pass
    return page


def upload_photos(page, image_paths: Sequence[Path], report: PrefillReport) -> None:
    """Dépose les photos dans le premier champ de fichier trouvé (best-effort)."""
    paths = [str(Path(p)) for p in image_paths]
    for selector in FILE_INPUT_SELECTORS:
        try:
            file_input = page.locator(selector).first
            file_input.wait_for(state="attached", timeout=5000)
            file_input.set_input_files(paths)
            report.photos_uploaded = len(paths)
            report.notes.append(f"{len(paths)} photo(s) déposée(s).")
            return
        except Exception:
            continue
    report.notes.append(
        "Champ d'upload de photos introuvable : ajoutez les photos manuellement."
    )


def fill_text_fields(page, listing: VintedListing, report: PrefillReport) -> None:
    """Pré-remplit le titre et la description (best-effort)."""
    title = _first_visible(page, TITLE_SELECTORS)
    if title is not None:
        try:
            title.fill(listing.title)
            report.title_filled = True
        except Exception:
            report.notes.append("Titre : champ trouvé mais non rempli.")
    else:
        report.notes.append("Champ « titre » introuvable (à remplir manuellement).")

    description = _first_visible(page, DESCRIPTION_SELECTORS)
    if description is not None:
        try:
            description.fill(listing.description)
            report.description_filled = True
        except Exception:
            report.notes.append("Description : champ trouvé mais non rempli.")
    else:
        report.notes.append(
            "Champ « description » introuvable (à remplir manuellement)."
        )


def prefill_listing(
    cdp_url: str,
    new_listing_url: str,
    listing: VintedListing,
    image_paths: Sequence[Path],
    upload_images: bool = True,
) -> PrefillReport:
    """Se connecte au navigateur et pré-remplit l'annonce, SANS jamais publier.

    Returns:
        Un :class:`PrefillReport` décrivant ce qui a été fait.
    """
    report = PrefillReport()
    with BrowserSession(cdp_url) as session:
        page = open_new_listing(session.context, new_listing_url)
        if upload_images and image_paths:
            upload_photos(page, image_paths, report)
        fill_text_fields(page, listing, report)
        # Volontairement : aucun clic sur un bouton de publication.
        report.notes.append(
            "Vérifiez la catégorie, la taille, le prix et l'état dans le "
            "navigateur, puis publiez vous-même. L'assistant ne publie jamais."
        )
    return report
