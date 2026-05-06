"""
LLM Writer Service for DNB Bilan Generation

Uses OpenAI (or an OpenAI-compatible gateway) to generate pedagogical
analysis with RAG context.
"""

from functools import lru_cache
from typing import Optional, Tuple, Literal

import openai
from openai import OpenAI
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

# Modèles selon criticité
MODEL_DEFAULT = getattr(settings, 'BILAN_LLM_DEFAULT', 'gpt-4o-mini')   # Bilans domaines, compétences, correcteurs
MODEL_PREMIUM = getattr(settings, 'BILAN_LLM_PREMIUM', 'gpt-4o')        # Synthèse finale direction/proviseur uniquement

SYSTEM_PROMPT = """Tu es un expert en ingénierie pédagogique et en évaluation
des apprentissages mathématiques au collège (cycle 4, classe de 3e).
Tu rédiges des bilans pédagogiques destinés exclusivement aux enseignants
et à l'équipe de direction d'un lycée.

Tes bilans sont :
- Précis et factuels : chaque affirmation s'appuie sur des données chiffrées
- Ancrés dans le programme officiel : tu cites les attendus Éduscol et les
  automatismes DNB quand ils sont fournis dans le contexte
- Opérationnels : chaque point faible identifié est suivi d'une action concrète
- Professionnels : ton style est celui d'un rapport d'inspection, sans jargon
  excessif, sans langue de bois

Tu n'inventes jamais de données. Si une information manque, tu le signales.
Tu rédiges toujours en français.

IMPORTANT (rendu front) : écris en texte brut, sans Markdown (pas de `##`, pas de `**`,
pas de tableaux Markdown, pas de blocs ```). Utilise des paragraphes et, si besoin,
des listes simples en texte."""

ProviderName = Literal["openai", "gateway"]


def _clean(s: object) -> str:
    return s.strip() if isinstance(s, str) else ""


def _looks_like_placeholder(key: str) -> bool:
    upper = key.upper()
    return (
        not key
        or "CHANGE_THIS" in upper
        or "YOUR_" in upper
        or key.startswith("__CHANGE")
    )


@lru_cache(maxsize=8)
def _make_client(api_key: str, base_url: str) -> OpenAI:
    kwargs = {"api_key": api_key}
    if base_url:
        kwargs["base_url"] = base_url
    return OpenAI(**kwargs)


def _select_client_and_model(requested_model: Optional[str]) -> Tuple[OpenAI, str, ProviderName, str]:
    """
    Pick the best available provider and the model to use.

    Priority:
    1) OpenAI (OPENAI_API_KEY) — optionally with OPENAI_BASE_URL
    2) OpenAI-compatible gateway (AI_PROVIDER_KEY + AI_PROVIDER_URL)

    Returns: (client, model_to_use, provider_name, base_url_for_logs)
    """
    gateway_key = _clean(getattr(settings, "AI_PROVIDER_KEY", ""))
    gateway_url = _clean(getattr(settings, "AI_PROVIDER_URL", ""))
    gateway_model = _clean(getattr(settings, "AI_MODEL_NAME", ""))

    requested = _clean(requested_model)

    # If caller requests a gateway-native model id (ex: Cloudflare Workers AI),
    # we MUST route through the configured gateway (OpenAI's API will reject it).
    if requested.startswith("@cf/") and gateway_key and gateway_url and not _looks_like_placeholder(gateway_key):
        model = requested
        client = _make_client(gateway_key, gateway_url)
        return client, model, "gateway", gateway_url

    openai_key = _clean(getattr(settings, "OPENAI_API_KEY", "")) or _clean(getattr(settings, "OPENAI_KEY", ""))
    openai_base_url = _clean(getattr(settings, "OPENAI_BASE_URL", ""))

    if openai_key and not _looks_like_placeholder(openai_key):
        model = requested or _clean(getattr(settings, "BILAN_LLM_DEFAULT", "")) or MODEL_DEFAULT
        client = _make_client(openai_key, openai_base_url)
        return client, model, "openai", openai_base_url

    if gateway_key and gateway_url and not _looks_like_placeholder(gateway_key):
        # If caller already requests a gateway-native model id, keep it.
        if requested.startswith("@cf/"):
            model = requested
        else:
            model = gateway_model or requested or MODEL_DEFAULT
        client = _make_client(gateway_key, gateway_url)
        return client, model, "gateway", gateway_url

    raise RuntimeError(
        "No LLM provider configured for bilan. "
        "Set OPENAI_API_KEY (optionally OPENAI_BASE_URL) or AI_PROVIDER_URL/AI_PROVIDER_KEY/AI_MODEL_NAME."
    )


def write(prompt: str, model: str = MODEL_DEFAULT,
          max_tokens: int = 1000) -> str:
    """
    Appel LLM (OpenAI ou gateway OpenAI-compatible).

    IMPORTANT: aucun fallback "démo" ne doit produire de contenu inventé pour un bilan.
    Si le LLM est indisponible, on lève une exception afin que la génération du bilan
    passe en ERROR (plutôt que d'afficher des données fausses).
    """
    client, chosen_model, provider, base_url = _select_client_and_model(model)
    logger.info(
        "bilan.llm_writer provider=%s model=%s base_url=%s",
        provider,
        chosen_model,
        base_url or "https://api.openai.com/v1",
    )

    try:
        r = client.chat.completions.create(
            model=chosen_model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.25,
            max_tokens=max_tokens,
        )
        content = r.choices[0].message.content
        if not content or not isinstance(content, str):
            raise RuntimeError("LLM response had no text content.")
        return _sanitize_for_plaintext_render(content)

    except openai.APIStatusError as e:
        req_id = getattr(e, "request_id", None)
        logger.error(
            "bilan.llm_writer APIStatusError provider=%s model=%s status=%s request_id=%s error=%s",
            provider,
            chosen_model,
            getattr(e, "status_code", None),
            req_id,
            str(e),
        )
        raise
    except openai.APIConnectionError as e:
        logger.error(
            "bilan.llm_writer APIConnectionError provider=%s model=%s error=%s",
            provider,
            chosen_model,
            str(e),
        )
        raise
    except Exception as e:
        logger.exception(
            "bilan.llm_writer unexpected error provider=%s model=%s error=%s",
            provider,
            chosen_model,
            str(e),
        )
        raise


def _sanitize_for_plaintext_render(text: str) -> str:
    """
    Frontend currently renders LLM outputs as plain text.
    Remove the most common Markdown wrappers that leak into the UI.
    """
    t = (text or "").strip()

    # Strip code fences (```lang ... ```)
    if t.startswith("```") and "```" in t[3:]:
        parts = t.split("```")
        # Typical: ["", "json\n{...}\n", ""] or ["", "...\n", ""]
        if len(parts) >= 3:
            inner = "```".join(parts[1:-1]).strip()
            lines = inner.splitlines()
            if lines and lines[0].strip().lower() in {"json", "markdown", "md", "text"}:
                inner = "\n".join(lines[1:]).strip()
            t = inner

    # Remove lightweight emphasis markers that show as raw text
    t = t.replace("**", "")
    t = t.replace("__", "")

    # Avoid heading markers leaking (keep line text)
    out_lines = []
    for line in t.splitlines():
        stripped = line.lstrip()
        if stripped.startswith("###"):
            out_lines.append(stripped.lstrip("#").strip())
            continue
        if stripped.startswith("##"):
            out_lines.append(stripped.lstrip("#").strip())
            continue
        if stripped.startswith("#"):
            out_lines.append(stripped.lstrip("#").strip())
            continue
        out_lines.append(line)

    return "\n".join(out_lines).strip()
