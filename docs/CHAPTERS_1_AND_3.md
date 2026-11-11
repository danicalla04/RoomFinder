# ROOMFINDER: A CALAPAN CITY HOTEL DISCOVERY AND EXACT-ROOM RESERVATION SYSTEM

Draft Chapters 1 and 3 for a capstone manuscript. This draft describes the implementation currently in the repository. Replace institution-specific formatting, names, dates, and participant details required by the school before submission. The proposed augmented-reality navigation feature is identified separately because it has not been implemented or evaluated.

# CHAPTER 1 — THE PROBLEM AND ITS BACKGROUND

## 1.1 Introduction

Travelers choosing accommodation need dependable information about location, price, capacity, and availability. A hotel listing may show a property but leave the traveler uncertain about which physical room is available for a chosen date. Hotel personnel, meanwhile, need a consistent way to maintain room inventory, review reservations, and make property details visible only after appropriate verification. These needs are especially relevant to a location-focused booking service that must distinguish a real room from a generic room type.

RoomFinder is a web-based hotel discovery and exact-room reservation system designed for Calapan City, Oriental Mindoro. It brings customer discovery, room selection, reservation records, owner management, and administrator verification into one application. Customers can search local hotels, compare up to three properties, review photos and ratings, inspect a floor layout, and reserve a specific available room. Hotel owners maintain their property, floors, rooms, photos, promotions, and reservation information. Administrators verify submitted property details and view service-wide reports. The application currently uses simulated payment approval; it does not process real money.

The system also includes a map that shows hotel locations and supports opening a location in Google Maps. A separate, future enhancement has been proposed: an in-app augmented-reality (AR) walking guide that activates when a guest is within five kilometers of a selected hotel. That guide is outside the present implementation and must be developed and field-tested before it can be described as a working feature.

## 1.2 Background of the Study

Conventional hotel discovery and reservation workflows often split property information, availability, and booking confirmation among separate channels. This can make it difficult for a traveler to know whether a room shown on a page is truly reservable for the selected dates. A property-level listing also does not necessarily communicate the room's position on a floor or distinguish a booked room from one taken out of service by the owner. For hotel personnel, updates made outside a shared inventory can increase the risk of inconsistent availability information.

RoomFinder addresses these workflow concerns in a defined local setting. Calapan City is fixed as the service area in the customer search and hotel-management forms. The backend and database reject hotels outside that city. Search filters cover travel dates, guest count, room price, property category, guest rating, and amenities. The floor layout links each selectable position to an actual room record. Availability is checked against the requested date range, room capacity, active status, and confirmed reservations. These checks are repeated on the server when the booking is submitted, so a client-side display alone does not authorize a reservation.

The project uses three account roles. A customer may reserve, cancel within the allowed time, review a completed stay, and see private notifications. A hotel owner may maintain only the owner's properties and related inventory. An administrator may review property submissions and access Calapan-wide management information. New customer and owner registrations use email verification, and new owner accounts require administrator approval. This role structure helps separate public discovery from privileged changes to room stock and property visibility.

The initial deployment and verification are local. Sample hotels, photos, reservations, and simulated payments illustrate system behavior; they are not a claim that the sample properties are operating businesses. The present study concerns the design and functional validation of the application, rather than commercial performance or actual payment settlement.

## 1.3 Statement of the Problem

This project addresses the general problem of how to provide a single Calapan-focused application through which customers can discover hotels and reserve a specific room while hotel owners and administrators maintain trustworthy property and availability information.

Specifically, the project seeks to answer the following questions:

1. How can customers find and compare Calapan hotels using location, dates, guest capacity, price, property category, guest rating, and amenities?
2. How can the system present individual rooms on a floor layout and prevent selection of rooms that are booked, unavailable, or too small for the guest count?
3. How can the system avoid conflicting reservations when two customers request the same room for overlapping dates?
4. How can owners maintain hotel details, floors, rooms, photos, promotions, and reservation reports without modifying another owner's records?
5. How can administrators review hotel submissions and control which properties appear to customers?
6. How can the application record reservation confirmation, cancellation, reviews, notifications, and simulated payment status consistently?
7. How can the implemented workflows be checked for correctness, access control, usability at mobile screen sizes, and basic system reliability?

## 1.4 Objectives of the Study

### General Objective

To design, develop, and functionally evaluate RoomFinder as a Calapan City hotel discovery and exact-room reservation application for customers, hotel owners, and administrators.

### Specific Objectives

