"""Affichage terminal du brouillon d'annonce (via `rich`)."""

from __future__ import annotations

from .models import VintedListing

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text

    _RICH = True
except Exception:  # pragma: no cover - fallback si rich absent
    _RICH = False


def _plain(value) -> str:
    if value is None:
        return "—"
    if isinstance(value, (list, tuple)):
        return ", ".join(str(v) for v in value) if value else "—"
    return str(value)


def render_listing(listing: VintedListing, photo_count: int) -> None:
    """Affiche le brouillon d'annonce de façon lisible dans le terminal."""
    if not _RICH:
        _render_plain(listing, photo_count)
        return

    console = Console()
    attrs = listing.attributes

    table = Table(show_header=False, box=None, padding=(0, 1))
    table.add_column("Champ", style="bold cyan", no_wrap=True)
    table.add_column("Valeur", overflow="fold")
    rows = [
        ("Type", attrs.product_type),
        ("Marque", attrs.brand),
        ("Modèle", attrs.model),
        ("Couleur", attrs.color),
        ("Matière", attrs.material),
        ("Style", attrs.style),
        ("Taille", attrs.size),
        ("État", attrs.condition),
        ("Défauts", attrs.defects),
        ("Atouts", attrs.highlights),
    ]
    for label, value in rows:
        table.add_row(label, _plain(value))

    console.print()
    console.print(
        Panel(table, title="[bold]Caractéristiques détectées[/bold]", border_style="cyan")
    )

    body = Text()
    body.append("Titre\n", style="bold cyan")
    body.append(listing.title + "\n\n")
    body.append("Description\n", style="bold cyan")
    body.append(listing.description + "\n\n")
    body.append("Hashtags\n", style="bold cyan")
    body.append(listing.hashtags_line() + "\n\n")
    body.append("Mots-clés\n", style="bold cyan")
    body.append(_plain(listing.keywords) + "\n")
    if listing.suggested_price_eur is not None:
        body.append("\nEstimation de prix (indicative)\n", style="bold cyan")
        body.append(f"~ {listing.suggested_price_eur:.0f} €\n")
    if listing.confidence_notes:
        body.append("\nÀ vérifier\n", style="bold yellow")
        body.append(listing.confidence_notes + "\n")

    console.print(Panel(body, title="[bold]Annonce proposée[/bold]", border_style="green"))
    console.print(
        f"[dim]Basé sur {photo_count} photo(s). "
        "Rien n'est publié : vous validez chaque étape.[/dim]\n"
    )


def _render_plain(listing: VintedListing, photo_count: int) -> None:
    attrs = listing.attributes
    print("\n=== Caractéristiques détectées ===")
    print(f"Type      : {_plain(attrs.product_type)}")
    print(f"Marque    : {_plain(attrs.brand)}")
    print(f"Modèle    : {_plain(attrs.model)}")
    print(f"Couleur   : {_plain(attrs.color)}")
    print(f"Matière   : {_plain(attrs.material)}")
    print(f"Style     : {_plain(attrs.style)}")
    print(f"Taille    : {_plain(attrs.size)}")
    print(f"État      : {_plain(attrs.condition)}")
    print(f"Défauts   : {_plain(attrs.defects)}")
    print(f"Atouts    : {_plain(attrs.highlights)}")
    print("\n=== Annonce proposée ===")
    print(f"Titre       : {listing.title}")
    print(f"\nDescription :\n{listing.description}")
    print(f"\nHashtags    : {listing.hashtags_line()}")
    print(f"Mots-clés   : {_plain(listing.keywords)}")
    if listing.suggested_price_eur is not None:
        print(f"Prix (indicatif) : ~ {listing.suggested_price_eur:.0f} €")
    if listing.confidence_notes:
        print(f"À vérifier  : {listing.confidence_notes}")
    print(f"\n(Basé sur {photo_count} photo(s). Rien n'est publié sans votre validation.)\n")
