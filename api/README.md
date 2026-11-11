# RoomFinder REST API v1

Service area: **Calapan City, Oriental Mindoro only**. Hotel `city` defaults to `Calapan City` when omitted; another city is rejected on create or update for both owners and admins. The database also enforces this restriction. Report responses include city, province and location; CSV exports include City and Province columns. The city filter remains available for compatibility and cannot expand results outside Calapan.

Base URL: `http://127.0.0.1:8000/api/v1/`. Include trailing slashes. JSON bodies use Content-Type application/json. Uploads use multipart/form-data. Authenticated requests send `Authorization: Bearer <access>`; access tokens last 30 minutes, refresh tokens one day. Validation errors return HTTP 400; unauthorized access returns 401/403, and inaccessible records may return 404. Public endpoints support read-only anonymous access. Collections return JSON arrays.

| Endpoint | Methods | Access / fields |
| --- | --- | --- |
| health/ | GET | Public database connectivity. |
| auth/register/ | POST | Public; username, email, password, role (customer or owner), optional first_name/last_name/phone. |
| auth/token/ | POST | username/password and optional role (customer, owner, admin) -> access and refresh. When supplied, role must match the account; a mismatch returns 401 without tokens. |
| auth/token/refresh/ | POST | refresh -> access. |
| auth/me/ | GET, PUT, PATCH | Own profile. Writable email, first_name, last_name, phone; username/role read-only. |
| hotels/ | GET, POST | Public verified Calapan listings; owner/admin create. Required name, description, address, latitude, longitude; city is fixed to Calapan City; amenities array, stars 1-5. Owner assigned by server. |
| hotels/{id}/ | GET, PUT, PATCH, DELETE | Verified public read; owner/admin mutation. Saving details sets pending. Dependent reservations protect history. |
| hotels/{id}/verify/ | POST | Admin; status verified/rejected, optional note. |
| hotels/nearby/ | GET | lat, lng required; radius km 1-500, default 50; same search filters; adds distance_km. |
| floors/ | GET, POST | Public visible hotel floors; owner/admin create with hotel, number, name, columns (1-12). |
| floors/{id}/ | GET, PUT, PATCH, DELETE | Owner/admin writes. Hotel cannot change after creation. |
| rooms/ | GET, POST | Public visible rooms; owner/admin create with floor, number, price, capacity; kind, description, beds, area, row, column, active. |
| rooms/{id}/ | GET, PUT, PATCH, DELETE | Owner/admin writes; floor cannot change after creation. |
| hotel-photos/ | GET, POST | Owner/admin only; multipart hotel, image, caption. |
| room-photos/ | GET, POST | Owner/admin only; multipart room, image, caption. |
| hotel-photos/{id}/, room-photos/{id}/ | GET, PUT, PATCH, DELETE | Authorized owner/admin only. Max 5 MB per image. Public images are nested in hotel/room responses. |
| bookings/ | GET, POST | Role-scoped list. Customer create: room, check_in, check_out, guests, optional promotion_code, special_requests. Server assigns all amounts/statuses. |
| bookings/{id}/ | GET | Own customer / owning hotel owner / admin. |
| bookings/{id}/cancel/ | POST | Customer who booked or admin; only before check-in day. Idempotent, simulated refund. |
| payments/, payments/{id}/ | GET | Scoped to booking access; read-only. Created automatically with valid booking. |
| promotions/ | GET, POST | Public currently active promotions for verified hotels. Owner/admin create: hotel, code, percent, starts_on, ends_on, active. |
| promotions/{id}/ | GET, PUT, PATCH, DELETE | Owner/admin writes. Owners can also see their inactive/expired promotions. |
| reviews/ | GET, POST | Public verified-hotel reviews. Customer create: completed own booking, rating 1-5, comment (max 2000). |
| reviews/{id}/ | GET | Public verified-hotel review. |
| notifications/ | GET | Own inbox only. |
| notifications/{id}/ | PATCH | Own notification; read boolean. |
| notifications/read_all/ | POST | Mark own notifications read. |
| reports/summary/ | GET | Owner own-hotel / admin platform summary. `?format=csv` downloads scoped reservations. |

Hotel search: `search`, `city`, `check_in`, `check_out`, `guests`, `min_price`, `max_price`, `stars`, `rating`, comma-separated `amenities`, `sort=newest|price|rating`. Owners can use `mine=true`; admins can filter `status=pending|verified|rejected`. Dates must be supplied together as YYYY-MM-DD, with check_out after check_in. Date/price/capacity filters select hotels with a matching active room. `min_price` in the response is the hotel's lowest active room rate, not a final booking quote.

Room listing supports `hotel`, `floor`, `check_in`, `check_out`; each row has `available`, `availability_status` (available, booked, unavailable) and `can_delete` (true only for the manager when there is no booking history). Without dates, availability is calculated for today through tomorrow. These fields are read-only. Floor listing supports `hotel`. Promotion/review listings support `hotel`. The client compares hotels by fetching their current detail records.

Booking example:

```json
{"room": 1, "check_in": "2026-11-05", "check_out": "2026-11-07", "guests": 2, "promotion_code": "STAY10", "special_requests": "Quiet room, please."}
```

A successful 201 response includes UUID reference, computed total/discount, status confirmed, and nested payment with status approved. No payment credentials are accepted or required. Use future dates appropriate to the day you run the example. Overlap, invalid dates/capacity, unverified/inactive rooms or expired promotions return 400 without writing a partial reservation.

Import RoomFinder.postman_collection.json and Local.postman_environment.json into Postman. Select the environment, log in with the role needed for a request, and set hotel_id, floor_id, room_id, booking_id as needed. The login request stores access/refresh automatically. POST create requests store returned IDs. Set check_in/check_out to future dates before reserving.


Booking responses also include `is_demo` and `customer_display_name`. `is_demo` identifies records explicitly marked by the demo-activity command. Owner/admin summary reports include `demo_booking_count`; the CSV Data type column distinguishes Demo from Reservation. Report trend data comes from persisted bookings, not chart constants.
