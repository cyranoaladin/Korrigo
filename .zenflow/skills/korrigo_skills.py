# KORRIGO CUSTOM SKILLS - SENIOR ARCHITECT LEVEL

skills = [
    {
        "name": "check_backend_health",
        "command": "docker-compose exec backend python manage.py check",
        "description": "Exécute les vérifications système de Django pour détecter les erreurs de configuration ou de modèles."
    },
    {
        "name": "run_grading_tests",
        "command": "docker-compose exec backend pytest grading/tests/",
        "description": "Lance spécifiquement les tests du moteur de correction (critique pour l'intégrité des notes)."
    },
    {
        "name": "verify_pdf_validators",
        "command": "docker-compose exec backend pytest exams/tests/test_pdf_validators.py",
        "description": "Vérifie que les 5 couches de sécurité PDF sont opérationnelles."
    },
    {
        "name": "tail_celery_logs",
        "command": "docker-compose logs --tail=50 celery",
        "description": "Vérifie si les tâches asynchrones (splitting A3/A4) rencontrent des erreurs."
    },
    {
        "name": "frontend_type_check",
        "command": "cd frontend && npm run typecheck",
        "description": "Lance la vérification TypeScript pour s'assurer que les modifications Vue.js ne cassent pas le contrat de données."
    },
    {
        "name": "db_status",
        "command": "docker-compose exec db pg_isready -U viatique_user",
        "description": "Vérifie la disponibilité de la base de données PostgreSQL."
    }
]
