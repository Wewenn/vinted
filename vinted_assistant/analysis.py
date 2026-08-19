"""Analyse visuelle des photos et génération de l'annonce via Claude (vision).

Le point d'entrée est :func:`analyze_photos`, qui prend un client Anthropic déjà
construit (facilite les tests), la liste des chemins de photos et un contexte
optionnel, et renvoie un :class:`~vinted_assistant.models.VintedListing`.
"""

from __future__ import annotations

import base64
import io
from pathlib import Path
from typing import Iterable, List, Sequence, Tuple

from .models import VintedListing
from .prompts import SYSTEM_PROMPT, build_user_prompt

# Extensions d'images acceptées.
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}

# Anthropic accepte jusqu'à 20 images par requête ; Vinted en accepte 20 aussi.
MAX_IMAGES = 20

# Côté long maximal recommandé pour limiter le coût en tokens.
MAX_IMAGE_DIMENSION = 1568

_MEDIA_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".gif": "image/gif",
}


class AnalysisError(RuntimeError):
    """Erreur lors de l'analyse des photos."""


def resolve_image_paths(
    inputs: Sequence[str | Path],
    directory: str | Path | None = None,
) -> List[Path]:
    """Résout et valide la liste des chemins d'images.

    Args:
        inputs: chemins de fichiers image individuels.
        directory: dossier dont on prend toutes les images (trié par nom).

    Returns:
        Liste ordonnée de chemins d'images existants.
    """
    paths: List[Path] = []

    if directory is not None:
        d = Path(directory).expanduser()
        if not d.is_dir():
            raise AnalysisError(f"Le dossier n'existe pas : {d}")
        paths.extend(
            sorted(
                p
                for p in d.iterdir()
                if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS
            )
        )

    for item in inputs:
        p = Path(item).expanduser()
        if not p.exists():
            raise AnalysisError(f"Fichier introuvable : {p}")
        if p.suffix.lower() not in IMAGE_EXTENSIONS:
            raise AnalysisError(
                f"Format d'image non supporté : {p.name} "
                f"(acceptés : {', '.join(sorted(IMAGE_EXTENSIONS))})"
            )
        paths.append(p)

    # Déduplication en conservant l'ordre.
    seen: set[Path] = set()
    unique: List[Path] = []
    for p in paths:
        rp = p.resolve()
        if rp not in seen:
            seen.add(rp)
            unique.append(p)

    if not unique:
        raise AnalysisError("Aucune image valide fournie.")

    return unique


def encode_image(path: Path, max_dimension: int = MAX_IMAGE_DIMENSION) -> Tuple[str, str]:
    """Encode une image en base64, en la redimensionnant si Pillow est présent.

    Returns:
        Un tuple ``(media_type, données_base64)``.
    """
    suffix = path.suffix.lower()
    media_type = _MEDIA_TYPES.get(suffix, "image/jpeg")

    try:
        from PIL import Image  # import local : dépendance optionnelle

        with Image.open(path) as img:
            img.load()
            needs_resize = max(img.size) > max_dimension
            if needs_resize or suffix not in (".jpg", ".jpeg", ".png"):
                if needs_resize:
                    img.thumbnail((max_dimension, max_dimension))
                buffer = io.BytesIO()
                if img.mode in ("RGBA", "P", "LA"):
                    # Conserve la transparence en PNG.
                    img.convert("RGBA").save(buffer, format="PNG", optimize=True)
                    media_type = "image/png"
                else:
                    img.convert("RGB").save(
                        buffer, format="JPEG", quality=85, optimize=True
                    )
                    media_type = "image/jpeg"
                data = buffer.getvalue()
                return media_type, base64.standard_b64encode(data).decode("utf-8")
    except ImportError:
        # Pillow absent : on envoie l'image brute (peut coûter plus de tokens).
        pass
    except Exception as exc:  # pragma: no cover - dépend du fichier
        raise AnalysisError(f"Impossible de lire l'image {path.name} : {exc}") from exc

    raw = path.read_bytes()
    return media_type, base64.standard_b64encode(raw).decode("utf-8")


def _build_content_blocks(
    image_paths: Sequence[Path], extra_context: str | None
) -> list:
    """Construit les blocs de contenu (images + texte) du message utilisateur."""
    blocks: list = []
    for path in image_paths:
        media_type, data = encode_image(path)
        blocks.append(
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": media_type,
                    "data": data,
                },
            }
        )
    blocks.append(
        {"type": "text", "text": build_user_prompt(len(image_paths), extra_context)}
    )
    return blocks


def analyze_photos(
    client,
    image_paths: Sequence[Path],
    *,
    model: str,
    extra_context: str | None = None,
    max_tokens: int = 8000,
) -> VintedListing:
    """Analyse les photos et renvoie un brouillon d'annonce structuré.

    Args:
        client: instance ``anthropic.Anthropic`` (injectée pour la testabilité).
        image_paths: chemins des photos de l'article.
        model: identifiant du modèle Claude à utiliser.
        extra_context: informations complémentaires facultatives.
        max_tokens: budget de sortie.
    """
    paths = list(image_paths)
    if not paths:
        raise AnalysisError("Aucune image à analyser.")
    if len(paths) > MAX_IMAGES:
        raise AnalysisError(
            f"Trop de photos ({len(paths)}). Maximum accepté : {MAX_IMAGES}."
        )

    content = _build_content_blocks(paths, extra_context)

    response = client.messages.parse(
        model=model,
        max_tokens=max_tokens,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": content}],
        output_format=VintedListing,
    )

    listing = getattr(response, "parsed_output", None)
    if listing is None:
        raise AnalysisError(
            "Le modèle n'a pas renvoyé de sortie structurée exploitable."
        )
    return listing
