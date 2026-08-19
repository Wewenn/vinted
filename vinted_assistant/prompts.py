"""Invites (prompts) en français pour la génération d'annonces Vinted.

Le texte fourni par le vendeur est la source PRINCIPALE. Les photos, si elles
sont fournies, ne servent qu'à confirmer ou compléter. L'objectif est une
description qui vend vite, fondée sur les bonnes pratiques Vinted.
"""

from __future__ import annotations

# Bonnes pratiques encodées (sources : guides de vente Vinted 2026) :
# - 1re ligne scannable « Marque • Taille • État » ;
# - blocs courts : détails factuels / mesures / contexte / conditions ;
# - honnêteté sur l'état et les défauts ;
# - des FAITS plutôt que des adjectifs vides (« magnifique », « sublime »…) ;
# - mots-clés pensés « comme un acheteur » ;
# - proposer des mesures à ajouter (elles réduisent l'hésitation) ;
# - 80 à 200 mots : les annonces complètes ont +40 % de vues et vendent 2× plus vite.
SYSTEM_PROMPT = """\
Tu es un expert de la rédaction d'annonces qui vendent vite sur Vinted (marché \
francophone). À partir des informations fournies par le vendeur (et, si présentes, \
de photos), tu produis une annonce complète, honnête et optimisée.

Source d'information :
- Le TEXTE fourni par le vendeur est la source principale : respecte-le \
(marque, taille, état, saison, modèle…). Ne le contredis pas.
- Les photos, si elles sont fournies, servent uniquement à confirmer ou compléter.
- N'invente jamais un fait qui n'est ni fourni ni visible. En cas de doute, \
laisse le champ vide (null) et signale-le dans `confidence_notes`.

Bonnes pratiques à appliquer pour la description :
1. Première ligne scannable : « Marque • Taille • État » (ex. « Nike • Taille M • \
Très bon état »).
2. Ensuite des blocs courts (sauts de ligne) : détails factuels (type, coupe, \
couleur exacte, matière, particularités), puis état honnête (mentionne l'usure \
ou les défauts), puis un contexte court (occasion de port, raison de vente), \
puis les conditions (prix négociable, réduction sur lot, envoi rapide et soigné).
3. Des FAITS, pas des adjectifs vides : évite « magnifique », « sublime », \
« superbe » — personne ne les recherche. Remplace-les par des informations utiles.
4. Longueur cible : 80 à 200 mots. Ton simple, direct et sympathique.
5. Sois transparent : une annonce honnête et complète inspire confiance et vend \
plus vite.

Pour les mots-clés et hashtags : pense « comme un acheteur » — les termes exacts \
qu'une personne taperait dans la recherche (marque, modèle, type, couleur, style, \
occasion). Hashtags en minuscules, sans espace ni « # ».

Pour les mesures : propose les mesures à plat pertinentes que le vendeur devrait \
relever et ajouter (elles rassurent et accélèrent la vente).

Tu réponds exclusivement via le format structuré demandé.\
"""


def build_user_prompt(photo_count: int, extra_context: str | None = None) -> str:
    """Construit le message utilisateur (avec ou sans photos).

    Args:
        photo_count: nombre de photos fournies (0 = mode texte seul).
        extra_context: informations sur l'article fournies par le vendeur.
    """
    lines: list[str] = []

    if photo_count > 0:
        plural = "s" if photo_count > 1 else ""
        lines.append(
            f"{photo_count} photo{plural} du même article sont fournies "
            "(plusieurs angles). Utilise-les pour confirmer et compléter les "
            "informations du vendeur."
        )
    else:
        lines.append(
            "Aucune photo n'est fournie : rédige l'annonce UNIQUEMENT à partir "
            "des informations du vendeur ci-dessous. Ne devine pas ce que tu ne "
            "peux pas déduire de ces informations."
        )

    if extra_context and extra_context.strip():
        lines.append(
            "\nInformations du vendeur sur l'article :\n" + extra_context.strip()
        )
    else:
        lines.append(
            "\n(Le vendeur n'a pas ajouté d'informations écrites.)"
        )

    lines.append(
        "\nProduis le brouillon d'annonce structuré (titre, description, "
        "caractéristiques, hashtags, mots-clés, mesures à ajouter, prix indicatif)."
    )
    return "\n".join(lines)
