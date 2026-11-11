from pathlib import Path
import os, re, secrets
import MySQLdb
from dotenv import load_dotenv

root = Path(__file__).resolve().parent.parent
environment_file = root / "backend" / ".env"
if not environment_file.exists():
    example = (root / "backend" / ".env.example").read_text(encoding="utf-8")
    environment_file.write_text(
        example.replace(
            "replace-with-a-random-local-secret", secrets.token_urlsafe(48)
        ),
        encoding="utf-8",
    )
    print("Created an ignored local environment file with a random secret.")
load_dotenv(environment_file)
name = os.getenv("DB_NAME", "roomfinder_db")
if not re.fullmatch(r"[A-Za-z0-9_]+", name):
    raise SystemExit("DB_NAME must contain only letters, digits, or underscores.")
connection = MySQLdb.connect(
    host=os.getenv("DB_HOST", "127.0.0.1"),
    port=int(os.getenv("DB_PORT", "3306")),
    user=os.getenv("DB_USER", "root"),
    passwd=os.getenv("DB_PASSWORD", ""),
    charset="utf8mb4",
)
with connection.cursor() as cursor:
    cursor.execute(
        f"CREATE DATABASE IF NOT EXISTS `{name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
    )
connection.close()
print(f"Database {name} is ready. Apply Django migrations next.")
