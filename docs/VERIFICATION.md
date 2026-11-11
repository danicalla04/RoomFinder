# Verification results

Verified locally on 16 October 2026 (Asia/Manila), using Windows, XAMPP MariaDB 10.4.32, Python 3.12.15, Django 4.2.30, Node 26.7.0, Vue 3 and Vite 7. Exact Python versions: backend/requirements-xampp.lock.txt. Frontend dependency versions: frontend/package-lock.json.

| Check | Result |
| --- | --- |
| XAMPP discovery / connection | C:/xampp exists; MySQL started and connected on 127.0.0.1:3306. |
| Database | roomfinder_db created with utf8mb4 / utf8mb4_unicode_ci. |
| Migrations | Applied successfully; 20 tables and 20 foreign-key relationships. |
| Migration drift | manage.py makemigrations --check --dry-run: no changes. |
| Django system check | No issues. |
| Database health | HTTP 200 through Django and Vite proxy; reports roomfinder_db and 10.4.32-MariaDB. |
| CORS | Explicit http://localhost:5173 origin accepted by Django. |
| phpMyAdmin | HTTP 200 on database structure; HTML contains hotels_hotel, rooms_room and bookings_booking. Apache was started for this check. |
| Demo data | 4 verified hotels, 8 floors, 96 rooms, stored photos, promotions and completed stays/reviews. |
| Database tests | 25 passed; latest run 35.224 seconds, separate test_roomfinder_db destroyed afterward. |
| Concurrent requests | Two separate MySQL connections racing for one room yield one confirmed booking and one conflict. |
| Vue production build | Passed; route chunks, CSS, map/chart dependencies and public assets generated in frontend/dist. |
| npm install | Successful, audit reported zero vulnerabilities. esbuild postinstall was blocked by the host policy; the build still succeeded with the installed platform binary. |
| Browser tests | Final complete run: all 3 passed in 19.9 seconds in headless Microsoft Edge. |
| Discovery browser flow | City filtering, comparison, map markers, loaded photos, desktop and 390 px mobile screenshot, no horizontal overflow or JavaScript page errors. |
| Customer browser flow | Login, exact-room selection, simulated payment confirmation, reservation history, cancellation/refund, private notifications and mark-all-read. |
| Owner/admin browser flow | Dashboard, hotel/floor/room creation, promotion creation, property and room image uploads, administrator verification, CSV download, temporary-record cleanup. |
| Windows scripts | PowerShell syntax checks passed. Full setup script completed successfully on the existing checkout without resetting demo data. Starting twice reused servers. Stop script verified to release ports 5173 and 8000. |

Screenshots are saved in ../.local/screenshots: home-desktop.png, home-mobile.png, room-selection.png, owner-dashboard.png, admin-dashboard.png. The final browser run removed its temporary properties/floors/rooms/promotions. Cancelled browser reservations remain as disclosed development history.

## Verification boundaries

The modern Django 5.2 profile was not run against a newer database, because this XAMPP server has MariaDB 10.4. Django's version check correctly rejected 5.2 on that database; no check was patched or bypassed. The compatible Django 4.2 profile is out of security support and is local-only. Upgrade MariaDB and use the maintained profile before considering an internet deployment.

No real payments, email service, cloud hosting, or push-notification transport are configured. Notifications are persisted in the application's private inbox. Nearby search is implemented and its distance calculation tested; the browser workflow uses map data and city search rather than granting physical-location permission. Map tiles require internet. Stock photos represent fictional properties.

The provided attachment referenced another master prompt that was not supplied. Verification covers the listed requirements and the precise behavior in FEATURES.md. Application preview servers were stopped after verification; start them with scripts/start.ps1. XAMPP services are managed separately.


## Login-first update - 26 October 2026

The local application now opens on role-aware login for guests. All app routes require a session, with registration available publicly. Customer, Hotel owner, and Administrator selections are checked against the stored account role by the JWT endpoint. Selecting Administrator does not grant administrator access. Sign-out returns to login, and unauthorized return paths fall back to the account's landing page.

Validation after this update: 29 database/security tests passed in 41.767 seconds; production build passed; all 9 browser workflows passed in 33.7 seconds. The browser suite covers all three successful role logins, role mismatch rejection without stored tokens, guest deep-link redirects, customer attempts to enter owner-only pages, sign-out, mobile layout, and the existing discovery/reservation/owner/admin workflows. Screenshots: .local/screenshots/login-roles-desktop.png and login-roles-mobile.png.

