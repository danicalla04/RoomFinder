# RoomFinder

A hotel discovery and exact-room reservation application for Calapan City, Oriental Mindoro, built with Vue 3/Vite and Django REST Framework. It can use Neon PostgreSQL or the original local XAMPP MariaDB database. No real payment service is used.

## Deploy the API on Railway

The Android app will package the Vue frontend; Railway runs only the Django API.

1. In Railway, create a service from this GitHub repository. The repository-root Dockerfile builds the Django API automatically. If the service's **Root Directory** is set to `/backend`, the Dockerfile in that folder builds the same API.
2. In **Variables**, set `DATABASE_URL` to the Neon PostgreSQL connection URL, `SECRET_KEY` to a new random secret, and `ROOMFINDER_DEBUG=False`. Do not commit these values. For new account registration, also set `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, and `DEFAULT_FROM_EMAIL` so verification emails can be sent.
3. In **Settings > Networking**, generate a public HTTPS domain. Railway supplies `RAILWAY_PUBLIC_DOMAIN`, which Django adds to its allowed hosts automatically. If using a custom domain, set `ROOMFINDER_ALLOWED_HOSTS` to that hostname and `ROOMFINDER_CSRF_TRUSTED_ORIGINS` to its HTTPS origin.
4. Attach a Railway volume to the service at `/app/media` before uploading photos. Without the volume, uploaded hotel and room photos are lost when the service is replaced. Existing local photos are not copied to Railway automatically.
5. Open `https://YOUR-RAILWAY-DOMAIN/api/v1/health/`. A successful response reports the connected database. When building the Android frontend, set `VITE_API_BASE_URL=https://YOUR-RAILWAY-DOMAIN/api/v1/` and rebuild the Vue bundle.

If Railway reports that it detected npm and has no start command, deploy the latest commit: it contains the repository-root Dockerfile that prevents Railway from treating this project as an npm service.

## Build the Android test app

The Android package uses the existing Vue frontend through Capacitor. Ionic Vue UI components can be added later without rebuilding the screens first. The backend remains on Railway and the data remains in Neon.

Before building, open `https://YOUR-RAILWAY-DOMAIN/api/v1/health/` and check that it returns `"status": "ok"`. The Android build uses the API address in `frontend/.env.android`; update that file if the Railway domain changes. The backend permits Capacitor's Android `http://localhost` origin.

Install Android Studio and an Android SDK, then from `frontend/` run:

```powershell
npm install @capacitor/core @capacitor/android
npm install -D @capacitor/cli
npm run build:android
npx cap add android
npx cap sync android
npx cap open android
```

In Android Studio, build an APK for testing and transfer the file to the phone through a download link or cloud drive. After changing Vue code or `frontend/.env.android`, run `npm run build:android` and `npx cap sync android` before building the next APK. The APK needs internet to reach the API. New account registration also needs the Railway SMTP variables documented above.

Alternatively, open the repository's **Actions** tab on GitHub, choose **Android test APK**, and run the workflow. It checks the hosted API, builds a debug APK with Capacitor, and uploads it as the **RoomFinder-Android-debug** artifact. Download the artifact ZIP, extract `app-debug.apk`, and install it on the Android phone. The APK does not need USB debugging or the development computer to stay on, but it does need the hosted API to remain available.

## Open locally

From this workspace:

```powershell
cd RoomFinder
./scripts/start.ps1 -Environment .venv-modern # Neon
```

- Vue: http://localhost:5173
- Django: http://127.0.0.1:8000
- API: http://127.0.0.1:8000/api/v1/
- Database health: http://127.0.0.1:8000/api/v1/health/
- Neon tables: https://console.neon.tech/app/projects/billowing-violet-84534769/ (Postgres database > Tables)
- Django administration: http://127.0.0.1:8000/admin/

For the Neon configuration, `.env.local` must contain the credentials pulled by `neon deploy`. For the local MariaDB configuration, start MySQL in XAMPP and use the `.venv-xampp` environment. Stop only the app servers with `./scripts/stop.ps1`. Logs and screenshots are in `.local/`.

The website opens on the login page. Select Customer, Hotel owner, or Administrator before entering credentials. Customers continue to hotel discovery; owners and administrators continue to their dashboard. All app pages require sign-in; registration remains available.

## Development accounts

| Role | Username | Password |
| --- | --- | --- |
| Customer | traveler | RoomFinder!2026 |
| Hotel owner | hotelowner | RoomFinder!2026 |
| Administrator | administrator | RoomFinder!2026 |

These are local sample accounts. The seed command never resets existing passwords. Register new customer/owner accounts through the app. Administrator accounts are provisioned through Django administration or the management shell; public registration cannot create admins.

## Version constraint on this machine

