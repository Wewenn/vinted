"""Assistant IA personnel pour créer des annonces Vinted à partir de photos.

Le paquet fournit :
- l'analyse visuelle des photos d'un article via un modèle de vision Claude ;
- la génération d'un titre, d'une description, de hashtags et de mots-clés ;
- la connexion au navigateur Chrome de l'utilisateur (via CDP) pour réutiliser
  la session Vinted déjà ouverte et pré-remplir l'annonce ;
- un garde-fou : l'outil ne publie JAMAIS une annonce automatiquement.
"""

__version__ = "0.1.0"
