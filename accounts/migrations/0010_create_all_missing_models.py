# Generated manually to create all missing models
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0009_create_missing_models'),
    ]

    operations = [
        migrations.CreateModel(
            name='AIBulletPoint',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('original_text', models.TextField()),
                ('enhanced_text', models.TextField()),
                ('improvement_type', models.CharField(choices=[('action_verb', 'Action Verb Enhancement'), ('quantification', 'Quantification'), ('impact', 'Impact Enhancement'), ('keyword', 'Keyword Optimization')], max_length=50)),
                ('confidence_score', models.FloatField(default=0.0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('resume', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='ai_bullet_points', to='accounts.resume')),
            ],
        ),
        migrations.CreateModel(
            name='ResumeTemplate',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('description', models.TextField(blank=True)),
                ('template_type', models.CharField(choices=[('modern', 'Modern'), ('classic', 'Classic'), ('creative', 'Creative'), ('ats_optimized', 'ATS Optimized')], max_length=50)),
                ('ats_score', models.IntegerField(default=0)),
                ('is_premium', models.BooleanField(default=False)),
                ('html_template', models.TextField()),
                ('css_styles', models.TextField(blank=True)),
                ('preview_image', models.ImageField(blank=True, null=True, upload_to='resume_templates/')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name='ResumeComparison',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('ats_score_diff', models.IntegerField(default=0, help_text='ATS score difference (B - A)')),
                ('keyword_match_diff', models.IntegerField(default=0)),
                ('content_quality_diff', models.IntegerField(default=0)),
                ('improvements_found', models.JSONField(default=list, help_text='Improvements in resume B')),
                ('regressions_found', models.JSONField(default=list, help_text='Areas where resume B is worse')),
                ('recommendations', models.JSONField(default=list, help_text='Recommendations based on comparison')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('resume_a', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='comparisons_as_a', to='accounts.resume')),
                ('resume_b', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='comparisons_as_b', to='accounts.resume')),
                ('user_profile', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='resume_comparisons', to='accounts.userprofile')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='ResumeAnalyticsReport',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('report_type', models.CharField(choices=[('weekly', 'Weekly Report'), ('monthly', 'Monthly Report'), ('custom', 'Custom Report')], max_length=50)),
                ('date_range_start', models.DateField()),
                ('date_range_end', models.DateField()),
                ('total_views', models.IntegerField(default=0)),
                ('total_downloads', models.IntegerField(default=0)),
                ('total_applications', models.IntegerField(default=0)),
                ('avg_match_score', models.FloatField(default=0.0)),
                ('top_keywords', models.JSONField(default=list)),
                ('performance_insights', models.JSONField(default=dict)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user_profile', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='analytics_reports', to='accounts.userprofile')),
            ],
        ),
    ]
