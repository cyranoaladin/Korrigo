from django.db import models
from django.contrib.auth.models import User

class Student(models.Model):
    """
    Modèle Élève.
    Clé primaire logique: (full_name, date_of_birth)
    Format CSV attendu: Élèves, Né(e) le, Adresse E-mail, Classe, EDS, Groupe
    """
    full_name = models.CharField(max_length=200, verbose_name="Nom et Prénom")
    date_of_birth = models.DateField(verbose_name="Date de naissance")
    email = models.EmailField(verbose_name="Adresse E-mail")
    class_name = models.CharField(max_length=50, blank=True, default="", verbose_name="Classe")
    eds_group = models.CharField(max_length=100, blank=True, default="", verbose_name="Groupe EDS")

    # Lien vers utilisateur Django pour authentification
    user = models.OneToOneField(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='student_profile',
        verbose_name="Utilisateur associé"
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
        unique_together = [['full_name', 'date_of_birth']]
        indexes = [
            models.Index(fields=['full_name']),
            models.Index(fields=['email']),
        ]
