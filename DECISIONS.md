# Decisions

## Assumptions and trade-offs

- Naive API timestamps are office-local IST; timezone-aware timestamps are converted to IST before storing in the starter's naive `DateTime` columns. Responses include `+05:30`.
- Weekends have no valid slots. Lunch overlap is allowed only when the meeting duration is 30 minutes or less, including meetings that cross into or out of lunch.
- The requester is considered a participant even if omitted from `attendee_ids`. The booking creator is also checked for conflicts. As a product-level extension beyond the assignment, distinct creator-plus-attendee count cannot exceed room capacity; the creator counts as one participant.
- A meeting longer than 60 minutes occupies the room through its 15-minute cleaning buffer. The buffer blocks following meetings but does not extend participant conflicts.
- Booking writes serialize on the room row in PostgreSQL and also lock participant rows in stable ID order. SQLite uses `BEGIN IMMEDIATE` before checking availability. SQLite serializes all writers, so it is suitable for local/small deployments, not high write throughput. PostgreSQL locking assumes all writers use this API; direct database writes can bypass application checks.
- Scheduling rules live in a shared module so suggestions and booking creation enforce the same constraints. The app remains a single deployable service; no cache or Celery is needed for this synchronous workload.

## Other issues found

- **High:** There is no authentication or authorization; user IDs and room creation are publicly writable.
- **Medium:** The seed command drops and recreates all tables, so it must only be used with disposable data.
- **Medium:** The timestamp schema remains timezone-naive. The API consistently interprets it as IST, but changing to UTC/timestamptz requires a migration and a conversion policy for existing rows.
- **Medium:** PostgreSQL concurrency has not been exercised in CI; the row-lock strategy is verified only with SQLite's file-backed concurrency test.
- **Low:** Tables and new indexes are created with `create_all` at startup rather than through versioned migrations.

## With more time

- Add authentication, authorization, and idempotency for booking creation.
- Add Alembic migrations and a PostgreSQL integration test that exercises simultaneous requests from separate connections.
- Add PostgreSQL integration and load tests, plus stronger keyboard/screen-reader review.

## AI usage

- Codex was used to inspect the assignment and starter, implement scheduling/API/UI changes, and draft tests and this note.
- An early implementation draft put the suggestion route under the bookings router, which would have exposed `/bookings/rooms/{id}/suggest`. I caught this by checking the router prefix and moved the endpoint into the rooms router so the required URL is `/rooms/{id}/suggest`.
