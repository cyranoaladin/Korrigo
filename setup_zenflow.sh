#!/bin/bash
set -e
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🏗️  Installation de Zenflow en MODE DIRECT pour Korrigo...${NC}"

mkdir -p .zenflow/rules .zenflow/memory .zenflow/workflows .zenflow/skills

# Config technique pour forcer le mode direct (pas de worktree)
cat > .zenflow/zenflow.config.yml << 'INNEREOF'
version: "2.0"
project_name: "Korrigo_PMF"
environment: "production-critical"
core:
  mode: "direct"
  dry_run_default: false
  backup_before_apply: true
agent:
  persona: "Senior Architect & QA Lead"
  tone: "Professional, Precise, Cautious"
  language: "fr"
safety_boundaries:
  protected_paths: ["backend/exams/migrations/*", ".env.prod"]
  forbidden_commands: ["docker-compose down -v", "rm -rf backend/media", "dropdb"]
INNEREOF

# Protocoles avec mention explicite du travail sur le dossier principal
cat > .zenflow/rules/critical_protocols.md << 'INNEREOF'
# PROTOCOLES CRITIQUES KORRIGO - TOLÉRANCE ZÉRO

## 1. Mode d'Intervention
- **DIRECT ONLY**: Interdiction formelle d'utiliser des worktrees. Toutes les corrections s'appliquent directement sur le 'File System' actuel.

## 2. Intégrité des Données
- **ACID**: Toute opération sur Copy/Annotation/Score doit être dans une transaction Django.
- **Validation PDF**: Respecter strictement validators.py (MIME, Size, Integrity).

## 3. Standards de Code
- **Backend**: Typage strict (Type hints) et logique métier uniquement dans services/.
- **Frontend**: Vue 3 Composition API et Pinia obligatoire.
INNEREOF

# Mapping du contexte pour une efficacité ciblée
cat > .zenflow/memory/context_map.json << 'INNEREOF'
{
  "docs_mapping": {
    "architecture": "docs/ARCHITECTURE.md",
    "db_schema": "docs/DATABASE_SCHEMA.md",
    "security": "docs/ADVANCED_PDF_VALIDATORS.md"
  },
  "critical_modules": {
    "grading_engine": "backend/grading/services.py",
    "validators": "backend/exams/validators.py"
  }
}
INNEREOF

# Workflows et Skills
cat > .zenflow/workflows/dev_cycle.yml << 'INNEREOF'
workflows:
  feature_development:
    steps: ["analysis", "spec_check", "direct_implementation", "testing"]
INNEREOF

echo -e "${GREEN}✅ Zenflow configuré à la racine de $(pwd)${NC}"
echo "Mode: DIRECT (Working tree désactivé)."
