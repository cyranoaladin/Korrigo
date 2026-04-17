# Générateur d'appréciations DNB

Workflow Python sobre et robuste pour générer des appréciations globales de mathématiques à partir de notes détaillées d'un examen blanc de DNB (classe de troisième).

## Architecture

Le projet est découpé en modules courts et spécialisés :

| Fichier | Rôle |
|---------|------|
| `config.py` | Constantes, seuils et configuration centralisée |
| `prompt_builder.py` | Construction du *system prompt* et des *user prompts* |
| `llm_client.py` | Client HTTP minimal pour Ollama |
| `validator.py` | Validation stricte des sorties LLM |
| `fallback.py` | Génération déterministe si la LLM échoue |
| `main.py` | Orchestration, CLI, lecture/écriture CSV |

## Prérequis

- Python 3.11+
- Ollama installé et accessible localement (par défaut sur `http://localhost:11434`)
- Modèle `qwen2.5:7b` (ou tout autre modèle configuré) pullé :
  ```bash
  ollama pull qwen2.5:7b
  ```

## Installation

Aucune dépendance externe n'est requise (bibliothèque standard uniquement).

```bash
cd tools/dnb_appreciation_generator
python main.py --help
```

## Usage

### Génération classique (lot CSV)

```bash
python main.py \
  --input examples/input.csv \
  --output examples/output.csv \
  --model qwen2.5:7b \
  --temperature 0.2 \
  --mode strict
```

### Mode dry-run (visualisation sans écriture)

```bash
python main.py \
  --input examples/input.csv \
  --output /dev/null \
  --dry-run
```

### Fallback déterministe uniquement

```bash
python main.py \
  --input examples/input.csv \
  --output resultats_fallback.csv \
  --fallback-only
```

## Format d'entrée CSV

Le fichier CSV doit contenir une ligne par élève avec les colonnes suivantes :

```csv
student_id,partie1,e2_q1,e2_q2,e2_q3,e2_q4,e2_q5,e3_q1,e3_q2,e3_q3,e3_q4,e3_q5,e4_q1,e4_q2,e4_q3,e4_q4,e5_q1,e5_q2,e5_q3,e5_q4a,e5_q4b,e5_q4c,e5_q4d
```

- `partie1` : note sur 6 pour les automatismes
- `e2_q1` à `e2_q5` : exercice 2 (total 3 pts)
- `e3_q1` à `e3_q5` : exercice 3 (total 3,5 pts)
- `e4_q1` à `e4_q4` : exercice 4 (total 3 pts)
- `e5_q1` à `e5_q3`, `e5_q4a` à `e5_q4d` : exercice 5 (total 4,5 pts)

## Format de sortie CSV

Le fichier de sortie est enrichi avec les colonnes suivantes :

| Colonne | Description |
|---------|-------------|
| `partie1`, `e2_total` … | Sous-totaux recalculés |
| `total` | Note finale sur 20 |
| `level` | Niveau global déterminé (ex: *satisfaisant*) |
| `regularity` | Profil de régularité (*homogène*, *irrégulier*, *très irrégulier*) |
| `appreciation` | Appréciation finale |
| `source` | `llm` ou `fallback` |
| `status` | `ok`, `ok_fallback` ou `ok_fallback_forced` |
| `attempts` | Nombre de tentatives LLM |
| `rejection_reason` | Motif de rejet si la sortie LLM était invalide |
| `raw_text` | Texte brut retourné par la LLM |

## Logique de profil et régularité

### Niveau global

Le niveau est déterminé uniquement par le total sur 20 :

| Total | Niveau |
|-------|--------|
| 0 – 5,75 | très fragile |
| 6 – 8,75 | fragile |
| 9 – 11,75 | correct mais insuffisamment maîtrisé |
| 12 – 14,75 | satisfaisant |
| 15 – 17,74 | solide |
| 17,75 – 20 | très bonne maîtrise |

### Régularité

Chacun des 5 blocs est normalisé entre 0 et 1. Deux indicateurs sont calculés :
- **écart-type** des 5 ratios
- **écart max-min** des 5 ratios

| Conditions | Profil |
|------------|--------|
| std ≤ 0,12 **ET** max-min ≤ 0,25 | homogène |
| std ≥ 0,30 **OU** max-min ≥ 0,55 | très irrégulier |
| sinon | irrégulier |

### Validation de sortie

Chaque appréciation générée par la LLM est vérifiée :
- non vide
- une seule phrase
- entre 8 et 22 mots (cible 8-18)
- aucun chiffre
- aucun mot interdit (*copie*, *devoir*, *exercice*, *géométrie* …)
- aucune formulation creuse (*poursuivez vos efforts*, *peut mieux faire* …)
- pas de caractère de structuration (`-`, `:`, `;`, `\n` …)

Si la validation échoue, une **seconde tentative** est lancée avec un *correction prompt*. Si l'échec persiste, le **fallback déterministe** prend le relais.

## Personnalisation

Vous pouvez ajuster les paramètres via `config.py` ou les options CLI :

- `--endpoint` : URL Ollama
- `--model` : nom du modèle
- `--temperature` : créativité de la LLM (0.2 recommandé)
- `--retries` : nombre de retries (défaut 2)
- `--mode strict|permissif` : gestion des cellules vides

## Conseils pour la production

- Sur des serveurs peu puissants, privilégiez `qwen2.5:1.5b` au détriment de la finesse, ou augmentez le timeout.
- Pour un traitement batch de plusieurs centaines de copies, envisagez de paralléliser `main.py` (par exemple via `concurrent.futures.ThreadPoolExecutor` en adaptant le module `llm_client.py`).
- En cas d'indisponibilité d'Ollama, le mode `--fallback-only` garantit une sortie utilisable sans dépendance LLM.
