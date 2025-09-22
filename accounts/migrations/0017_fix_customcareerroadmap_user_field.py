# Generated manually to fix field mismatch

from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0016_roadmapprogresslog'),
    ]

    operations = [
        # First, rename the incorrect user_profile field to user
        migrations.RenameField(
            model_name='customcareerroadmap',
            old_name='user_profile',
            new_name='user',
        ),
        # Update the foreign key to point to User model instead of UserProfile
        migrations.AlterField(
            model_name='customcareerroadmap',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='custom_roadmaps', to=settings.AUTH_USER_MODEL),
        ),
    ]
