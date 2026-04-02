import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import override_settings


@override_settings(DJANGO_ENV="production")
def test_seed_prod_requires_confirmation_in_production(monkeypatch):
    called = False

    def fake_seed():
        nonlocal called
        called = True

    monkeypatch.setattr("core.management.commands.seed_prod.seed_prod", fake_seed)

    with pytest.raises(CommandError, match="--confirm-production"):
        call_command("seed_prod")

    assert called is False


@override_settings(DJANGO_ENV="production")
def test_seed_prod_runs_with_confirmation(monkeypatch):
    calls = []

    def fake_seed():
        calls.append("called")

    monkeypatch.setattr("core.management.commands.seed_prod.seed_prod", fake_seed)

    call_command("seed_prod", "--confirm-production")

    assert calls == ["called"]
