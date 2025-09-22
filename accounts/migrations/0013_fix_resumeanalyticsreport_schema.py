# Generated migration to fix ResumeAnalyticsReport schema mismatch

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0012_fix_jobapplicationtracker_schema'),
    ]

    operations = [
        # Drop the existing table with incorrect schema
        migrations.RunSQL(
            "DROP TABLE IF EXISTS accounts_resumeanalyticsreport;",
            reverse_sql="SELECT 1;"  # No reverse operation needed
        ),
        
        # Recreate the table with correct schema matching the model
        migrations.CreateModel(
            name='ResumeAnalyticsReport',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('total_applications', models.IntegerField(default=0)),
                ('total_responses', models.IntegerField(default=0)),
                ('total_interviews', models.IntegerField(default=0)),
                ('best_performing_keywords', models.JSONField(default=list)),
                ('underperforming_sections', models.JSONField(default=list)),
                ('improvement_suggestions', models.JSONField(default=list)),
                ('ats_score_trend', models.JSONField(default=list, help_text='ATS scores over time')),
                ('response_rate_trend', models.JSONField(default=list, help_text='Response rates over time')),
                ('industry_benchmarks', models.JSONField(default=dict)),
                ('competitive_analysis', models.JSONField(default=dict)),
                ('generated_at', models.DateTimeField(auto_now_add=True)),
                ('user_profile', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='analytics_reports', to='accounts.userprofile')),
            ],
            options={
                'ordering': ['-generated_at'],
            },
        ),
    ]
