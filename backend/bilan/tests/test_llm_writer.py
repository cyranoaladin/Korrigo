import pytest


class _FakeResponse:
    def __init__(self, content: str):
        class _Msg:
            def __init__(self, content: str):
                self.content = content

        class _Choice:
            def __init__(self, content: str):
                self.message = _Msg(content)

        self.choices = [_Choice(content)]


class _FakeClient:
    def __init__(self, content: str = "ok"):
        self._content = content
        self.calls = []

        class _Completions:
            def __init__(self, outer):
                self._outer = outer

            def create(self, **kwargs):
                self._outer.calls.append(kwargs)
                return _FakeResponse(self._outer._content)

        class _Chat:
            def __init__(self, outer):
                self.completions = _Completions(outer)

        self.chat = _Chat(self)


def _set_llm_settings(m, settings_obj, **kwargs):
    for k, v in kwargs.items():
        m.setattr(settings_obj, k, v, raising=False)


@pytest.mark.unit
def test_write_prefers_openai_when_openai_key_configured(monkeypatch):
    from bilan.services import llm_writer

    llm_writer._make_client.cache_clear()

    captured = {"api_key": None, "base_url": None, "client": _FakeClient("hello")}

    def _fake_make_client(api_key: str, base_url: str):
        captured["api_key"] = api_key
        captured["base_url"] = base_url
        return captured["client"]

    monkeypatch.setattr(llm_writer, "_make_client", _fake_make_client)
    _set_llm_settings(
        monkeypatch,
        llm_writer.settings,
        OPENAI_API_KEY="sk-test",
        OPENAI_BASE_URL="",
        AI_PROVIDER_KEY="free-token-korrigo",
        AI_PROVIDER_URL="https://example.invalid/v1",
        AI_MODEL_NAME="@cf/moonshotai/kimi-k2.6",
        BILAN_LLM_DEFAULT="gpt-4o-mini",
    )

    out = llm_writer.write("ping", model="gpt-4o-mini", max_tokens=10)
    assert out == "hello"
    assert captured["api_key"] == "sk-test"
    assert captured["base_url"] == ""
    assert captured["client"].calls[0]["model"] == "gpt-4o-mini"


@pytest.mark.unit
def test_write_uses_gateway_when_openai_key_missing(monkeypatch):
    from bilan.services import llm_writer

    llm_writer._make_client.cache_clear()

    captured = {"api_key": None, "base_url": None, "client": _FakeClient("hi")}

    def _fake_make_client(api_key: str, base_url: str):
        captured["api_key"] = api_key
        captured["base_url"] = base_url
        return captured["client"]

    monkeypatch.setattr(llm_writer, "_make_client", _fake_make_client)
    _set_llm_settings(
        monkeypatch,
        llm_writer.settings,
        OPENAI_API_KEY="",
        OPENAI_BASE_URL="",
        AI_PROVIDER_KEY="gateway-token",
        AI_PROVIDER_URL="https://gateway.example/v1",
        AI_MODEL_NAME="@cf/moonshotai/kimi-k2.6",
    )

    out = llm_writer.write("ping", model="gpt-4o-mini", max_tokens=10)
    assert out == "hi"
    assert captured["api_key"] == "gateway-token"
    assert captured["base_url"] == "https://gateway.example/v1"
    assert captured["client"].calls[0]["model"] == "@cf/moonshotai/kimi-k2.6"


@pytest.mark.unit
def test_write_gateway_respects_explicit_cf_model(monkeypatch):
    from bilan.services import llm_writer

    llm_writer._make_client.cache_clear()

    captured = {"client": _FakeClient("ok")}

    def _fake_make_client(api_key: str, base_url: str):
        return captured["client"]

    monkeypatch.setattr(llm_writer, "_make_client", _fake_make_client)
    _set_llm_settings(
        monkeypatch,
        llm_writer.settings,
        OPENAI_API_KEY="",
        OPENAI_BASE_URL="",
        AI_PROVIDER_KEY="gateway-token",
        AI_PROVIDER_URL="https://gateway.example/v1",
        AI_MODEL_NAME="@cf/moonshotai/kimi-k2.6",
    )

    out = llm_writer.write("ping", model="@cf/meta/llama-3.1-8b-instruct", max_tokens=10)
    assert out == "ok"
    assert captured["client"].calls[0]["model"] == "@cf/meta/llama-3.1-8b-instruct"


@pytest.mark.unit
def test_write_raises_when_no_provider_configured(monkeypatch):
    from bilan.services import llm_writer

    llm_writer._make_client.cache_clear()
    _set_llm_settings(
        monkeypatch,
        llm_writer.settings,
        OPENAI_API_KEY="",
        OPENAI_BASE_URL="",
        AI_PROVIDER_KEY="",
        AI_PROVIDER_URL="",
        AI_MODEL_NAME="",
        BILAN_ALLOW_OLLAMA_FALLBACK=False,
    )

    with pytest.raises(RuntimeError):
        llm_writer.write("ping", model="gpt-4o-mini", max_tokens=10)


@pytest.mark.unit
def test_write_can_fallback_to_ollama_when_enabled(monkeypatch):
    from bilan.services import llm_writer

    llm_writer._make_client.cache_clear()
    _set_llm_settings(
        monkeypatch,
        llm_writer.settings,
        OPENAI_API_KEY="",
        OPENAI_BASE_URL="",
        AI_PROVIDER_KEY="",
        AI_PROVIDER_URL="",
        AI_MODEL_NAME="",
        BILAN_ALLOW_OLLAMA_FALLBACK=True,
        BILAN_OLLAMA_MODEL="qwen2.5:7b",
        OLLAMA_URL="http://ollama:11434",
        OLLAMA_TIMEOUT=5,
    )

    captured = {"prompt": None, "max_tokens": None}

    def _fake_ollama(*, prompt: str, max_tokens: int) -> str:
        captured["prompt"] = prompt
        captured["max_tokens"] = max_tokens
        return "ollama_ok"

    monkeypatch.setattr(llm_writer, "_write_with_ollama", _fake_ollama)

    out = llm_writer.write("ping", model="gpt-4o-mini", max_tokens=9)
    assert out == "ollama_ok"
    assert captured["prompt"] == "ping"
    assert captured["max_tokens"] == 9
