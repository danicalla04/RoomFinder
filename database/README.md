# XAMPP database

The application uses MariaDB through Django ORM, never SQLite. Start MySQL in XAMPP, then execute schema/create_database.sql with the XAMPP mysql client. Copy backend/.env.example to backend/.env to change connection credentials. The initializer creates an ignored .env with a random SECRET_KEY when needed. Defaults are root, blank password, 127.0.0.1:3306 and roomfinder_db, for local development only.

Installed XAMPP has MariaDB 10.4.32. Django 5.2 requires MariaDB 10.5+, so this machine uses Python 3.12 and requirements-xampp.txt (Django 4.2). Django 4.2 is out of support: this compatibility profile is for local coursework only. For a maintained stack, upgrade MariaDB to a supported release (10.11 LTS recommended) and use requirements.txt with Django 5.2. No database version checks are bypassed.

Run migrations from backend with ../.venv-xampp/Scripts/python.exe manage.py migrate. Tables and foreign keys are defined by the app migrations. Sample data: manage.py seed_demo. The seed command is idempotent and never overwrites existing accounts or hotel content.

phpMyAdmin is installed at C:/xampp/phpMyAdmin. To inspect tables in a browser, start Apache in XAMPP and visit http://localhost/phpmyadmin, then select roomfinder_db. Apache is optional for the application itself. Verify using SHOW TABLES and INFORMATION_SCHEMA when Apache is stopped.

Tests create and destroy only test_roomfinder_db. The configured MySQL user needs permission to create that test database. Avoid running these commands with production credentials.

The schema-only snapshot in schema/schema_snapshot.sql was exported from the migrated development database. It is a reference artifact; use migrations to install or evolve tables. Sample data and local asset provenance are documented in seed/README.md and ../docs/IMAGE_CREDITS.md.
