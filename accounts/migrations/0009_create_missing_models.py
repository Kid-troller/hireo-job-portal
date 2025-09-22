# Generated manually to create missing models
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0008_auto_20250915_1721'),
    ]

    operations = [
        migrations.CreateModel(
            name='JobDescription',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=200)),
                ('company', models.CharField(blank=True, max_length=200)),
                ('description', models.TextField()),
                ('requirements', models.TextField(blank=True)),
                ('extracted_keywords', models.JSONField(default=list, help_text='AI-extracted keywords')),
                ('required_skills', models.JSONField(default=list, help_text='AI-extracted required skills')),
                ('preferred_skills', models.JSONField(default=list, help_text='AI-extracted preferred skills')),
                ('experience_level', models.CharField(blank=True, max_length=50)),
                ('education_requirements', models.JSONField(default=list)),
                ('keyword_count', models.IntegerField(default=0)),
                ('analysis_score', models.FloatField(default=0.0, help_text='Quality of job description analysis')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user_profile', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='job_descriptions', to='accounts.userprofile')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='ATSOptimization',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('overall_ats_score', models.IntegerField(default=0, help_text='Overall ATS score (0-100)')),
                ('keyword_match_score', models.IntegerField(default=0)),
                ('format_score', models.IntegerField(default=0)),
                ('section_score', models.IntegerField(default=0)),
                ('missing_keywords', models.TextField(blank=True)),
                ('suggestions', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('job_description', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='accounts.jobdescription')),
                ('resume', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='ats_optimization', to='accounts.resume')),
            ],
        ),
        migrations.CreateModel(
            name='ResumeVersion',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('version_name', models.CharField(max_length=200)),
                ('description', models.TextField(blank=True, help_text='What makes this version unique')),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('base_resume', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='versions', to='accounts.resume')),
                ('job_description', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='accounts.jobdescription')),
            ],
        ),
        migrations.CreateModel(
            name='CoverLetter',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(default='Cover Letter', max_length=200)),
                ('content', models.TextField()),
                ('is_template', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('job_description', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='accounts.jobdescription')),
                ('resume', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='cover_letters', to='accounts.resume')),
                ('user_profile', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='cover_letters', to='accounts.userprofile')),
            ],
        ),
        migrations.CreateModel(
            name='JobApplicationTracker',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(choices=[('applied', 'Applied'), ('reviewing', 'Under Review'), ('interview', 'Interview Scheduled'), ('offer', 'Offer Received'), ('rejected', 'Rejected'), ('withdrawn', 'Withdrawn')], default='applied', max_length=20)),
                ('application_date', models.DateTimeField(auto_now_add=True)),
                ('last_updated', models.DateTimeField(auto_now=True)),
                ('notes', models.TextField(blank=True)),
                ('cover_letter', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='accounts.coverletter')),
                ('job_description', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='accounts.jobdescription')),
                ('resume_version', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='accounts.resumeversion')),
                ('user_profile', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='job_applications', to='accounts.userprofile')),
            ],
        ),
    ]
