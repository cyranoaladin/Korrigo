from django.db import models

class Student(models.Model):
    ine = models.CharField(max_length=50, unique=True, verbose_name="Identifiant National Élève")
    first_name = models.CharField(max_length=100, verbose_name="Prénom")
    last_name = models.CharField(max_length=100, verbose_name="Nom")
    class_name = models.CharField(max_length=50, verbose_name="Classe")
    email = models.EmailField(blank=True, null=True, verbose_name="Email")

    def __str__(self):
        return f"{self.last_name} {self.first_name} ({self.class_name})"

    class Meta:
        verbose_name = "Élève"
        verbose_name_plural = "Élèves"
