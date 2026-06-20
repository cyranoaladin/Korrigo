"""
RAG Retriever Service for EAM BLANCHE Bilan Generation

Uses the local RAG service (rag-ui.nexusreussite.academy) to retrieve
pedagogical context for EAM BLANCHE analysis using the rag_maths_premiere collection.
"""

import httpx
import logging
from typing import Optional
from django.conf import settings

logger = logging.getLogger(__name__)

RAG_URL = getattr(settings, 'RAG_URL', 'http://ingestor:8001')
RAG_TOKEN = getattr(settings, 'RAG_TOKEN', '')
RAG_COLLECTION = 'rag_maths_premiere'


class RAGRetrieverPremiere:
    """
    Utilise UNIQUEMENT l'endpoint /search du RAG local.
    Le LLM interne du RAG (qwen2.5:1.5b) n'est PAS utilisé —
    on récupère les chunks et on les passe à GPT-4o-mini.
    """

    def __init__(self):
        self.client = httpx.Client(timeout=30.0)
        self.headers = {
            "Content-Type": "application/json",
        }
        # Ajouter l'authorization seulement si le token est disponible
        if RAG_TOKEN:
            self.headers["Authorization"] = f"Bearer {RAG_TOKEN}"

    def search(self, query: str, top_k: int = 5,
               domain_filter: Optional[str] = None) -> str:
        """
        Retourne les chunks pertinents sous forme de texte formaté
        prêt à être injecté dans un prompt LLM.
        """
        payload = {
            "q": query,
            "k": top_k,
            "collection": RAG_COLLECTION,
            "include_documents": True,
        }
        # IMPORTANT:
        # Le schéma de métadonnées de la collection RAG n'est pas garanti.
        # Un filtrage trop strict (ex: domain="Géométrie") peut éliminer tous les hits
        # si la collection indexe un domaine générique (ex: "mathematiques").
        # Pour éviter des "0 hits" systématiques, on n'applique pas de filtre par défaut.
        _ = domain_filter  # conservé pour compatibilité d'API / signature

        try:
            r = self.client.post(
                f"{RAG_URL}/search",
                headers=self.headers,
                json=payload,
            )
            r.raise_for_status()
            results = r.json()

            # Normalisation selon le format de réponse de l'API RAG
            hits = results.get("hits", [])

            if not hits:
                return "[Aucun contexte pédagogique trouvé]"

            formatted = []
            for i, hit in enumerate(hits, 1):
                # Extraire le contenu et métadonnées selon le schema réel
                content  = hit.get("document", "")
                metadata = hit.get("metadata", {})
                source   = metadata.get("drive_file_name", metadata.get("source", metadata.get("original_filename", "doc")))

                if content:
                    formatted.append(
                        f"[Réf. {i} | {source}]\n{content}"
                    )

            return "\n\n---\n\n".join(formatted)

        except httpx.HTTPError as e:
            logger.warning(f"RAG indisponible: {e}")
            return "[RAG indisponible — contexte pédagogique non chargé]"

    def search_for_domain(self, domain: str, issue: str) -> str:
        """Shortcut pour récupérer le contexte programme sur un domaine défaillant."""
        query = (
            f"attendus fin première programme officiel {domain} "
            f"automatismes remédiation {issue}"
        )
        return self.search(query, top_k=4, domain_filter=domain)

    def search_for_competence(self, competence: str) -> str:
        """Contexte sur une compétence transversale Première."""
        query = (
            f"compétence {competence} première mathématiques "
            f"évaluation attendus"
        )
        return self.search(query, top_k=3)

    def search_for_automatismes(self, domain: str) -> str:
        """Liste des automatismes pour un domaine donné."""
        query = f"automatismes première {domain}"
        return self.search(query, top_k=3)

    def search_for_remediation(self, domains: list) -> str:
        """Contexte large pour les recommandations pédagogiques."""
        domain_str = " ".join(domains)
        query = (
            f"remédiation mathématiques première conseil classe terminale "
            f"automatismes non maîtrisés {domain_str}"
        )
        return self.search(query, top_k=5)