XAMPP contains MariaDB **10.4.32**. Django 5.2 refuses that version. The verified local environment is **Python 3.12.15 + Django 4.2.30** in `.venv-xampp`, using `backend/requirements-xampp.txt`. Django 4.2 is out of security support and this profile is for local coursework only. No compatibility checks are bypassed.

For a maintained stack, upgrade MariaDB to a supported release such as 10.11, then run `./scripts/setup.ps1 -ModernDatabase` and `./scripts/start.ps1 -Environment .venv-modern`. That profile uses Django 5.2 and `backend/requirements.txt`. Existing migrations remain the source of truth. Back up your database before a database-server upgrade. The exploratory `.venv` contains the Django 5.2 tools and uv; it is not the runtime used with MariaDB 10.4.

References: https://docs.djangoproject.com/en/4.2/ref/databases/ and https://docs.djangoproject.com/en/5.2/ref/databases/ .

## Install on Windows

Prerequisites: XAMPP, a Python interpreter available as `python`, Node.js (20.19+ or 22.12+), npm, and internet access for dependency installation. Microsoft Edge is used for optional browser tests.

```powershell
cd RoomFinder
# Optional: customize credentials without committing secrets.
Copy-Item backend/.env.example backend/.env
# Set SECRET_KEY in backend/.env to a random value.
./scripts/setup.ps1
./scripts/start.ps1
```

The setup script creates an ignored environment file with a random secret if one is missing, provisions Python 3.12 with uv when needed, installs project-local Python dependencies, starts XAMPP MySQL if necessary, creates roomfinder_db, migrates, seeds, installs npm packages, and builds Vue. Supply `-XamppPath` if XAMPP is installed elsewhere. It does not replace XAMPP database binaries. If PowerShell blocks local scripts, invoke `powershell -ExecutionPolicy Bypass -File ./scripts/setup.ps1` for that process only.

On this checkout, dependencies, database, migrations, sample data, and a random ignored `backend/.env` have already been created. Do not overwrite that file just to start the app.

Manual equivalent commands after Python 3.12 is available:

```powershell
py -3.12 -m venv .venv-xampp
./.venv-xampp/Scripts/python.exe -m pip install -r backend/requirements-xampp.txt
./.venv-xampp/Scripts/python.exe scripts/initialize_database.py
cd backend
../.venv-xampp/Scripts/python.exe manage.py migrate --noinput
../.venv-xampp/Scripts/python.exe manage.py seed_demo
../.venv-xampp/Scripts/python.exe manage.py runserver 127.0.0.1:8000
# In another terminal from RoomFinder:
cd frontend
npm ci
npm run dev
```

Alternatively create the database in the XAMPP mysql client with `SOURCE` and the absolute path to `database/schema/create_database.sql`. Django migrations create application tables; do not import the schema snapshot on top of migrated tables.

## Features

Customers can register/log in, search Calapan hotels by name/street/barangay, dates, capacity, price, stars, rating and amenities, sort results, and view a modern vector map centered on Calapan City with price pins and a basic-map fallback, compare up to three stays, browse photos and verified reviews, select an exact room on a floor plan, apply a promotion, reserve with automatic simulated payment approval, download confirmation, cancel before check-in, review completed stays, edit their profile, and read private notifications.

Owners can register, create/edit Calapan properties with the city and province fixed, manage floors and room layout coordinates, change prices/capacity/active status, upload property and room images, create/edit/delete promotions, see their reservations and simulated payments, and view charts or export scoped CSV reports. New or edited property details require administrator verification.

Administrators can inspect and verify/reject Calapan hotels, receive Calapan-wide reports, manage properties, and use Django administration for account and record management. Public customers see only verified properties.

The supplied attachment references an additional master prompt that was not included. This implementation covers the feature list actually supplied; see docs/FEATURES.md for its precise behavior.

## Verification

```powershell
./scripts/test.ps1
# With both local app servers running:
./scripts/test.ps1 -Browser
```

Database tests use a separate `test_roomfinder_db` and include real concurrent connections. Browser tests use the local development database; they retain cancelled reservation history and clean up their temporary properties after a successful run. See tests/README.md and docs/VERIFICATION.md for results and boundaries.

## Project map

- `frontend/`: Vue pages, components, Pinia stores, Axios services, Vite and Tailwind, Playwright tests.
- `backend/`: Django project plus accounts, hotels, rooms, bookings, payments, promotions, reviews, notifications and reports apps.
- `api/`: REST documentation and Postman collection/environment.
- `database/`: database creation SQL, schema snapshot, sample photos and seed documentation.
- `tests/`: testing guide (executable suites are placed with their respective runtimes).
- `docs/`: architecture, feature behavior, verification, image credits.
- `scripts/`: Windows setup, start, stop and test helpers plus database initializer.

## Local configuration

