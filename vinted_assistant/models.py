"""Modèles de données (Pydantic) pour l'analyse d'un article et l'annonce Vinted.

Ces modèles servent aussi de schéma de sortie structurée pour l'appel au modèle
de vision (`client.messages.parse(output_format=VintedListing)`). Les
descriptions de champs sont volontairement rédigées en français : elles sont
transmises au modèle et guident directement l'extraction.
"""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class ProductAttributes(BaseModel):
    """Caractéristiques de l'article identifiées à partir des photos.

    Chaque champ optionnel doit rester `null` lorsque l'information n'est pas
    visible ou identifiable avec un minimum de confiance. Ne jamais inventer.
    """

    product_type: Optional[str] = Field(
        default=None,
        description="Type de produit (ex. 'jean slim', 'robe midi', 'sneakers', "
        "'sac à main'). null si indéterminable.",
    )
    brand: Optional[str] = Field(
        default=None,
        description="Marque identifiée (logo, étiquette, style caractéristique). "
        "null si non identifiable avec confiance.",
    )
    model: Optional[str] = Field(
        default=None,
        description="Modèle ou nom de gamme précis si identifiable "
        "(ex. 'Air Force 1', '501'). null sinon.",
    )
    color: Optional[str] = Field(
        default=None,
        description="Couleur(s) principale(s) de l'article.",
    )
    material: Optional[str] = Field(
        default=None,
        description="Matière si visible sur une étiquette ou clairement "
        "identifiable (ex. 'coton', 'cuir', 'laine'). null sinon.",
    )
    style: Optional[str] = Field(
        default=None,
        description="Style / esprit du produit (ex. 'vintage', 'streetwear', "
        "'chic', 'sport', 'bohème').",
    )
    size: Optional[str] = Field(
        default=None,
        description="Taille lisible sur une étiquette ou une photo "
        "(ex. 'M', '40', 'W32 L34'). null si non visible.",
    )
    condition: Optional[str] = Field(
        default=None,
        description="État apparent de l'article, formulé pour Vinted "
        "(ex. 'Neuf avec étiquette', 'Très bon état', 'Bon état', "
        "'Satisfaisant').",
    )
    defects: List[str] = Field(
        default_factory=list,
        description="Défauts visibles (taches, trous, bouloches, usure, "
        "décoloration...). Liste vide si aucun défaut visible.",
    )
    highlights: List[str] = Field(
        default_factory=list,
        description="Détails intéressants ou vendeurs (coupe, finitions, "
        "édition limitée, accessoire fourni...).",
    )


class VintedListing(BaseModel):
    """Brouillon complet d'annonce Vinted prêt à être validé par l'utilisateur."""

    attributes: ProductAttributes = Field(
        description="Caractéristiques détaillées de l'article."
    )
    title: str = Field(
        description="Titre d'annonce court et accrocheur (idéalement "
        "marque + type + détail marquant), max ~70 caractères.",
    )
    description: str = Field(
        description="Description Vinted en français, courte mais suffisamment "
        "détaillée (3 à 6 phrases) : type, marque, taille, matière, état, "
        "défauts éventuels et atouts. Honnête et sans invention.",
    )
    hashtags: List[str] = Field(
        default_factory=list,
        description="Hashtags pertinents en minuscules, sans espace, sans '#' "
        "(ex. 'vintage', 'levis', 'jeanslim'). 5 à 10 éléments.",
    )
    keywords: List[str] = Field(
        default_factory=list,
        description="Mots-clés de recherche cohérents avec le produit "
        "(termes que les acheteurs taperaient). 5 à 12 éléments.",
    )
    suggested_price_eur: Optional[float] = Field(
        default=None,
        description="Estimation INDICATIVE de prix en euros (fourchette basse), "
        "à titre d'aide uniquement. null si trop incertain.",
    )
    confidence_notes: Optional[str] = Field(
        default=None,
        description="Courte note sur les incertitudes ou éléments à vérifier "
        "par l'utilisateur (ex. 'marque supposée', 'taille non visible').",
    )

    def hashtags_line(self) -> str:
        """Retourne les hashtags formatés avec '#' pour l'affichage/collage."""
        return " ".join(f"#{tag.lstrip('#')}" for tag in self.hashtags)
