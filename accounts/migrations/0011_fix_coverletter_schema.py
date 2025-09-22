# Generated manually to fix CoverLetter schema mismatch

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0010_create_all_missing_models'),
    ]

    operations = [
        # Drop and recreate the CoverLetter table with correct schema
        migrations.RunSQL(
            "DROP TABLE IF EXISTS accounts_coverletter;",
            reverse_sql="SELECT 1;"  # No reverse operation needed
        ),
        
        # Create the table with correct schema matching the model
        migrations.RunSQL(
            """
            CREATE TABLE accounts_coverletter (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_profile_id BIGINT NOT NULL REFERENCES accounts_userprofile(id),
                resume_id BIGINT NULL REFERENCES accounts_resume(id),
                job_description_id BIGINT NULL REFERENCES accounts_jobdescription(id),
                title VARCHAR(200) NOT NULL DEFAULT 'Cover Letter',
                content TEXT NOT NULL,
                ai_suggestions TEXT NOT NULL DEFAULT '[]',
                tone_analysis TEXT NOT NULL DEFAULT '{}',
                ats_score INTEGER NOT NULL DEFAULT 0,
                readability_score REAL NOT NULL DEFAULT 0.0,
                created_at DATETIME NOT NULL,
                updated_at DATETIME NOT NULL
            );
            """,
            reverse_sql="DROP TABLE IF EXISTS accounts_coverletter;"
        ),
        
        # Create indexes for foreign keys
        migrations.RunSQL(
            """
            CREATE INDEX accounts_coverletter_user_profile_id_idx ON accounts_coverletter(user_profile_id);
            CREATE INDEX accounts_coverletter_resume_id_idx ON accounts_coverletter(resume_id);
            CREATE INDEX accounts_coverletter_job_description_id_idx ON accounts_coverletter(job_description_id);
            """,
            reverse_sql="SELECT 1;"
        ),
    ]