Current checkout: C:/Projects/app/RoomFinder. Updated frontend and backend servers were left running for user testing.


## Calapan-only update - 26 October 2026

RoomFinder now serves Calapan City, Oriental Mindoro. Customer destination is prefilled and read-only; other city tabs have been removed. Refine search supports local hotel names, streets and barangays. The map opens in Calapan. Owner/admin property forms keep the city and province fixed; reports and CSV exports identify the service area. REST input validation and a database check constraint reject a different hotel city.

Hotels migration 0002 converted only the four original fictional sample properties and preserved their IDs and relationships. Before and immediately after migration there were 96 rooms, 9 reservations and 4 reviews. The pre-change hotel/photo records and counts are backed up in .local/backups/hotels_before_calapan_20261026.json. The Escolta Rooms sample was renamed The Calapan Rooms. Seed data now creates Calapan samples directly; pins and street names are illustrative, not verified real establishments.

Validation: all 35 database/API tests passed in 49.435 seconds, the production build passed, and all 12 headless Edge workflows passed in 45.0 seconds. Tests cover fixed customer destination, removal of other city tabs, local results/maps, owner/admin read-only location fields, API rejection of outside-city creation and changes, the database constraint, and location-specific reports. Existing login, reservation, payment, cancellation, owner management and administrator verification workflows also passed. No migration drift was detected.

Screenshots: .local/screenshots/calapan-discovery-desktop.png, calapan-discovery-mobile.png, calapan-hotelowner-form.png, and calapan-administrator-form.png. Application servers were left running for user review.

Approximate city-center map reference: https://beta.cityofcalapan.gov.ph/barangays/ . Actual property coordinates and street/barangay addresses require administrator verification; this implementation does not perform surveyed-boundary geofencing.


## Room states, map and owner activity update - 26 October 2026

Implemented labeled Available, Booked, Unavailable/maintenance, Selected and guest-capacity states. Booked is based on confirmed reservations for the applied date interval; without dates the API uses today through tomorrow. Changing dates clears selection and disables the old plan until Check availability. Owner inventory now has responsive per-room actions and a Delete room action in the editor. Deletion remains protected for any reservation history; Make unavailable retains history and stops new reservations.

Seeded 36 clearly marked demo reservations, approved simulated payments and four unusable-password demo guest accounts, with 4 unused sample rooms marked unavailable. Existing records (including the user's additional room) were preserved. Backup: .local/backups/rooms_before_demo_activity_20261026.json. The seed command is idempotent, checks conflicts, and targets only the four known sample hotels. Reports and exports disclose demo rows; the owner chart includes reservation counts alongside simulated revenue.

Fixed a reporting issue revealed by the new tests: MySQL date casts required populated timezone tables and returned zero daily counts on this XAMPP installation. Reports now filter using aware Manila day boundaries, so actual persisted reservation timestamps contribute correctly without a global MySQL configuration change.

Replaced the old-looking map view with MapLibre/OpenFreeMap vector Streets and Light styles, price pins/popups, view-room links, fullscreen/zoom/fit controls and Google Maps links. Loading/failure feedback and a basic Leaflet/OpenStreetMap fallback are available. MapLibre 6's worker is explicitly bundled through Vite's ?worker&url import; the production build emits the worker asset. Actual street tiles and both styles were verified in Edge. This uses open map data; it is not the Google Maps JavaScript API.

Property stars now read '-star category' and are explained as owner-provided categories separate from guest reviews and official accreditation.

Validation: all 40 database/security tests passed in 57.585 seconds. The final production build passed with the bundled worker asset. All 16 browser workflows passed in the final complete run, including date-dependent room status/click protection, a populated owner chart, making a temporary room unavailable/available, visible deletion in the editor at 760 px width, deleting that temporary room, both vector map styles, marker popups, Google Maps links, and intentional vector-tile failure followed by the basic-map fallback. Existing role, Calapan, booking and owner/admin flows passed. No model migration is required for these read-only computed fields and UI changes.

Screenshots: .local/screenshots/room-statuses.png, active-owner-chart.png, owner-room-actions.png, modern-calapan-map.png. The app servers remain running on ports 5173 and 8000.
