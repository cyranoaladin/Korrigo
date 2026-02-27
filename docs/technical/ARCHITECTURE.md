# Architecture Korrigo PMF

> **Version**: 2.1.0  
> **Date**: 14 février 2026  
> **Public**: Développeurs, Architectes, DevOps  
> **Production**: [https://korrigo.labomaths.tn](https://korrigo.labomaths.tn)

Ce document décrit l'architecture complète de la plateforme Korrigo PMF, une solution de correction numérique d'examens scannés pour établissements scolaires.

---

## 📋 Table des Matières

1. [Vue d'Ensemble](#vue-densemble)
2. [Stack Technique](#stack-technique)
3. [Architecture en Couches](#architecture-en-couches)
4. [Diagramme d'Architecture](#diagramme-darchitecture)
5. [Flux de Données](#flux-de-données)
6. [Infrastructure Docker](#infrastructure-docker)
7. [Patterns et Principes](#patterns-et-principes)
8. [Justifications Techniques](#justifications-techniques)

---

## Vue d'Ensemble

### Contexte

Korrigo PMF est une plateforme locale de correction dématérialisée pour examens internes (Bac Blanc, contrôles). Elle permet de:
- Numériser des copies d'examens scannées en masse
- Identifier les copies via OCR assisté
- Corriger numériquement avec annotations vectorielles
- Exporter les résultats vers Pronote
- Permettre aux élèves de consulter leurs copies corrigées

### Contraintes Spécifiques

- **Sans QR Code**: Identification semi-automatique (OCR + validation humaine)
- **Déploiement Local**: Serveur interne ou cloud privé (pas de SaaS)
- **Workflow Pédagogique**: Double finalité administrative (notes) et pédagogique (consultation élève)
- **Architecture Locale**: Stockage fichiers en local (NAS/Volume Docker)

---

## Stack Technique

### Backend

| Composant | Version | Rôle |
|-----------|---------|------|
| **Python** | 3.11 | Langage principal |
| **Django** | 4.2 (LTS) | Framework web, ORM, Admin |
| **Django REST Framework** | 3.16+ | API REST |
| **PostgreSQL** | 15+ | Base de données relationnelle |
| **Redis** | 7+ | Cache, broker Celery |
| **Celery** | 5+ | Traitement asynchrone |
| **PyMuPDF (fitz)** | 1.23.26 | Manipulation PDF |
| **OpenCV** | 4.8.0 | Traitement d'images |
| **pdf2image** | - | Conversion PDF → Images |
| **Gunicorn** | - | Serveur WSGI (production) |
| **Tesseract OCR** | - | OCR fallback (fra+eng) |
| **OpenAI GPT-4o-mini** | Vision | OCR principal (écriture manuscrite) |
| **Ollama** | qwen2.5:32b | LLM local pour bilans pédagogiques |
| **Pillow** | 12.1+ | Traitement images (crop header) |
| **python-magic** | 0.4.27 | Validation type MIME |
| **django-ratelimit** | 4.1.0 | Protection brute force |
| **django-csp** | 3.8 | Content Security Policy |
| **prometheus-client** | 0.19.0 | Métriques monitoring |
| **DRF Spectacular** | 0.27.1 | Documentation OpenAPI 3.0 |

### Frontend

| Composant | Version | Rôle |
|-----------|---------|------|
| **Vue.js** | 3.4+ | Framework UI (Composition API) |
| **Pinia** | 2.1+ | State management |
| **Vue Router** | 4.2+ | Routing SPA |
| **Axios** | 1.13+ | Client HTTP |
| **PDF.js** | 4.0+ | Visualisation PDF |
| **Vite** | 5.1+ | Build tool, dev server |
| **TypeScript** | 5.9+ | Typage statique |

### Infrastructure

| Composant | Version | Rôle |
|-----------|---------|------|
| **Docker** | 20+ | Conteneurisation |
| **Docker Compose** | 2+ | Orchestration locale |
| **Nginx** | 1.25+ | Reverse proxy, serving static |

---

## Architecture en Couches

```mermaid
graph TB
    subgraph "Couche Présentation"
        UI[Vue.js 3 SPA]
        Router[Vue Router]
        Store[Pinia Stores]
    end
    
    subgraph "Couche API"
        DRF[Django REST Framework]
        Auth[Session Auth]
        Perms[Permissions RBAC]
    end
    
    subgraph "Couche Logique Métier"
        ExamsSvc[Exams Service]
        GradingSvc[Grading Service]
        ProcessingSvc[Processing Service]
        StudentsSvc[Students Service]
    end
    
    subgraph "Couche Données"
        ORM[Django ORM]
        DB[(PostgreSQL)]
        Files[Media Storage]
    end
    
    subgraph "Couche Traitement Asynchrone"
        Celery[Celery Workers]
        Redis[(Redis)]
    end
    
    UI --> Router
    Router --> Store
    Store --> DRF
    DRF --> Auth
    DRF --> Perms
    DRF --> ExamsSvc
    DRF --> GradingSvc
    DRF --> ProcessingSvc
    DRF --> StudentsSvc
    
    ExamsSvc --> ORM
    GradingSvc --> ORM
    ProcessingSvc --> ORM
    StudentsSvc --> ORM
    
    ORM --> DB
    ProcessingSvc --> Files
    ProcessingSvc --> Celery
    Celery --> Redis
```

### Séparation des Responsabilités

#### 1. Couche Présentation (Frontend)
- **Responsabilité**: Interface utilisateur, interactions, routing
- **Technologies**: Vue.js 3, Pinia, Vue Router
- **Principe**: Composants réutilisables, state management centralisé

#### 2. Couche API (Backend - Interface)
- **Responsabilité**: Exposition des endpoints REST, authentification, permissions
- **Technologies**: Django REST Framework
- **Principe**: API-first, session-based auth, RBAC via `UserRole` (Admin, Teacher, Student)

#### 3. Couche Logique Métier (Backend - Services)
- **Responsabilité**: Logique applicative, règles métier, workflows
- **Technologies**: Services Python, transactions atomiques
- **Principe**: Service Layer Pattern, séparation concerns

#### 4. Couche Données (Backend - Persistance)
- **Responsabilité**: Accès données, persistance, intégrité
- **Technologies**: Django ORM, PostgreSQL
- **Principe**: Repository Pattern via ORM, migrations versionnées

#### 5. Couche Traitement Asynchrone
- **Responsabilité**: Tâches longues (rasterization, PDF generation)
- **Technologies**: Celery, Redis
- **Principe**: Fire-and-forget, retry logic

---

## Diagramme d'Architecture

### Architecture Globale

```mermaid
graph TB
    subgraph "Client Browser"
        Browser[Navigateur Web]
    end
    
    subgraph "Docker Host"
        subgraph "Frontend Container"
            Vite[Vite Dev Server<br/>Port 5173]
            VueApp[Vue.js SPA]
        end
        
        subgraph "Backend Container"
            Django[Django + DRF<br/>Port 8000]
            Gunicorn[Gunicorn WSGI]
        end
        
        subgraph "Celery Container"
            CeleryWorker[Celery Worker]
        end
        
        subgraph "Database Container"
            Postgres[(PostgreSQL<br/>Port 5432)]
        end
        
        subgraph "Cache Container"
            RedisCache[(Redis<br/>Port 6379)]
        end

        subgraph "LLM Container"
            Ollama[(Ollama<br/>Port 11434)]
        end
        
        subgraph "Volumes"
            MediaVol[Media Volume<br/>PDF, Images]
            DBVol[DB Volume<br/>PostgreSQL Data]
        end
    end
    
    Browser -->|HTTP :5173| Vite
    Vite --> VueApp
    VueApp -->|API Calls :8000| Django
    Django --> Gunicorn
    Django --> Postgres
    Django --> RedisCache
    Django --> Ollama
    Django --> MediaVol
    CeleryWorker --> Postgres
    CeleryWorker --> RedisCache
    CeleryWorker --> Ollama
    CeleryWorker --> MediaVol
    Postgres --> DBVol
```

### Architecture Modules Backend

```mermaid
graph LR
    subgraph "Backend Django"
        Core[core/<br/>Settings, URLs, WSGI]
        
        subgraph "Apps Django"
            Exams[exams/<br/>Gestion Examens]
            Grading[grading/<br/>Correction]
            Identification[identification/<br/>OCR & Identification]
            Students[students/<br/>Gestion Élèves]
        end
    end
    
    Core --> Exams
    Core --> Grading
    Core --> Identification
    Core --> Students
    
    Exams -.->|ForeignKey| Grading
    Exams -.->|ForeignKey| Students
    Identification -.->|Service| Grading
```

---

## Flux de Données

### Workflow Correction Complet

```mermaid
sequenceDiagram
    participant Admin
    participant Frontend
    participant API
    participant GradingService
    participant ProcessingService
    participant Celery
    participant DB
    participant Storage
    
    Admin->>Frontend: Upload PDF examen
    Frontend->>API: POST /api/exams/upload/
    API->>GradingService: import_pdf()
    GradingService->>DB: Create Exam
    GradingService->>Storage: Save PDF
    GradingService->>ProcessingService: rasterize_pdf()
    ProcessingService->>Storage: Generate images
    ProcessingService->>DB: Create Booklets
    GradingService->>DB: Create GradingEvent (IMPORT)
    API-->>Frontend: {exam_id, booklets}
    
    Admin->>Frontend: Identifier copie
    Frontend->>API: POST /api/exams/{id}/merge/
    API->>GradingService: merge_booklets()
    GradingService->>DB: Create Copy (STAGING)
    GradingService->>DB: Update Copy → READY
    API-->>Frontend: {copy_id}
    
    Note over Admin,Frontend: Correction par Enseignant
    
    Frontend->>API: POST /api/grading/copies/{id}/lock/
    API->>GradingService: lock_copy()
    GradingService->>DB: Create CopyLock
    GradingService->>DB: Update Copy → LOCKED
    
    Frontend->>API: POST /api/annotations/
    API->>GradingService: add_annotation()
    GradingService->>DB: Create Annotation
    GradingService->>DB: Create GradingEvent (CREATE_ANN)
    
    Frontend->>API: POST /api/grading/copies/{id}/finalize/
    API->>GradingService: finalize_copy()
    GradingService->>ProcessingService: flatten_copy()
    ProcessingService->>Storage: Generate final PDF
    GradingService->>DB: Update Copy → GRADED
    GradingService->>DB: Create GradingEvent (FINALIZE)
    API-->>Frontend: {final_pdf_url}
```

### Communication Frontend ↔ Backend

```mermaid
graph LR
    subgraph "Frontend (Vue.js)"
        Component[Vue Component]
        Store[Pinia Store]
        APIService[API Service<br/>axios]
    end
    
    subgraph "Backend (Django)"
        View[DRF ViewSet]
        Serializer[DRF Serializer]
        Service[Service Layer]
        Model[Django Model]
    end
    
    Component -->|dispatch action| Store
    Store -->|HTTP Request| APIService
    APIService -->|POST/GET/PATCH| View
    View -->|validate| Serializer
    Serializer -->|business logic| Service
    Service -->|ORM| Model
    Model -->|JSON| Serializer
    Serializer -->|Response| View
    View -->|JSON| APIService
    APIService -->|update state| Store
    Store -->|reactive| Component
```

---

## Infrastructure Docker

### Services Docker Compose

Le projet utilise plusieurs configurations Docker Compose selon l'environnement:

#### 1. `docker-compose.yml` (Développement)

```yaml
services:
  - db: PostgreSQL 15 (port 5435)
  - redis: Redis 7 (port 6385)
  - backend: Django runserver (port 8088)
  - celery: Celery worker
  - frontend: Vite dev server (port 5173)
```

**Caractéristiques**:
- Hot reload activé (volumes montés)
- DEBUG=true
- CORS permissif
- Pas de SSL

#### 2. `docker-compose.server.yml` (Production — korrigo.labomaths.tn)

Override de la configuration de base pour la production :

```yaml
services:
  backend:
    environment:
      DATABASE_URL: postgresql://...
      DJANGO_ENV: production
      DEBUG: False
      SSL_ENABLED: True
      ALLOWED_HOSTS: korrigo.labomaths.tn
      OPENAI_API_KEY: ...
      OPENAI_MODEL: gpt-4.1-mini-2025-04-14
  celery:
    environment:
      DATABASE_URL: postgresql://...
      DJANGO_ENV: production
```

**Caractéristiques** :
- DEBUG=False (vérifié au démarrage, crash si True en production)
- SSL/HSTS activé via Nginx reverse proxy
- CORS strict (origine unique)
- Session cookies Secure + HttpOnly
- JSON structured logging
- Gunicorn 3 workers, timeout 120s

### Volumes Persistants

| Volume | Montage | Contenu | Criticité |
|--------|---------|---------|-----------|
| `postgres_data` | `/var/lib/postgresql/data` | Base de données | **CRITIQUE** |
| `media_volume` | `/app/media` | PDF, images, copies | **CRITIQUE** |
| `static_volume` | `/app/staticfiles` | CSS, JS, admin | Moyen |

> [!WARNING]
> **Ne JAMAIS exécuter** `docker-compose down -v` en production ! Cela détruit les volumes et toutes les données.

---

## Patterns et Principes

### 1. Service Layer Pattern

**Principe**: Séparer la logique métier des views/controllers.

**Implémentation**:
```python
# backend/grading/services.py
class GradingService:
    @staticmethod
    @transaction.atomic
    def finalize_copy(copy: Copy, user):
        # Logique métier complexe
        # Validation, calculs, transitions d'état
        # Génération PDF, audit trail
        pass
```

**Avantages**:
- Testabilité (unit tests sans HTTP)
- Réutilisabilité (plusieurs views peuvent appeler le même service)
- Transactions atomiques centralisées

### 2. Repository Pattern (via ORM)

**Principe**: Abstraction de l'accès aux données.

**Implémentation**: Django ORM agit comme repository
```python
# Accès données via ORM (repository implicite)
copies = Copy.objects.filter(status=Copy.Status.READY)
```

### 3. State Machine Pattern

**Principe**: Gestion des transitions d'état avec validation.

**Implémentation**: Statuts Copy
```
STAGING → READY → LOCKED → GRADING_IN_PROGRESS → GRADED
                    ↑         │                         │
                    └─unlock───┘                  GRADING_FAILED
                                                       │
                                                       └─retry→ GRADING_IN_PROGRESS
```

Chaque transition est validée et auditée via `GradingEvent`. Les états `GRADING_IN_PROGRESS` et `GRADING_FAILED` gèrent la génération du PDF final avec retry automatique (max 3 tentatives).

### 4. Audit Trail Pattern

**Principe**: Traçabilité complète des actions.

**Implémentation**: Modèle `GradingEvent`
```python
GradingEvent.objects.create(
    copy=copy,
    action=GradingEvent.Action.FINALIZE,
    actor=user,
    metadata={'score': final_score}
)
```

### 5. Optimistic Locking

**Principe**: Gestion de la concurrence sans blocage DB.

**Implémentation**: `CopyLock` avec token et expiration
```python
class CopyLock(models.Model):
    copy = OneToOneField(Copy)
    owner = ForeignKey(User)
    token = UUIDField()
    expires_at = DateTimeField()
```

### 6. Normalized Coordinates

**Principe**: Coordonnées indépendantes de la résolution.

**Implémentation**: Annotations en [0, 1]
```python
class Annotation(models.Model):
    x = FloatField()  # 0.0 à 1.0
    y = FloatField()  # 0.0 à 1.0
    w = FloatField()  # 0.0 à 1.0
    h = FloatField()  # 0.0 à 1.0
```

**Avantage**: Annotations valides quelle que soit la taille d'affichage.

---

## Justifications Techniques

### Pourquoi Django ?

✅ **ORM puissant**: Gestion complexe des relations (Exam → Booklet → Copy → Annotation)  
✅ **Admin intégré**: Interface d'administration prête pour le staff  
✅ **Écosystème mature**: DRF, Celery, nombreux packages  
✅ **Sécurité**: CSRF, XSS, SQL injection protégés par défaut  
✅ **Migrations**: Gestion versionnée du schéma DB

### Pourquoi Vue.js 3 ?

✅ **Composition API**: Logique réutilisable, meilleure organisation  
✅ **Réactivité**: Mise à jour UI automatique (annotations temps réel)  
✅ **Écosystème**: Pinia (state), Vue Router (routing), Vite (build)  
✅ **Performance**: Virtual DOM, lazy loading  
✅ **TypeScript**: Typage statique pour robustesse

### Pourquoi PostgreSQL ?

✅ **ACID**: Transactions atomiques critiques (annotations + audit)  
✅ **JSON**: Support natif JSONField (grading_structure, annotations)  
✅ **Performance**: Index, requêtes complexes  
✅ **Fiabilité**: Production-ready, backup/restore robustes

### Pourquoi Celery + Redis ?

✅ **Asynchrone**: Traitement PDF long (rasterization, flattening)  
✅ **Retry**: Gestion automatique des échecs  
✅ **Scalabilité**: Ajout de workers facile  
✅ **Monitoring**: Flower pour supervision

### Pourquoi Docker ?

✅ **Reproductibilité**: Même environnement dev/prod  
✅ **Isolation**: Pas de conflits de dépendances  
✅ **Déploiement**: `docker-compose up` suffit  
✅ **Portabilité**: Fonctionne sur Linux/Mac/Windows

### Pourquoi Session-based Auth (pas JWT) ?

✅ **Sécurité**: Cookies httpOnly (pas de XSS)  
✅ **Révocation**: Déconnexion immédiate (pas de token valide après logout)  
✅ **Simplicité**: Intégré Django, pas de gestion token côté client  
✅ **CSRF**: Protection native Django

---

## Évolutions Futures

### Réalisé depuis v1.0
- [x] OCR dual : GPT-4o-mini Vision (principal) + Tesseract (fallback)
- [x] Mode INDIVIDUAL_A4 (1 PDF = 1 copie, sans split)
- [x] Banque d'annotations (templates + annotations personnelles + suggestions contextuelles)
- [x] Versionnement optimiste des annotations (champ `version`)
- [x] Gestion documentaire versionnée (sujet, corrigé, barème)
- [x] Métriques Prometheus + JSON structured logging
- [x] Rate limiting + CSP + audit trail RGPD
- [x] Health checks (liveness, readiness)

### Court Terme
- [ ] Celery pour traitement PDF volumineux (actuellement synchrone)
- [ ] Module d'export avancé (statistiques par question)
- [ ] Amélioration UI mobile (responsive)

### Moyen Terme
- [ ] Support multi-établissements
- [ ] CI/CD Pipeline (GitHub Actions)
- [ ] Tableau de bord analytics

### Long Terme
- [ ] IA de correction automatique (suggestions basées sur LLM)
- [ ] Application mobile native

---

## Références

- [DATABASE_SCHEMA.md](DATABASE_SCHEMA.md) - Schéma base de données
- [API_REFERENCE.md](API_REFERENCE.md) - Référence API REST
- [BUSINESS_WORKFLOWS.md](BUSINESS_WORKFLOWS.md) - Workflows métier
- [DEPLOYMENT_GUIDE.md](../DEPLOYMENT_GUIDE.md) - Guide déploiement
- [ADR-002: PDF Coordinate Normalization](../decisions/ADR-002-pdf-coordinate-normalization.md)
- [ADR-003: Copy Status State Machine](../decisions/ADR-003-copy-status-state-machine.md)

---

**Dernière mise à jour**: 14 février 2026  
**Auteur**: Alaeddine BEN RHOUMA  
**Licence**: Propriétaire - AEFE/Éducation Nationale
