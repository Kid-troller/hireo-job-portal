# Generated manually to fix JobApplicationTracker schema mismatch

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0011_fix_coverletter_schema'),
    ]

    operations = [
        # Drop and recreate the JobApplicationTracker table with correct schema
        migrations.RunSQL(
            "DROP TABLE IF EXISTS accounts_jobapplicationtracker;",
            reverse_sql="SELECT 1;"  # No reverse operation needed
        ),
        
        # Create the table with correct schema matching the model
        migrations.RunSQL(
            """
            CREATE TABLE accounts_jobapplicationtracker (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_profile_id BIGINT NOT NULL REFERENCES accounts_userprofile(id),
                job_description_id BIGINT NOT NULL REFERENCES accounts_jobdescription(id),
                resume_version_id BIGINT NULL REFERENCES accounts_resumeversion(id),
                cover_letter_id BIGINT NULL REFERENCES accounts_coverletter(id),
                company_name VARCHAR(200) NOT NULL,
                position_title VARCHAR(200) NOT NULL,
                application_url VARCHAR(200) NOT NULL DEFAULT '',
                status VARCHAR(20) NOT NULL DEFAULT 'applied',
                applied_date DATETIME NOT NULL,
                last_updated DATETIME NOT NULL,
                follow_up_date DATE NULL,
                notes TEXT NOT NULL DEFAULT '',
                resume_ats_score INTEGER NOT NULL DEFAULT 0
            );
            """,
            reverse_sql="DROP TABLE IF EXISTS accounts_jobapplicationtracker;"
        ),
        
        # Create indexes for foreign keys and performance
        migrations.RunSQL(
            """
            CREATE INDEX accounts_jobapplicationtracker_user_profile_id_idx ON accounts_jobapplicationtracker(user_profile_id);
            CREATE INDEX accounts_jobapplicationtracker_job_description_id_idx ON accounts_jobapplicationtracker(job_description_id);
            CREATE INDEX accounts_jobapplicationtracker_resume_version_id_idx ON accounts_jobapplicationtracker(resume_version_id);
            CREATE INDEX accounts_jobapplicationtracker_cover_letter_id_idx ON accounts_jobapplicationtracker(cover_letter_id);
            CREATE INDEX accounts_jobapplicationtracker_applied_date_idx ON accounts_jobapplicationtracker(applied_date);
            CREATE INDEX accounts_jobapplicationtracker_status_idx ON accounts_jobapplicationtracker(status);
            """,
            reverse_sql="SELECT 1;"
        ),
    ]
