# Implemented behavior

| Area | Behavior |
| --- | --- |
| Identity | Login-first app entry with Customer, Hotel owner and Administrator choices. The server rejects a selected role that differs from the authenticated account. Customers land on discovery; owners/admins land on dashboards; sign-out returns to login. Registration remains available without signing in. Unique email, validated password, customer/owner registration, JWT login and refresh, role read-only in profile API. |
| Verification | New or edited hotel details become pending. Administrator verifies or rejects and notifies the owner. Pending/rejected hotels are hidden from customers. |
| Discovery | Fixed Calapan City, Oriental Mindoro destination. Local hotel-name/street/barangay substring search; date range, guest count, min/max price, minimum property stars, minimum guest rating and amenities; price/rating/newest sort. |
| Location | Calapan City is fixed in customer, owner and administrator forms. API/model choices and a database check constraint reject other cities. Explore Calapan map opens local results without a geolocation prompt. The nearby API still validates caller coordinates and calculates distances, but only returns Calapan hotels. |
| Map | MapLibre/OpenFreeMap vector Streets and Light styles, local hotel price pins/popups, fit/zoom/fullscreen controls and Google Maps links. Tile loading and failure states are visible. Leaflet/OpenStreetMap is the basic fallback for unsupported WebGL or network errors. Map details require internet. |
| Comparison | Up to three hotel IDs retained locally, with current descriptions, amenities, rates and reviews fetched from the API. |
| Room selection | Floor tabs and explicit row/column positions form a cinema-style grid. Each seat is an actual database room. Booked, owner-unavailable and undersized rooms cannot be selected. Each state has a distinct label/color. Changing dates clears selection and requires an availability refresh. |
| Layout management | Owners add/edit floors and rooms. Floor+room number and floor+position are unique. Occupied layout columns cannot be removed by shrinking the floor. |
| Photos | JPEG/PNG/WebP images validated with Pillow, max 5 MB per API upload; stored through Django media. Property gallery and selected room details show uploaded images. |
| Reservation | One room per reservation, 1-30 nights, check-in today or later, check-out exclusive, positive guests within capacity. Adjacent stays are allowed. |
| Concurrency | InnoDB room-row lock and an overlap recheck inside transaction.atomic. Two simultaneous conflicting requests cannot both succeed. Hotel/room state and price are checked on the server. |
| Prices | PHP, room rate multiplied by nights, percentage promotion discount rounded to cents. No additional fees. Amounts/status supplied by a client are ignored. |
| Payment | Creating a valid reservation atomically writes a confirmed booking and approved simulated payment. No card fields, external provider, or real money. Payment records are read-only through REST. |
| Cancellation | Customer or admin can cancel before check-in day. Cancellation is idempotent, marks the simulated payment refunded, frees availability and notifies customer/owner. Owners cannot cancel guests' reservations. |
| History | Records referenced by reservations are protected from deletion. Owners use Make unavailable rather than deleting history. Delete is visible in the room editor and responsive inventory for rooms with no reservations. |
| Promotions | Hotel-specific uppercase unique codes, 1-80% discount, start/end validity and active flag. Discounts are snapshotted on the reservation. |
| Reviews | One public rating/comment per confirmed completed own reservation. Cancelled and upcoming reservations cannot be reviewed. |
| Notifications | Database-backed private inbox, mark one/all read. Confirmation, cancellation and verification create notices. |
| Owner dashboard | Own Calapan properties/rooms/reservations, confirmed simulated revenue, active room occupancy today, seven-day revenue chart, top hotels and CSV export. |
| Admin dashboard | Calapan-wide metrics, pending verification, bookings and reports. Django administration adds account/record controls. |
| Reports | Revenue is the sum of confirmed reservation totals grouped by reservation creation date; it is simulated booking revenue, not an accounting settlement or nightly earned revenue report. Occupancy is active rooms reserved today / active rooms. |

Room availability updates on API refresh, not push notifications. All date comparisons on the server use Asia/Manila. Floors use zero-based row/column coordinates; hotel floor numbers are labels. Review comments are rendered as text by Vue. Sample photos illustrate fictional properties and do not identify real bookable establishments.

Property stars are owner-provided categories, not guest scores or official accreditation. Demo reservations are persisted and clearly marked in dashboards/exports. The activity command is idempotent and preserves existing reservations.
