# Generated manually to fix field mismatches between model and database

from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('accounts', '0017_fix_customcareerroadmap_user_field'),
    ]

    operations = [
        # Rename target_role to target_position to match model
        migrations.RenameField(
            model_name='customcareerroadmap',
            old_name='target_role',
            new_name='target_position',
        ),
        # Remove target_industry field (not in current model)
        migrations.RemoveField(
            model_name='customcareerroadmap',
            name='target_industry',
        ),
        # Remove is_public field (not in current model)
        migrations.RemoveField(
            model_name='customcareerroadmap',
            name='is_public',
        ),
        # Remove completed_at field (not in current model)
        migrations.RemoveField(
            model_name='customcareerroadmap',
            name='completed_at',
        ),
        # Add target_company field
        migrations.AddField(
            model_name='customcareerroadmap',
            name='target_company',
            field=models.CharField(blank=True, max_length=200),
        ),
        # Add target_salary field
        migrations.AddField(
            model_name='customcareerroadmap',
            name='target_salary',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True),
        ),
        # Update timeline_months to PositiveIntegerField
        migrations.AlterField(
            model_name='customcareerroadmap',
            name='timeline_months',
            field=models.PositiveIntegerField(default=12),
        ),
        # Update status choices to match model
        migrations.AlterField(
            model_name='customcareerroadmap',
            name='status',
            field=models.CharField(choices=[('active', 'Active'), ('paused', 'Paused'), ('completed', 'Completed')], default='active', max_length=20),
        ),
    ]
