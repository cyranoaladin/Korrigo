from django.core.management.base import BaseCommand, CommandError

from core.seed_prod import seed_prod


class Command(BaseCommand):
    help = "Create idempotent production validation data."

    def add_arguments(self, parser):
        parser.add_argument(
            "--confirm-production",
            action="store_true",
            help="Required when DJANGO_ENV=production to acknowledge production seeding.",
        )

    def handle(self, *args, **options):
        env = self._current_env()
        if env == "production" and not options["confirm_production"]:
            raise CommandError(
                "Refusing to run seed_prod in production without --confirm-production."
            )

        seed_prod()

    @staticmethod
    def _current_env():
        from django.conf import settings

        return getattr(settings, "DJANGO_ENV", None) or "development"
