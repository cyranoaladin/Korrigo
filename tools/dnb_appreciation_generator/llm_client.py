"""Client minimal pour interroger Ollama via HTTP."""

import json
import urllib.request
from typing import Optional

from config import Config


class LLMError(Exception):
    """Erreur liée à l'appel LLM."""
    pass


def generate(system_prompt: str, user_prompt: str, cfg: Config = Config()) -> str:
    """Appelle Ollama et retourne le texte généré.

    Lève LLMError en cas d'échec HTTP ou de timeout.
    """
    payload = json.dumps({
        "model": cfg.model,
        "prompt": user_prompt,
        "system": system_prompt,
        "stream": False,
        "options": {
            "temperature": cfg.temperature,
            "top_p": cfg.top_p,
            "num_predict": cfg.max_tokens,
        },
    }).encode("utf-8")

    req = urllib.request.Request(
        cfg.ollama_endpoint,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=cfg.timeout_seconds) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("response", "").strip()
    except urllib.error.HTTPError as exc:
        raise LLMError(f"HTTP {exc.code}: {exc.reason}") from exc
    except urllib.error.URLError as exc:
        raise LLMError(f"URL error: {exc.reason}") from exc
    except TimeoutError as exc:
        raise LLMError("Timeout LLM") from exc
