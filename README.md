# Assistant Vinted 🧥🤖

Un assistant IA personnel qui, **à partir de ta description de l'article (et,
si tu veux, de photos)**, rédige une annonce Vinted qui vend vite (titre,
description, hashtags, mots-clés, mesures à ajouter, prix indicatif) selon les
bonnes pratiques de vente, puis **pré-remplit l'annonce dans _ton_ navigateur**
en réutilisant ta session Vinted déjà ouverte.

Le texte que tu fournis est la source principale ; **les photos sont
facultatives** (elles ne servent qu'à confirmer/compléter).

> ⚠️ **L'assistant ne publie JAMAIS une annonce automatiquement.** Il prépare
> tout et s'arrête ; vous vérifiez et publiez vous-même dans le navigateur.

---

## Comment ça marche

```
Ta description (+ photos facultatives) ──▶ Rédaction (Claude) ──▶ Fiche d'annonce
                                                                      │
                                                            ▶ TU valides / édites
                                                                      │
                                              (connexion à ton Chrome via CDP)
                                                                      ▼
                                          Pré-remplissage du formulaire Vinted
                                            (titre, description, photos…)
                                                                      │
                                                            ▶ Tu publies à la main
```

- **Rédaction** : ta description (et les photos si tu en ajoutes) est envoyée à
  un modèle Claude qui produit une annonce optimisée selon les bonnes pratiques
  Vinted (titre, description structurée, caractéristiques, hashtags, mots-clés,
  mesures à ajouter, prix indicatif).
- **Navigateur** : l'outil se connecte à votre Chrome via le **protocole CDP**
  (débogage distant). Il **réutilise votre session Vinted** — il ne voit jamais
  votre identifiant ni votre mot de passe (vous vous connectez à Vinted
  vous-même, une seule fois, dans le navigateur).
- **Garde-fou** : aucun clic sur un bouton « Publier ». Jamais.

L'outil s'exécute **sur votre machine** (c'est lui qui pilote votre navigateur
local).

---

## Installation

Prérequis : **Python 3.10+** et **Google Chrome** installés.

```bash
# 1. Récupérer le projet, puis dans le dossier :
python -m venv .venv
source .venv/bin/activate          # Windows : .venv\Scripts\activate

# 2. Installer les dépendances
pip install -r requirements.txt
# (ou, pour la commande `vinted-assistant` : pip install -e .)
```

> 💡 Pas besoin de `playwright install` : l'outil se connecte à **votre** Chrome,
> il n'a pas besoin de télécharger un navigateur.

### Clé API Anthropic

L'analyse des photos nécessite une clé API Anthropic :

```bash
cp .env.example .env
# éditez .env et renseignez ANTHROPIC_API_KEY=sk-ant-...
```

(Alternative : `ant auth login` si vous utilisez déjà la CLI Anthropic.)

---

## Utilisation

Deux façons de travailler : l'**interface web** (recommandée — glisser-déposer)
ou la **ligne de commande**. Les deux utilisent le même moteur d'analyse.

### 🖥️ Interface web (recommandé)

```bash
python -m vinted_assistant web
```

Le navigateur s'ouvre sur l'interface locale. **Décris ton article** (marque,
taille, état, saison, défauts…), ajoute éventuellement des photos, et clique sur
**« Générer la fiche »**. Tu obtiens une fiche détaillée et **entièrement
éditable**, rédigée selon les bonnes pratiques Vinted :

- description structurée pour vendre vite : 1re ligne scannable
  « Marque • Taille • État », blocs courts (détails factuels, état honnête,
  contexte, conditions), des faits plutôt que des adjectifs vides ;
- caractéristiques, hashtags, mots-clés « comme un acheteur », et une liste de
  **mesures à ajouter** (elles rassurent et accélèrent la vente) ;
- prix conseillé indicatif ;
- un bouton **Copier** par champ, et **« Copier toute la fiche »** ;
- un bouton **« Pré-remplir dans Vinted »** qui envoie tout dans le formulaire
  d'annonce de ton navigateur — **sans jamais publier**.

Les **photos sont facultatives** : tu peux générer la fiche à partir du texte
seul. Pour utiliser le bouton « Pré-remplir dans Vinted », lance d'abord Chrome
connecté à l'assistant (voir ci-dessous). Pour seulement obtenir la fiche à
copier-coller, la clé API suffit.

> 💳 **La génération consomme des crédits Anthropic.** Si tu vois « credit
> balance is too low », ajoute des crédits sur console.anthropic.com →
> Plans & Billing (quelques euros suffisent, une fiche coûte des centimes).

#### 📱 Ouvrir l'app depuis ton téléphone

L'app tourne sur ton ordinateur ; pour l'ouvrir depuis ton téléphone (sur le
**même Wi-Fi**), lance-la avec l'option `--lan` :

```bash
python -m vinted_assistant web --lan
```

Le terminal affiche alors l'URL à taper sur le téléphone (ex.
`http://192.168.1.42:5000`) **et un QR code** : scanne-le avec l'appareil photo
de ton téléphone pour ouvrir l'app directement. Tu décris l'article et tu copies
la fiche depuis le téléphone.

Notes :
- macOS peut demander d'**autoriser les connexions entrantes** la première fois
  → clique « Autoriser ».
- N'utilise `--lan` que sur un **Wi-Fi de confiance** : toute personne sur le
  réseau peut alors ouvrir l'app (et chaque génération consomme tes crédits).