1. Provide a role-aware account workflow with registration, email verification, login, and access control.
2. Provide Calapan-only hotel discovery, filtering, comparison, property details, map locations, photos, and verified guest reviews.
3. Present floors and actual rooms in a visual layout with date-sensitive availability and capacity information.
4. Reserve one specific room per booking, calculate a Philippine peso total from nightly price and eligible promotion, and prevent overlapping confirmed reservations.
5. Support cancellation before check-in, maintain reservation history, and create private booking and verification notifications.
6. Provide owner tools for hotel, floor, room, image, and promotion management, together with scoped reports and CSV export.
7. Provide administrator verification and management of hotel records and Calapan-wide reports.
8. Validate the implemented application through backend/API checks, concurrent-booking tests, production frontend build checks, and browser workflows.

The proposed AR walking guide is a subsequent objective for a future version: display route arrows in an in-app camera view for a guest within five kilometers of the selected hotel's verified entrance coordinates, with map directions as the fallback. It is not counted among the implemented objectives in this manuscript draft.

## 1.5 Significance of the Study

Customers may benefit from seeing the specific rooms available for their dates and guest count before confirming a reservation. Hotel comparison, photos, local map pins, reservation history, and private notifications support a more informed booking process. The application's current approval step is simulated, so the benefit relates to workflow clarity rather than real payment completion.

Hotel owners may benefit from a centralized view of their property information, room stock, promotions, reservations, and reports. The floor layout can make room maintenance and availability decisions more concrete than a list of generic room categories.

Administrators may benefit from a defined approval process for new or changed property details and from service-wide reports. Verification status separates public listings from submissions awaiting review.

Future developers and researchers may use the application as a reference for role-based authorization, transactional room reservation, local geographic scope, and a staged path toward mobile navigation. The planned AR feature would require separate evidence about device support, route quality, positioning accuracy, and safe use before any claim of navigation effectiveness.

## 1.6 Scope and Delimitations

The application covers hotels entered for Calapan City, Oriental Mindoro. It supports customer, hotel-owner, and administrator roles; discovery and comparison; property and room photos; exact-room selection; one-room reservations for one to thirty nights; promotions; simulated payment approval; eligible cancellation; reviews after completed stays; private notifications; owner inventory and reports; and administrator verification. The map shows hotel pins using online map data. The frontend is built with Vue 3 and Vite; the backend uses Django REST Framework and a relational database. A Neon PostgreSQL development profile and a local MariaDB compatibility profile are available.

The project does not include a real payment gateway, card processing, guaranteed room fulfillment by a real hotel, or public deployment. The local sample properties and activity are illustrative. Map tiles require internet access. The application does not certify that an entered hotel coordinate is within a surveyed Calapan boundary; an administrator must verify a real address and coordinate before public use. Availability changes appear after an API refresh rather than a push subscription. Email verification requires configured SMTP credentials.

The proposed in-app AR guide, road-by-road arrows, five-kilometer activation rule, native Android package, routing-provider integration, and on-street positioning tests have not been implemented in the current system. They are described as future work, not as validated results. A straight-line arrow to a hotel would not by itself constitute safe walking directions.

## 1.7 Conceptual Framework

The study follows an input-process-output view. Inputs include registered account information, hotel details and coordinates, room and floor records, travel dates, guest count, photos, promotions, and reservation requests. Processes include validation, role checks, hotel verification, search and filtering, availability calculation, transactional booking, cancellation, and report aggregation. Outputs include verified hotel listings, room-status displays, booking confirmations, reservation and simulated-payment records, notifications, and role-specific reports.

Feedback comes from validation messages, administrator decisions, test results, and user observations. That feedback informs corrections to rules and interface behavior. The conceptual framework concerns the implemented reservation system; the proposed AR guide would add phone location, a walking route, camera positioning, and navigation feedback only after a separate development phase.

## 1.8 Definition of Terms

Exact room — an individual room record with a hotel, floor, room number, capacity, price, activity status, and layout position; it is the unit selected for a reservation.

Availability — the room's eligibility for a selected date interval after checking active status, capacity, and overlapping confirmed bookings.

Booking or reservation — a record associating one customer and one room with check-in, check-out, guest count, price, and status.

Hotel verification — administrator review of submitted or changed property details before the property becomes publicly visible.

Simulated payment — a system-generated approval or refund status used to demonstrate the reservation workflow without moving money.

Promotion — a hotel-specific percentage discount that is applied when its code and validity conditions are satisfied.

Role-based access — permissions that distinguish customer, owner, and administrator actions, including ownership checks for hotel-related records.

AR navigation — a proposed mobile feature that would overlay route guidance on a live camera view using geographic positioning. It is not part of the current implemented application.

# CHAPTER 3 — METHODOLOGY

## 3.1 Research Design

