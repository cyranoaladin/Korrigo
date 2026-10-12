"""OCR requests remain valid when deployment model overrides are empty."""

import json
from io import BytesIO

import httpx
import pytest
from openai import OpenAI
from PIL import Image

from identification.services import OCRService


@pytest.mark.parametrize(
    ("base_url", "expected_model"),
    [
        ("https://api.openai.com/v1", "gpt-4o-mini"),
        ("https://openrouter.ai/api/v1", "openai/gpt-4o-mini"),
    ],
)
@pytest.mark.parametrize("model_override", [None, "", "   "])
def test_ocr_uses_provider_default_for_missing_or_blank_model(
    monkeypatch, base_url, expected_model, model_override
):
    if model_override is None:
        monkeypatch.delenv("OPENAI_MODEL", raising=False)
    else:
        monkeypatch.setenv("OPENAI_MODEL", model_override)

    request, result = _perform_ocr(base_url)

    assert request["model"] == expected_model
    assert result["text"] == "JEAN DUPONT"


@pytest.mark.parametrize(
    "base_url", ["https://api.openai.com/v1", "https://openrouter.ai/api/v1"]
)
def test_ocr_preserves_explicit_model(monkeypatch, base_url):
    monkeypatch.setenv("OPENAI_MODEL", "  provider/explicit-vision-model  ")

    request, result = _perform_ocr(base_url)

    assert request["model"] == "provider/explicit-vision-model"
    assert result["text"] == "JEAN DUPONT"


def _perform_ocr(base_url):
    requests = []

    def respond(request):
        requests.append(json.loads(request.content))
        return httpx.Response(
            200,
            json={
                "id": "ocr-test",
                "object": "chat.completion",
                "created": 0,
                "model": "test-model",
                "choices": [
                    {
                        "index": 0,
                        "finish_reason": "stop",
                        "message": {"role": "assistant", "content": "JEAN DUPONT"},
                    }
                ],
            },
        )

    image = BytesIO()
    Image.new("RGB", (20, 10), "white").save(image, format="JPEG")
    with OpenAI(
        api_key="test-key",
        base_url=base_url,
        http_client=httpx.Client(transport=httpx.MockTransport(respond)),
    ) as client:
        result = OCRService._ocr_with_openai(client, image)

    assert len(requests) == 1
    return requests[0], result