- Le bouton « Pré-remplir dans Vinted » pilote le Chrome de l'ordinateur ; depuis
  le téléphone, utilise plutôt **« Copier toute la fiche »** puis colle dans
  l'appli Vinted.

### 🔌 Lancer Chrome connecté à l'assistant

Nécessaire uniquement pour le pré-remplissage automatique dans Vinted.

```bash
python -m vinted_assistant launch
```

Cela ouvre **Chrome avec un profil dédié** et le débogage distant activé, puis
va sur Vinted. **Connectez-vous à Vinted dans cette fenêtre** (uniquement la
première fois : la session est mémorisée dans ce profil).

> **Pourquoi un profil dédié ?** Depuis Chrome 136, le débogage distant est
> refusé sur le profil Chrome par défaut (sécurité). L'assistant utilise donc un
> profil séparé (`~/.vinted-assistant/chrome-profile`). Vous vous y connectez à
> Vinted une fois, et c'est réglé. Vos identifiants ne transitent jamais par
> l'outil.

Vérifiez que tout est prêt :

```bash
python -m vinted_assistant check
```

### ⌨️ En ligne de commande (alternative)

```bash
# Plusieurs photos :
python -m vinted_assistant create photo1.jpg photo2.jpg photo3.jpg

# …ou tout un dossier :
python -m vinted_assistant create --dir ./mon-article

# …avec un contexte utile (facultatif) :
python -m vinted_assistant create --dir ./mon-article \
  --context "taille M, portée 2 fois, achetée en 2023"
```

L'assistant :
1. analyse les photos et **affiche** les caractéristiques + l'annonce proposée ;
2. enregistre un brouillon JSON dans `~/.vinted-assistant/drafts/` ;
3. **vous demande quoi faire** :
   - `p` — **pré-remplir** l'annonce dans le navigateur (après confirmation) ;
   - `e` — **éditer** le titre / la description / les tags (dans `$EDITOR`) ;
   - `c` — **copier** le texte dans un fichier `.txt` ;
   - `a` — **annuler**.

Après le pré-remplissage, **vous complétez les derniers champs** (catégorie,
taille, prix, état) et **vous publiez vous-même**.

### Options utiles

| Option | Effet |
|---|---|
| `--no-browser` | Analyse + export texte seulement, sans toucher au navigateur. |
| `--no-photos-upload` | Ne pas déposer les photos automatiquement. |
| `--json` | Sortie JSON brute (scripting). |
| `--yes` | Pré-remplir directement après analyse (toujours **sans publier**). |
| `--model` | Choisir le modèle (ex. `--model claude-sonnet-5` pour réduire le coût). |

---

## Configuration (`.env`)

| Variable | Rôle | Défaut |
|---|---|---|
| `ANTHROPIC_API_KEY` | Clé API pour l'analyse vision. | — |
| `VINTED_AI_MODEL` | Modèle Claude. | `claude-opus-5` |
| `VINTED_BASE_URL` | Domaine Vinted (`.fr`, `.com`, `.de`…). | `https://www.vinted.fr` |
| `VINTED_DEBUG_PORT` | Port de débogage Chrome. | `9222` |
| `VINTED_CDP_URL` | URL CDP complète. | `http://localhost:9222` |
| `VINTED_AI_HOME` | Répertoire de travail. | `~/.vinted-assistant` |

---

## Sécurité & vie privée

- **Aucune publication automatique.** Le code ne clique jamais sur « Publier » —
  c'est un choix d'architecture (voir `vinted_assistant/browser.py`).
- **Vos identifiants restent chez vous.** Vous vous connectez à Vinted dans le
  navigateur ; l'outil réutilise seulement la session ouverte.
- **Vos photos** sont envoyées à l'API Anthropic pour l'analyse vision. Ne
  traitez que des articles que vous acceptez d'analyser ainsi.
- Le profil Chrome dédié et les brouillons sont stockés localement dans
  `~/.vinted-assistant/` (ignoré par git).

---

## Dépannage

- **« Navigateur inaccessible »** → lancez `python -m vinted_assistant launch`
  et gardez la fenêtre ouverte. Vérifiez le port (`check`).
- **Chrome ne s'ouvre pas** → indiquez le chemin : `launch --chrome-path "/chemin/vers/chrome"`.
- **Titre/description non remplis** → Vinted fait évoluer son formulaire. Les
  sélecteurs sont dans `vinted_assistant/browser.py`
  (`TITLE_SELECTORS`, `DESCRIPTION_SELECTORS`) et faciles à ajuster. En attendant,
  utilisez `c` pour copier le texte et le coller manuellement.
- **Photos non déposées** → ajoutez-les manuellement ; le reste de l'annonce est
  quand même pré-rempli.

---

## Développement

```bash
pip install -r requirements.txt pytest
python -m pytest -q
```

Structure du projet :

```
vinted_assistant/
├── cli.py         # interface en ligne de commande (launch / check / web / create)
├── webapp.py      # serveur Flask local + API (analyse, pré-remplissage)
├── web/index.html # interface web (glisser-déposer, fiche éditable) — autonome
├── analysis.py    # encodage des images + appel vision Claude (sortie structurée)
├── models.py      # modèles Pydantic (caractéristiques + annonce)
├── prompts.py     # invites en français
├── browser.py     # connexion CDP + pré-remplissage Vinted (ne publie jamais)
├── launcher.py    # lancement de Chrome (débogage distant + profil dédié)
├── display.py     # affichage terminal (rich)
└── config.py      # configuration / variables d'environnement
```
