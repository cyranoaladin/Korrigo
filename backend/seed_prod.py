#!/usr/bin/env python3
"""Compatibility shim for direct seed script execution."""

import os
import sys

from core.seed_prod import seed_prod, setup_standalone_django


if __name__ == "__main__":
    env = os.environ.get("DJANGO_ENV", "development")
    if env == "production":
        print("ERROR: seed_prod.py ne doit PAS être exécuté directement en production.")
        print("Utilisez: python manage.py seed_prod --confirm-production")
        sys.exit(1)
    setup_standalone_django()
    seed_prod()
