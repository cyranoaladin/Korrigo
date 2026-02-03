from django.db import migrations, models


def migrate_to_full_name(apps, schema_editor):
    """Migrate existing first_name + last_name to full_name."""
    Student = apps.get_model('students', 'Student')
    for student in Student.objects.all():
        # Combine last_name and first_name into full_name
        student.full_name = f"{student.last_name} {student.first_name}".strip()
        student.save(update_fields=['full_name'])


def migrate_from_full_name(apps, schema_editor):
    """Reverse migration: split full_name back to first_name and last_name."""
    Student = apps.get_model('students', 'Student')
    for student in Student.objects.all():
        parts = student.full_name.split(maxsplit=1) if student.full_name else []
        student.last_name = parts[0] if parts else ""
        student.first_name = parts[1] if len(parts) > 1 else ""
        student.save(update_fields=['last_name', 'first_name'])


class Migration(migrations.Migration):

    dependencies = [
        ('students', '0004_remove_ine_add_fields'),
    ]

    operations = [
        # Step 1: Add full_name field with default empty string
        migrations.AddField(
            model_name='student',
            name='full_name',
            field=models.CharField(default='', max_length=200, verbose_name='Nom et Prénom'),
            preserve_default=False,
        ),
        
        # Step 2: Migrate data from first_name + last_name to full_name
        migrations.RunPython(migrate_to_full_name, migrate_from_full_name),
        
        # Step 3: Make date_of_birth required (remove null=True, blank=True)
        migrations.AlterField(
            model_name='student',
            name='date_of_birth',
            field=models.DateField(verbose_name='Date de naissance'),
        ),
        
        # Step 4: Remove unique constraint on email
        migrations.AlterField(
            model_name='student',
            name='email',
            field=models.EmailField(max_length=254, verbose_name='Adresse E-mail'),
        ),
        
        # Step 5: Remove first_name and last_name fields
        migrations.RemoveField(
            model_name='student',
            name='first_name',
        ),
        migrations.RemoveField(
            model_name='student',
            name='last_name',
        ),
        
        # Step 6: Add unique_together constraint and indexes
        migrations.AlterUniqueTogether(
            name='student',
            unique_together={('full_name', 'date_of_birth')},
        ),
        migrations.AddIndex(
            model_name='student',
            index=models.Index(fields=['full_name'], name='students_st_full_na_idx'),
        ),
        migrations.AddIndex(
            model_name='student',
            index=models.Index(fields=['email'], name='students_st_email_idx'),
        ),
    ]
