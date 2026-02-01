from django.db import models
from django.conf import settings

class Student(models.Model):
    # Lien vers utilisateur Django pour authentification (REQUIS)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='student_profile',
        verbose_name="Utilisateur associé"
    )

    ine = models.CharField(max_length=50, unique=True, verbose_name="Identifiant National Élève")
    first_name = models.CharField(max_length=100, verbose_name="Prénom")
    last_name = models.CharField(max_length=100, verbose_name="Nom")
    class_name = models.CharField(max_length=50, verbose_name="Classe")
    email = models.EmailField(unique=True, verbose_name="Email")
    date_of_birth = models.DateField(null=True, blank=True, verbose_name="Date de naissance")

    def __str__(self):
        return f"{self.last_name} {self.first_name} ({self.class_name})"

    class Meta:
        verbose_name = "Élève"
        verbose_name_plural = "Élèves"