`backend/.env` uses DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, DB_PORT, SECRET_KEY, and ROOMFINDER_DEBUG. The RoomFinder-specific debug name avoids the machine's unrelated DEBUG environment variable. Vite proxies `/api` and `/media` to Django, so no frontend database credentials are exposed. An optional `frontend/.env` can set VITE_API_BASE_URL for a different API origin; update Django's allowed hosts/CORS origins accordingly.

For Neon PostgreSQL, run `neon deploy` from the RoomFinder root. It pulls `DATABASE_URL` into `.env.local` (or `.env`); Django reads either file before `backend/.env`. The URL takes precedence over local MySQL settings. Run `./scripts/setup.ps1` to install the maintained Python dependencies and apply Django migrations, then `./scripts/start.ps1 -Environment .venv-modern`. Neon tables and queries are available in the project's Tables and SQL Editor pages in the Neon Console. Existing MySQL records require a separate data migration.

New customer and owner registrations send a six-digit verification code by SMTP. Enter it on `/verify-email` within 3 minutes after the email is sent; another code can be requested after 60 seconds. Five incorrect attempts require a new code. Configure `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, and `DEFAULT_FROM_EMAIL` in the ignored `backend/.env`; see `backend/.env.example`. New accounts cannot sign in until verified. Existing accounts remain active. Verified email addresses are read-only in the profile until an email-change verification flow is added.

New hotel-owner accounts require administrator approval after email verification. An administrator opens `/admin/users` to review pending owners and approve or decline them. Existing owner accounts are approved by default during migration.
New customers can sign in only after email verification, without administrator approval; new owners also need administrator approval. An unverified new account receives a verification reminder at sign-in and no access token. Older active demo accounts predate email verification and remain usable, including accounts with `roomfinder.test` addresses. The admin Users page has separate hotel owner and user sections, shows "None yet" for empty lists, and lets administrators open each owner's property, select a floor, and select a room to see its details, photos, and reservations. Reservation lists narrow to the selected floor or room and include booking and payment status. Pending owners cannot create a hotel through the API. Returning sessions display the cached account and user list while the app refreshes them from the server.

JWTs are stored in sessionStorage and refreshed once when expired. Sign out clears them. For an internet deployment use a maintained database/framework stack, HTTPS, restricted hosts, production secret management, durable private media handling as appropriate, and a production WSGI server; these development scripts bind only to loopback.


## Calapan-only service area

The destination is automatically set to **Calapan City, Oriental Mindoro** and cannot be changed. Other city tabs have been removed. Use Refine search to search a local hotel name, street, or barangay. Explore Calapan map opens the same local results on the map.

Owners and administrators use a fixed Calapan City / Oriental Mindoro property form. The REST API rejects any other city, and the database enforces a city check constraint. Administrators verify the actual local street/barangay and property coordinates; the application does not claim to validate coordinates against a surveyed city-boundary polygon.

The original four fictional demo properties were converted by hotels migration 0002, preserving IDs, all rooms, booking history and reviews. The Escolta Rooms sample is now The Calapan Rooms. Sample street names and pins are illustrative, not verified real businesses. A pre-change location snapshot is saved in .local/backups/hotels_before_calapan_20261026.json on the development machine. Fresh installations seed Calapan examples directly.


## Room states, activity, and map controls

The floor plan distinguishes Available (green), Booked (orange), Unavailable/maintenance (gray), Selected (dark green), and Too small for the guest count. Booked is calculated from confirmed reservations for the selected date range; Unavailable is an owner-controlled room setting. Without dates, room APIs show today's state. Changing dates requires Check availability before selecting a room.

Owner > Manage properties > Rooms & layout now has a responsive room list with Edit room, Make unavailable/available, and Delete room. Deletion is also in the room editor. A room with any reservation history is protected and can be made unavailable instead; its reservations are not silently cancelled.

To add/update sample activity, run the following from RoomFinder:

```powershell
./.venv-xampp/Scripts/python.exe backend/manage.py seed_demo_activity
```

This idempotent command targets only the four known demo hotels. It adds marked sample guests/reservations over the last seven days with approved simulated payments, sets several sample rooms booked today, and makes one unused sample room per hotel unavailable. Existing reservations and overlaps are respected. Newly created demo guest accounts cannot log in. `seed_demo` also runs this command for fresh setups. Owners see a demo-data notice, Demo guest labels, a reservation-count line and simulated-revenue bars; exports label demo rows.

The map uses MapLibre with OpenFreeMap vector streets and a light style, hotel price pins, room links, zoom/fullscreen/fit controls, and an Open in Google Maps link. Internet access is required for map details. Basic map uses Leaflet/OpenStreetMap and is offered automatically when WebGL is unavailable, or manually after a loading error. MapLibre is loaded only when the map is opened. This is not the Google Maps JavaScript API and does not use a Google Maps key or billing account.

Stars on property cards mean the owner-provided 1-5 category. They are separate from guest review averages and do not assert official tourism accreditation. The sample categories are demonstration data.
