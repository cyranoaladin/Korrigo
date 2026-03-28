from django.apps import AppConfig


class ExamsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'exams'

    def ready(self):
        import exams.signals  # noqa
        from exams.models import Exam
        from django.db.models.signals import m2m_changed
        from exams.signals import auto_dispatch_copies
        m2m_changed.connect(auto_dispatch_copies, sender=Exam.correctors.through)
