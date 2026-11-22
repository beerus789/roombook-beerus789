# Decisions

## Task 1: Back-to-back booking fix

- **Assumption:** booking intervals are half-open (`[start, end)`), as stated in the assignment. Two bookings may touch at an endpoint.
- Changed the shared overlap predicate from inclusive endpoints to strict comparisons and added an API regression test that creates adjacent bookings in the same room.

## Other problems noticed

- **High:** there is no authentication or authorization. Callers can read booking/user data, claim another creator ID, or create rooms.
- **High:** booking conflict checks and inserts are not protected as one transaction, so concurrent requests can double-book a room.
- **Medium:** timestamps are stored without timezone information; API clients can interpret the same values differently.
- **Medium:** `GET /bookings` is unbounded and the suggestion path will need room/attendee filters and indexes as data grows.
- **Medium:** schema changes use `create_all` rather than versioned migrations; the seed command drops all tables.
- **Low:** request limits and validation for attendee counts and normalized room names are incomplete.

## AI usage

- Codex helped inspect the starter and draft the fix and regression test. An early AI routing suggestion put the future slot suggestion endpoint under the bookings router, which would produce the wrong URL; I checked the required path and rejected that placement.

## With more time

- Continue with the assignment's separate slot API, concurrency, and UI pull requests. Add authorization, migrations, PostgreSQL integration coverage, and load tests before production.
