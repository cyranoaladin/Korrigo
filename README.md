# Korrigo

**Korrigo** est une plateforme de correction numérique d'examens scannés de bout en bout. Elle permet de gérer tout le cycle de vie d'un examen dématérialisé : de l'ingestion des scans PDF à la publication des résultats pour les élèves, en passant par l'anonymisation, le dispatch intelligent, l'annotation vectorielle et la génération de bilans pédagogiques par IA.

**Production** : [https://korrigo.labomaths.tn](https://korrigo.labomaths.tn)

---

## 🏗 Architecture Technique

Le projet repose sur une architecture moderne, robuste et conteneurisée, privilégiant la sécurité et l'expérience utilisateur.

```
┌───────────────────────────────────────────────────────┐
│                 NGINX (reverse proxy)                  │
│           korrigo.labomaths.tn:443 (TLS)              │
├────────────────────┬──────────────────────────────────┤
│  Frontend (SPA)    │       Backend (API REST)          │
│  Vue 3 + Vite      │  Django 4.2 + DRF + Python 3.11  │
│  Pinia + Router    │  Gunicorn · Session Auth · CSRF   │
│  TailwindCSS 4     │  PyMuPDF · OpenCV · Tesseract     │
│  PDF.js · Lucide   │  GPT-4o-mini Vision (OCR)         │
├────────────────────┼──────────────────────────────────┤
│                    │  Celery + Beat │ Redis (broker)   │
│                    │  PostgreSQL 15  (port 5432)       │
│                    │  Ollama (LLM)   (port 11434)      │
└────────────────────┴──────────────────────────────────┘
```

### Stack Technologique

| Couche | Technologie | Version |
|--------|-------------|---------|
| **Frontend** | Vue.js 3 (Composition API) + Vite | 3.4 / 5.1 |
| **UI** | TailwindCSS + Lucide Icons | 4.x |
| **State / Routing** | Pinia + Vue Router | 2.1 / 4.2 |
| **PDF Viewer** | PDF.js | 4.0 |
| **Backend** | Django + Django REST Framework | 4.2 |
| **Runtime** | Python 3.11 + Gunicorn | |
| **Base de données** | PostgreSQL | 15 |
| **Cache / Broker** | Redis | |
| **Tâches async** | Celery + Celery Beat | |
| **OCR** | **GPT-4o-mini Vision** (Principal) + Tesseract (Fallback) | |
| **LLM (Bilans)** | **Ollama** (qwen2.5:32b / llama3.2:latest) | |
| **Vision** | OpenCV (headless) + PyMuPDF (fitz) | |
| **Monitoring** | Prometheus metrics + JSON structured logging | |
| **Container** | Docker + Docker Compose | |

---

## 🎯 Fonctionnalités Clés

### 1. Gestion des Examens & Scans
- **Modes d'upload** : `BATCH_A3` (scans en masse, split auto) et `INDIVIDUAL_A4` (1 PDF = 1 copie).
- **Import Élèves** : Liaison automatique via import CSV des listes Pronote.
- **Anonymisation** : Génération d'identifiants séquentiels sécurisés (ex: `0F8E-001`).
- **Dispatch Intelligent** : Répartition équitable des copies entre correcteurs (round-robin).

### 2. Correction & Notation
- **Annotations Vectorielles** : Coordonnées [0,1] garantissant un rendu parfait à tout zoom.
- **Édition Concurrente** : état `IN_PROGRESS`, garde serveur sur les écritures et nettoyage périodique des verrous transitoires.
- **Sauvegarde Auto (DraftState)** : Protection contre la perte de données en cas de déconnexion.
- **Barème Hiérarchique** : Structure imbriquée (Exercice > Question > Sous-question).
- **Banque d'Annotations** : Templates partagés, annotations perso et suggestions contextuelles.
- **Tampon Vrai/Faux (V/✗)** : Marquage rapide des réponses (geste papier numérisé).
- **Vue Scindée** : Barème affiché en permanence à côté de la copie PDF.
- **Déverrouillage Admin** : Déblocage forcé des copies verrouillées par l'administrateur.
- **Réouverture Copie Finalisée** : Transition `FINALIZED → READY` par admin si correction à revoir.

### 3. Intelligence Artificielle (Korrigo AI)
- **OCR Vision** : Identification automatique des élèves via lecture manuscrite par GPT-4o-mini.
- **Bilans Pédagogiques** : Génération de résumés personnalisés (tutoie l'élève, analyse les points forts/faibles) via LLM local (Ollama).
- **Aide au Dispatch** : Matching fuzzy entre OCR et liste CSV (nom, prénom, date).

### 4. Publication & Export
- **Génération PDF** : Aplatissement (flattening) des annotations pour un PDF final portable.
- **Export Pronote** : Génération de fichiers CSV prêts pour l'import de notes Pronote.
- **Portail Élève** : Espace sécurisé permettant aux élèves de consulter leur copie et leur bilan.

---

## 🗄 Modèle de Données (Résumé)

### Machine d'États des Copies

```
READY ──[1ère annotation]──→ IN_PROGRESS ──[finalize]──→ FINALIZED
  ↑                                                          │
  └──────────────────────[reopen admin]──────────────────────┘
```

### Tables Principales

| Modèle | Rôle |
|--------|------|
| `Exam` | Examen, structure de notation, mode d'upload, PDF source |
| `Copy` | Copie élève, statut, liens PDF source/final, **llm_summary** |
| `Student` | Élève, nom, email, classe, liaison compte utilisateur |
| `Annotation` | Annotation sur la copie (type, position, contenu, score_delta) |
| `Score` | Notes détaillées au format JSON selon le barème |
| `OCRResult` | Trace de l'identification automatique (confiance, texte détecté) |
| `AuditLog` | Traçabilité RGPD complète (qui a fait quoi, quand, IP, UA) |

---

## 🔌 Référence API (Extraits)

**Base URL** : `/api/` · **Swagger** : `/api/schema/swagger-ui/`

### Examens & Identification
- `POST /api/exams/upload/` : Upload de scans batch.
- `POST /api/identification/perform-ocr/{id}/` : Lancer l'OCR sur une copie.
- `POST /api/identification/identify/{id}/` : Lier manuellement un élève.

### Correction
- `POST /api/grading/copies/{id}/lock/` : Prendre le verrou sur une copie.
- `POST /api/grading/copies/{id}/finalize/` : Finaliser et générer le PDF.
- `POST /api/grading/copies/{id}/generate-summary/` : Générer le bilan LLM.

### Élèves
- `POST /api/students/login/` : Connexion au portail élève.
- `GET /api/students/my-copies/` : Liste des copies corrigées pour l'élève.

---

## 🛠 Installation & Déploiement

### Prérequis
- Docker & Docker Compose v2
- 8 GB RAM recommandé (pour Ollama/OCR)

### Développement Local

```bash
# Cloner le dépôt
git clone <repo-url> && cd korrigo

# Lancer les services (dev)
make up

# Initialiser la base et l'admin
make superuser
```

**Services** :
- Frontend : [http://localhost:5173](http://localhost:5173)
- API / Swagger : [http://localhost:8000/api/schema/swagger-ui/](http://localhost:8000/api/schema/swagger-ui/)
- Ollama : [http://localhost:11434](http://localhost:11434)

### Production

Le déploiement s'effectue via Docker Compose sur `korrigo.labomaths.tn`.
Configuration requise dans `.env` :
- `OPENAI_API_KEY` (pour l'OCR Vision)
- `OLLAMA_URL` (interne ou externe)
- `DATABASE_URL` (PostgreSQL)

### Sauvegardes de production

La production utilise un backup automatisé toutes les 30 minutes :
- dump PostgreSQL complet
- export JSON des corrections
- archive complète du volume media Docker
- envoi vers Hetzner StorageBox
- rétention distante de 24 heures
- suppression locale après synchronisation, avec au plus 2 fallbacks locaux en cas d'échec réseau

---

## 📚 Documentation Complète

Korrigo dispose d'une documentation exhaustive organisée par rôle et par thématique.

**👉 [INDEX PRINCIPAL DE LA DOCUMENTATION](docs/INDEX.md)**

| Public | Guide Recommandé |
|--------|------------------|
| 👨‍🏫 **Enseignant** | [Guide de Correction](docs/users/GUIDE_ENSEIGNANT.md) |
| 👨‍💼 **Administrateur** | [Guide Admin Système](docs/admin/GUIDE_UTILISATEUR_ADMIN.md) |
| 👔 **Secrétariat** | [Guide d'Identification](docs/users/GUIDE_SECRETARIAT.md) |
| 🎓 **Élève** | [Guide Portail Élève](docs/users/GUIDE_ETUDIANT.md) |
| 🔧 **Développeur** | [Architecture Technique](docs/technical/ARCHITECTURE.md) |
| 🔒 **Sécurité/DPO** | [Conformité RGPD](docs/security/POLITIQUE_RGPD.md) |

---

## 📜 Crédits & Licence

**Concepteur** : Alaeddine BEN RHOUMA   
**Contexte** : Nexus Réussite  
**Licence** : Propriétaire — Usage institutionnel uniquement.

---
*Dernière mise à jour : 3 avril 2026*