This project uses a design-and-development approach. The principal output is a working information system, and the central inquiry concerns whether its defined workflows and safeguards behave as specified. The work is organized into requirements analysis, design, implementation, and verification. Functional evidence comes from code and database inspection, automated backend and browser tests, and recorded local verification. This method supports claims about the tested application behavior; it does not by itself measure customer adoption or business impact.

The application was developed iteratively. Features such as role-aware entry, Calapan-only listings, room-state labels, and map controls were added and checked against existing workflows. When a test revealed an inconsistency, the relevant rule or interface was revised and the affected checks were run again. This iteration is appropriate because discovery, reservation, owner management, and verification depend on the same data and must remain consistent as features are added.

## 3.2 Project Locale and Intended Users

The geographic scope is Calapan City, Oriental Mindoro. Hotel addresses, barangays, and coordinates entered into the application are used for local search and map display. The application enforces the city choice in forms and backend constraints, while the accuracy of a real entrance location remains subject to administrator review.

The intended users are customers who search and reserve rooms, hotel owners who maintain their own property and room inventory, and administrators who approve property information and oversee the service. These are functional roles in the system, not a claim that a participant survey or field trial has already occurred.

## 3.3 Requirements Gathering and Analysis

Functional requirements were translated into user tasks and system rules. Customer tasks include account access, hotel search, comparison, room selection, reservation, cancellation, and review. Owner tasks include hotel and room maintenance, photo upload, promotions, and scoped reporting. Administrator tasks include verification, account and record management, and service-wide reporting. Nonfunctional considerations include access control, prevention of conflicting reservations, readable mobile layouts, clear error messages, and maintainable separation between frontend, API, and database.

The requirements were checked against the application's feature list, architecture notes, API behavior, and test cases. A requirement was treated as implemented only when an executable path existed in the application. Proposed mobile AR navigation was kept separate because credentials, native app integration, routing, and field validation are still pending.

## 3.4 Development Method

The project followed five recurring stages. During analysis, user roles, entities, validation rules, and booking constraints were identified. During design, page flows, REST resources, database relationships, and authorization boundaries were defined. During implementation, Vue pages and services were connected to Django endpoints and migrations. During verification, API tests, browser flows, and a production frontend build were run. During revision, issues revealed by checks or inspection were corrected and relevant tests repeated.

This method produces traceability from a user task to a system rule and then to a verification activity. For example, the requirement that two guests cannot confirm the same room for overlapping dates maps to a transaction that locks the room, rechecks overlap, and either inserts one booking or rejects the conflict. A concurrent-request test then exercises that rule.

## 3.5 System Architecture and Tools

The frontend uses Vue 3, Vue Router, Pinia, Axios, and Vite. Vue pages present role-specific workflows; Pinia holds the authenticated profile and comparison state; Axios sends requests to the API. Hotel maps use MapLibre with OpenFreeMap styles, with a Leaflet/OpenStreetMap fallback when WebGL or network loading fails. The frontend does not connect directly to the database.

The backend uses Django REST Framework. Its apps separate accounts, hotels, rooms, bookings, payments, promotions, reviews, notifications, and reports. Serializers validate input, permission checks enforce role and ownership, and a central reservation service applies the final booking rules. Django migrations define the relational schema. A maintained development profile uses PostgreSQL through Neon; the local XAMPP profile uses MariaDB with compatible Django dependencies. The XAMPP profile is for local coursework because its MariaDB version requires an older Django line.

Local development requires a computer with Python, Node.js and npm, a configured relational database, and a current browser. The existing PowerShell setup, start, stop, and test scripts support repeatable local work. A production mobile release would additionally require an Android development environment, a public HTTPS backend, durable media storage, and production configuration. These release prerequisites are not evidence of current deployment.

## 3.6 Data Model and Processing

The principal entities are User, Hotel, Floor, Room, Booking, Payment, Promotion, Review, and Notification, together with hotel and room photos. A user can own hotels or make bookings according to role. A hotel contains floors and rooms, while each booking identifies exactly one room. Booking and payment have a one-to-one relationship. A completed eligible booking can receive one review. Notifications belong to individual recipients.

The hotel model stores Calapan location details and coordinates. Floors and rooms store the explicit positions used by the visual layout. Database constraints protect valid values, unique room positions, and key relationships. The server calculates price and availability rather than accepting a client-supplied total or payment status. Reports are calculated from existing records instead of maintained as separate editable totals.

## 3.7 Core Workflow Procedures

Account access begins with registration or role-aware login. New accounts verify their email before sign-in, and new owner accounts wait for administrator approval. After login, routing sends customers to discovery and owners or administrators to their dashboards. Backend authorization independently checks every protected request; changing the visible role selector does not change the stored role.

