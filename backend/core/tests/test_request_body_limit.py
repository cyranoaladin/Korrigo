"""DRF must enforce Django's memory limit before parsing API request bodies."""

import pytest
from django.core.exceptions import RequestDataTooBig
from django.test import RequestFactory
from rest_framework.parsers import FormParser, JSONParser
from rest_framework.request import Request


@pytest.mark.parametrize(
    ("content_type", "body"),
    [
        ("application/json", b'{"value":"' + b"a" * 64 + b'"}'),
        ("application/x-www-form-urlencoded", b"value=" + b"a" * 64),
    ],
)
def test_api_parser_rejects_body_over_memory_limit(settings, content_type, body):
    settings.DATA_UPLOAD_MAX_MEMORY_SIZE = 32
    incoming = RequestFactory().generic("POST", "/body-limit", body, content_type)
    request = Request(incoming, parsers=[JSONParser(), FormParser()])

    with pytest.raises(RequestDataTooBig):
        _ = request.data


@pytest.mark.parametrize(
    ("content_type", "body"),
    [
        ("application/json", b'{"value":"ok"}'),
        ("application/x-www-form-urlencoded", b"value=ok"),
    ],
)
def test_api_parser_accepts_body_below_memory_limit(settings, content_type, body):
    settings.DATA_UPLOAD_MAX_MEMORY_SIZE = 32
    incoming = RequestFactory().generic("POST", "/body-limit", body, content_type)
    request = Request(incoming, parsers=[JSONParser(), FormParser()])

    assert request.data["value"] == "ok"
