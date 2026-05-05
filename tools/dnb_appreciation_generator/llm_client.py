"""Client pour interroger Kimi K2.6 via la passerelle Cloudflare Korrigo."""

import json
import urllib.request
import urllib.error
from typing import Optional

from config import Config


class LLMError(Exception):
    """Erreur liée à l'appel LLM."""
    pass


def generate(system_prompt: str, user_prompt: str, cfg: Config = Config()) -> str:
    """Appelle Kimi K2.6 (via Cloudflare) et retourne le texte généré.

    Lève LLMError en cas d'échec HTTP ou de timeout.
    Optimisé pour la qualité 'Opus 4.7' via le mode Thinking.
    """
    
    # Utilisation de l'URL de votre Worker Cloudflare
    # Note : On ignore cfg.ollama_endpoint pour forcer la puissance forte du Cloud
    endpoint = "https://kimi-gateway.cyranoaladin.workers.dev/v1/chat/completions"

    # Préparation du payload format OpenAI compatible avec Kimi K2.6
    payload_dict = {
        "model": "@cf/moonshotai/kimi-k2.6",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "stream": False,
        "thinking": True,  # Activation de la réflexion profonde (Strong Compute)
        "temperature": cfg.temperature,
        "max_tokens": cfg.max_tokens
    }
    
    payload = json.dumps(payload_dict).encode("utf-8")

    # Configuration de la requête avec votre clé de passerelle
    req = urllib.request.Request(
        endpoint,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer free-token-korrigo"
        },
        method="POST",
    )

    try:
        # Le mode Thinking de Kimi peut être plus long, on respecte le timeout de la config
        with urllib.request.urlopen(req, timeout=cfg.timeout_seconds) as resp:
            raw_data = resp.read().decode("utf-8")
            data = json.loads(raw_data)
            
            # Extraction selon le format de réponse de votre Worker (OpenAI Style)
            try:
                return data['choices'][0]['message']['content'].strip()
            except (KeyError, IndexError):
                raise LLMError("Format de réponse IA inattendu (manque 'choices' ou 'content')")

    except urllib.error.HTTPError as exc:
        # Tentative de lecture de l'erreur détaillée renvoyée par Cloudflare
        try:
            err_detail = exc.read().decode("utf-8")
            error_msg = json.loads(err_detail).get("error", exc.reason)
        except:
            error_msg = exc.reason
        raise LLMError(f"Erreur HTTP {exc.code}: {error_msg}") from exc
        
    except urllib.error.URLError as exc:
        raise LLMError(f"Erreur de connexion : {exc.reason}") from exc
        
    except TimeoutError as exc:
        raise LLMError("Le modèle Kimi a mis trop de temps à réfléchir (Timeout)") from exc