Hotel publication begins when an owner submits or changes property details. The record becomes pending until an administrator verifies or rejects it. Only verified properties appear in customer discovery. An owner can manage only records under the owner's own hotel.

Reservation begins with hotel and date selection. The customer views actual rooms and their availability states. When a room is submitted, the backend checks hotel and room activity, guest capacity, a valid date interval, and price or promotion rules. It locks the room record and rechecks overlapping confirmed bookings within a transaction. A successful transaction creates a confirmed booking, an approved simulated payment record, and notifications. A conflicting request receives an error instead of a second confirmed reservation.

Cancellation is allowed before the check-in day. It changes the booking status, marks the simulated payment refunded, frees the room for later availability checks, and records notices. Completed eligible stays may be reviewed once. Owners and administrators receive their respective report projections and exports.

## 3.8 Security, Privacy, and Data Integrity Measures

The application uses token-based authentication and role checks on protected endpoints. Querysets restrict private bookings, payments, and notifications to the relevant account. Owner mutations include ownership checks even when hotel information is publicly viewable. Input serializers reject unsupported fields and invalid values, while database constraints provide a second layer for key invariants. Passwords are handled through Django's authentication system rather than stored as plain text by the application.

Uploaded images are limited to supported image formats and a maximum API upload size. Development environment files and media are excluded from version control. The local development server and debug media serving are not a production hosting design. A public deployment would require HTTPS, a strong secret, restricted hosts and origins, maintained dependencies, durable private media arrangements where appropriate, and operational monitoring. Real payment data is not collected because the application uses simulated approvals.

## 3.9 Testing and Evaluation Procedure

Verification uses several complementary checks. Backend tests validate models, serializers, permissions, role mismatch handling, search and Calapan restrictions, room capacity and availability, reservation pricing, promotion rules, cancellation, and report behavior. A concurrency test sends competing requests through separate database connections for an overlapping room and checks that only one is confirmed. Django system and migration checks inspect configuration and schema consistency.

The frontend production build checks that the Vue application and its map worker assets compile. Browser workflows in a controlled local environment exercise customer, owner, and administrator journeys, including login, search, map pins, room selection, reservation, cancellation, property management, verification, and mobile-width rendering. Screenshots and logs are retained as development evidence. These checks are a functional evaluation of the software and should be reported with the exact run date, environment, and result; an earlier result should not be presented as a new test run.

If the school requires an end-user usability study, a separate evaluation phase should recruit consenting representatives of all three roles. Participants should perform defined tasks, such as finding an available room, completing a simulated reservation, updating an owner-managed room, and verifying a property. The evaluator should record task completion, observed errors, time or assistance needed, and anonymous written feedback. The actual number of participants, recruitment method, questionnaire, and results must be inserted only after the study is conducted. No user-survey result is claimed in this draft.

## 3.10 Proposed AR Navigation Extension and Evaluation

The future Android extension would package the Vue application with Capacitor and open a native camera-based navigation screen inside RoomFinder. The selected hotel's verified entrance coordinate would be the destination. A five-kilometer straight-line distance check would determine when to offer the AR action. A walking-routing service would return a road-following path; ARCore Geospatial would estimate the phone's position and orientation so that guidance objects could be placed along suitable route points. A small map and turn instruction would remain visible in the same screen.

The AR feature would be optional. If the device lacks ARCore support, location permission, reliable positioning, route data, or sufficient visual positioning at the street, the application should show a map-based route instead. A simple bearing arrow may indicate the direction of the hotel but must not be labelled as a safe walking route. Outdoor testing would compare displayed turns and arrows against the actual walk to the hotel entrance, record positioning failures and rerouting events, and check behavior on both AR-capable and unsupported phones. None of these tests has been completed for the current system.

## 3.11 Ethical and Practical Considerations

Account and location data should be used only for the task the user requests. A future mobile guide should request camera and precise location permission at the moment the feature is opened and explain why they are needed. Location tracking should stop when navigation ends. Real hotel information and entrance coordinates should be reviewed with the property owner or responsible administrator before public display. Users should be directed to remain aware of traffic and surroundings while walking; the camera overlay is guidance rather than a guarantee that a street or path is safe or passable.

For any formal user evaluation, participation should be voluntary. Participants should know that payment is simulated, that any sample properties are fictional unless independently verified, and that their responses will be summarized without unnecessary personal identifiers. Test accounts, records, and screenshots should be handled so they do not expose credentials or private reservation details.

## 3.12 Chapter Summary

The methodology documents how RoomFinder was designed, implemented, and functionally checked as a Calapan-focused exact-room reservation system. It separates observed application behavior from proposed usability research and future AR development. This separation allows later chapters to report only evidence actually collected and gives future work a clear technical and evaluation path.
