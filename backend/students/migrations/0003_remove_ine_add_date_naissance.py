# Generated migration for Student model restructuring
# Removes INE field and adds date_naissance, groupe
# Changes unique constraint to (last_name, first_name, date_naissance)

from django.db import migrations, models
import datetime


class Migration(migrations.Migration):

    dependencies = [
        ('students', '0002_student_user'),
    ]

    operations = [
        # Step 1: Add new fields with null=True temporarily
        migrations.AddField(
            model_name='student',
            name='date_naissance',
            field=models.DateField(null=True, blank=True, verbose_name='Date de naissance'),
        ),
        migrations.AddField(
            model_name='student',
            name='groupe',
            field=models.CharField(blank=True, max_length=20, null=True, verbose_name='Groupe'),
        ),
        
        # Step 2: Remove INE field
        migrations.RemoveField(
            model_name='student',
            name='ine',
        ),
        
        # Step 3: Make date_naissance required (NOT NULL)
        # Note: This requires existing data to have date_naissance populated
        # If there's existing data, populate it first or clear the table
        migrations.AlterField(
            model_name='student',
            name='date_naissance',
            field=models.DateField(verbose_name='Date de naissance'),
        ),
        
        # Step 4: Add unique constraint on (last_name, first_name, date_naissance)
        migrations.AlterUniqueTogether(
            name='student',
            unique_together={('last_name', 'first_name', 'date_naissance')},
        ),
        
        # Step 5: Add index for performance
        migrations.AddIndex(
            model_name='student',
            index=models.Index(fields=['last_name', 'first_name', 'date_naissance'], name='students_st_last_na_idx'),
        ),
    ]
