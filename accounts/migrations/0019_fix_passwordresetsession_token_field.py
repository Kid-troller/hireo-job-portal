# Generated manually to fix token field mismatch in PasswordResetSession

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0018_fix_customcareerroadmap_fields'),
    ]

    operations = [
        # Drop the NOT NULL constraint on token field and make it nullable
        migrations.RunSQL(
            """
            -- Create new table with correct schema
            CREATE TABLE accounts_passwordresetsession_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES auth_user(id),
                session_token VARCHAR(100) UNIQUE,
                token VARCHAR(100),
                questions_answered_correctly INTEGER DEFAULT 0,
                is_verified BOOLEAN DEFAULT 0,
                is_used BOOLEAN DEFAULT 0,
                created_at DATETIME NOT NULL,
                expires_at DATETIME NOT NULL
            );
            
            -- Copy existing data
            INSERT INTO accounts_passwordresetsession_new 
            SELECT id, user_id, session_token, session_token as token, 
                   questions_answered_correctly, is_verified, is_used, 
                   created_at, expires_at 
            FROM accounts_passwordresetsession;
            
            -- Drop old table and rename new one
            DROP TABLE accounts_passwordresetsession;
            ALTER TABLE accounts_passwordresetsession_new RENAME TO accounts_passwordresetsession;
            """,
            reverse_sql="""
            -- Reverse: recreate original table structure
            CREATE TABLE accounts_passwordresetsession_old AS SELECT * FROM accounts_passwordresetsession;
            DROP TABLE accounts_passwordresetsession;
            CREATE TABLE accounts_passwordresetsession (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES auth_user(id),
                session_token VARCHAR(100) UNIQUE,
                questions_answered_correctly INTEGER DEFAULT 0,
                is_verified BOOLEAN DEFAULT 0,
                is_used BOOLEAN DEFAULT 0,
                created_at DATETIME NOT NULL,
                expires_at DATETIME NOT NULL
            );
            INSERT INTO accounts_passwordresetsession SELECT id, user_id, session_token, questions_answered_correctly, is_verified, is_used, created_at, expires_at FROM accounts_passwordresetsession_old;
            DROP TABLE accounts_passwordresetsession_old;
            """
        ),
    ]
