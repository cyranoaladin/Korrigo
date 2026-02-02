from django.db import models
from django.contrib.auth.models import User

class Student(models.Model):
    first_name = models.CharField(max_length=100, verbose_name="Prénom")
    last_name = models.CharField(max_length=100, verbose_name="Nom")
    date_of_birth = models.DateField(null=True, blank=True, verbose_name="Date de naissance")
    email = models.EmailField(unique=True, verbose_name="Email")  # Used for login
    class_name = models.CharField(max_length=50, verbose_name="Classe")
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
        return f"{self.last_name} {self.first_name} ({self.class_name})"

    class Meta:
        verbose_name = "Élève"
        verbose_name_plural = "Élèves"
