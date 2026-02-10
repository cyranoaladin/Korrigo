from django.db import models
from django.contrib.auth.models import User

class Student(models.Model):
    first_name = models.CharField(max_length=100, verbose_name="Prénom")
    last_name = models.CharField(max_length=100, verbose_name="Nom")
    date_naissance = models.DateField(verbose_name="Date de naissance")
    email = models.EmailField(blank=True, null=True, verbose_name="Email")
    class_name = models.CharField(max_length=50, verbose_name="Classe")
    groupe = models.CharField(max_length=20, blank=True, null=True, verbose_name="Groupe")

    # Lien vers utilisateur Django pour authentification
    user = models.OneToOneField(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='student_profile',
        verbose_name="Utilisateur associé"
    )
    
    # Consentement RGPD
    privacy_charter_accepted = models.BooleanField(
        default=False,
        verbose_name="Charte de confidentialité acceptée"
    )
    privacy_charter_accepted_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Date d'acceptation de la charte"
    )

    def __str__(self):
        return f"{self.full_name} ({self.class_name})"

    @property
    def last_name(self):
        """Extrait le nom de famille (premier mot) pour compatibilité login."""
        parts = self.full_name.split(maxsplit=1)
        return parts[0] if parts else ""

    class Meta:
        verbose_name = "Élève"
        verbose_name_plural = "Élèves"
        unique_together = [['last_name', 'first_name', 'date_naissance']]
        indexes = [
            models.Index(fields=['last_name', 'first_name', 'date_naissance']),
        ]
