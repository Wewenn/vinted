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
        description=(
            "Description Vinted PRÊTE À PUBLIER, rédigée pour vendre vite "
            "(80 à 200 mots, en blocs courts séparés par des sauts de ligne). "
            "Structure :\n"
            "1) Première ligne scannable : « Marque • Taille • État » "
            "(ex. « Nike • Taille M • Très bon état »).\n"
            "2) Détails concrets : type, coupe, couleur exacte, matière, "
            "particularités — des FAITS, pas d'adjectifs vides (évite "
            "« magnifique », « sublime », « superbe » : personne ne les cherche).\n"
            "3) État honnête : précise l'usure ou les défauts s'il y en a.\n"
            "4) Contexte court (occasion de port, raison de vente) puis "
            "conditions : prix négociable, réduction sur lot, envoi rapide et "
            "soigné.\n"
            "Base-toi EN PRIORITÉ sur les informations fournies par le vendeur. "
            "N'invente jamais un fait non fourni et non visible."
        ),
    )
    measurements_to_add: List[str] = Field(
        default_factory=list,
        description=(
            "Mesures à plat que le vendeur devrait relever puis ajouter pour "
            "rassurer l'acheteur (elles réduisent fortement l'hésitation). "
            "Adapte au type d'article : pour un haut/maillot → "
            "« largeur poitrine (d'aisselle à aisselle) », « longueur totale » ; "
            "pour un pantalon → « tour de taille à plat », « entrejambe » ; "
            "pour des chaussures → « longueur semelle intérieure ». 2 à 4 éléments."
        ),
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
