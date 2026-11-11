# Sample data

Run the idempotent Django management command from backend:

```powershell
../.venv-xampp/Scripts/python.exe manage.py seed_demo
```

The command creates three local demo accounts, four fictional verified Calapan City properties, two floors per property, twelve rooms per floor (96 total), promotions valid for 90 days from seeding, four historical confirmed stays with simulated payments/reviews, and a welcome notification. Sample photos in database/sample_images are copied into Django's media storage and linked through real photo records. Existing accounts/passwords and hotel content are never overwritten.

Source: backend/hotels/management/commands/seed_demo.py. Tests use their own independent fixtures in a separate test database. SQL is deliberately not used to insert application records; this keeps password hashing, relationships, storage and migrations under Django control.

Property street names and coordinates are illustrative development data near Calapan city center. They do not identify actual hotels. See hotels migration 0002 for the reversible conversion of the original four sample records.
