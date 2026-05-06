"""
Management command to ingest DNB pedagogical documents into RAG.
"""

import httpx
import os
from django.core.management.base import BaseCommand
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

RAG_URL = os.environ.get('RAG_URL', 'http://ingestor:8001')
RAG_TOKEN = os.environ.get('RAG_TOKEN', '')
COLLECTION = 'rag_maths_3e_dnb'

HEADERS = {"Authorization": f"Bearer {RAG_TOKEN}"}

# URLs des documents pédagogiques DNB
DOCS = [
    {
        "name": "Programme Cycle 4 - Annexe 18",
        "url": "https://eduscol.education.fr/cycle4/programme",
        "source_type": "url",
        "hints": {
            "domain": "mathematiques",
            "niveau": "3e",
            "type_ressource": "Programme officiel"
        }
    },
    {
        "name": "Attendus de fin de 3e",
        "url": "https://eduscol.education.fr/2665/attendus-de-fin-de-3e",
        "source_type": "url",
        "hints": {
            "domain": "mathematiques",
            "niveau": "3e",
            "type_ressource": "Attendus"
        }
    },
    {
        "name": "Automatismes DNB Octobre 2025",
        "url": "https://eduscol.education.fr/3896/automatismes-au-college",
        "source_type": "url",
        "hints": {
            "domain": "mathematiques",
            "niveau": "3e",
            "type_ressource": "Automatismes"
        }
    },
    {
        "name": "Structure du brevet 2026",
        "url": "https://eduscol.education.fr/1051/brevet-des-colleges",
        "source_type": "url",
        "hints": {
            "domain": "mathematiques",
            "niveau": "3e",
            "type_ressource": "Structure épreuve"
        }
    }
]

class Command(BaseCommand):
    help = "Ingère les documents pédagogiques DNB dans le RAG local"

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Forcer la réingestion même si déjà présents',
        )

    def handle(self, *args, **options):
        if not RAG_TOKEN:
            self.stdout.write(
                self.style.ERROR('RAG_TOKEN non configuré')
            )
            return

        client = httpx.Client(timeout=120.0)
        headers = {"Authorization": f"Bearer {RAG_TOKEN}"}

        self.stdout.write(
            self.style.SUCCESS(f'Début ingestion pour collection: {COLLECTION}')
        )

        total_added = 0
        total_skipped = 0

        for doc in DOCS:
            self.stdout.write(f"\nIngestion: {doc['name']}")

            payload = {
                "source_type": doc["source_type"],
                "source": doc["url"],
                "hints": doc["hints"]
            }

            try:
                r = client.post(
                    f"{RAG_URL}/ingest",
                    headers=headers,
                    json=payload,
                )

                if r.status_code == 200:
                    result = r.json()
                    added = result.get('added', 0)
                    skipped = result.get('skipped', 0)
                    
                    total_added += added
                    total_skipped += skipped
                    
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"  ✓ {doc['name']} — +{added} / -{skipped}"
                        )
                    )
                else:
                    self.stdout.write(
                        self.style.ERROR(
                            f"  ✗ {doc['name']} — {r.status_code}: {r.text[:200]}"
                        )
                    )

            except httpx.RequestError as e:
                self.stdout.write(
                    self.style.ERROR(f"  ✗ Erreur réseau: {e}")
                )

        # Vérification finale
        try:
            stats_response = client.get(
                f"{RAG_URL}/stats/{COLLECTION}",
                headers=headers
            )
            
            if stats_response.status_code == 200:
                stats = stats_response.json()
                self.stdout.write(
                    self.style.SUCCESS(
                        f"\nCollection '{COLLECTION}': {stats} documents indexés"
                    )
                )
            else:
                self.stdout.write(
                    self.style.WARNING(
                        f"\nImpossible de vérifier les stats: {stats_response.status_code}"
                    )
                )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"\nErreur vérification stats: {e}")
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"\nTerminé: {total_added} ajoutés, {total_skipped} ignorés"
            )
        )
