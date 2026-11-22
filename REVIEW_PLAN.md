# Production Readiness Review and Remediation Plan

## Follow-up Status

- **Addressed in the follow-up:** GET latency now defaults to zero; CORS origins are configurable; health/readiness checks test the database; booking reads are bounded and paginated; availability queries now filter by the requested room and selected people; attendee inputs are capped; room names are trimmed and case-insensitive duplicates rejected; room capacity is enforced using the unique creator-plus-attendee count; and the UI now covers every supported duration and cancels stale reads.
- **Still required before production:** authentication/authorization and identity-bound creator IDs; versioned schema migrations and a UTC storage migration; PostgreSQL integration/concurrency coverage; request rate controls at the edge; and a load test against the intended production database and deployment.
- **Regression coverage added:** 34 backend tests and 3 frontend component tests pass, covering scheduling boundaries, API validation, capacity, pagination, conflict refresh, booking flow, and stale booking-list responses. These are not a substitute for PostgreSQL integration tests or load tests.
- **UI direction:** the interface was rebuilt as a restrained workplace scheduling workspace with an editorial heading, dark pine booking rail, warm paper schedule, compact room directory, and responsive stacking. Browser review covered desktop and mobile widths, slot suggestions, and one-click booking; no browser console errors were observed. Conflict refresh feedback is now visible alongside refreshed slots.

## Review Snapshot

- Current checks: backend `pytest -q` passes (34 tests); frontend `npm test` passes (3 tests); `npm run build` succeeds; `npm audit` reports zero known vulnerabilities.
- Adversarial concurrency probes: two simultaneous requests for the same room return one `201` and one `409`; two requests for different rooms but the same attendee also return one `201` and one `409` on SQLite.
- A direct scheduling benchmark scanning 20,000 unrelated bookings took about 0.076 seconds in this environment. This excludes database fetch, ORM hydration, network latency, and concurrent load, so it is not a production capacity claim.
- The original development latency middleware was measured at 64–796 ms per GET (mean 407 ms across eight health requests) with its former 800 ms default. It now defaults to zero and remains configurable for local simulation.
- A six-person booking was accepted for a four-seat room (`201`). This is a confirmed product-rule gap, though capacity enforcement is not explicit in the assignment.

## Findings and Priority

### P0 — Protect user and booking operations

- There is no authentication or authorization. Callers can read user/booking data, claim any `creator_id`, book on behalf of another user, and create rooms. Add identity-based authorization before production exposure.

### P1 — Correctness and operational behavior

- `SIMULATED_LATENCY_MS` defaults to 800 and applies to every GET, including health checks. Default it to zero outside local development and enable simulation only through an explicit development setting.
- Room capacity is displayed and stored but not enforced. Define whether creator counts toward capacity, then reject over-capacity bookings and omit such rooms from suggestions. Current probe: 6 participants were accepted in a 4-seat room.
- `/bookings` can return the entire history when no date is supplied. Suggestions load every booking for a day across every room, then scan bookings in Python for each candidate slot. Add pagination and filter/shape availability queries in the database, with indexes for room/time and attendee/time lookups.
- The database stores naive local timestamps. API inputs now normalize to IST, but this is fragile for integrations, historical data, and future timezone changes. Migrate to an explicit UTC/timestamptz representation with a documented conversion for existing seed/data.
- PostgreSQL concurrency logic is not covered by an integration test, and database writes outside this API can bypass its row-lock convention. Add a PostgreSQL concurrency test and decide whether a database-level overlap constraint is required.
- Startup calls `create_all`, so schema evolution has no version history; the seed command drops all tables. Add migrations and make destructive reset behavior explicit and environment guarded.
- `/health` always says `ok` without checking database readiness. Split liveness from readiness and check database connectivity for readiness.
- CORS is fixed to `http://localhost:5173`. Move allowed origins to deployment configuration and reject wildcard production policies.

### P2 — Input limits, frontend correctness, and regression coverage

- `attendee_ids` has no list-size bound and room capacity is not used to limit the request. Add request size/list limits and reject duplicate or excessive attendees with a clear `422`.
- `BookingList` does not cancel or sequence requests. With delayed/reordered responses, a slow response for an old date can overwrite the bookings for the newly selected date. Abort the prior request or ignore stale response generations.
- `SlotFinder` also returns a successful refresh result to its caller even when its request became stale. A user can change date/room while a `409` refresh is in flight and see a “times refreshed” message although those results were discarded. Only report refresh success when the active query generation applied the results.
- The date input can be cleared; this sends an empty date to the API and surfaces a validation error. Keep the prior valid date or disable actions until a valid date is selected.
- The duration picker offers only a subset of valid 15-minute increments. Either expose all supported durations from 15 through 240 minutes or document the narrower product choice.
- Frontend automated coverage currently tests core booking flow, 409 refresh feedback, and stale booking-list responses. Add coverage for date/room changes during an in-flight availability refresh, network errors/timeouts, keyboard-only flows, and API contract edge cases.
- Room names are exact-match unique but not trimmed/case-normalized, so `Huddle`, `huddle`, and whitespace variants can become separate rooms. Normalize and validate names if they represent the same physical room.
- Add bounded database contention handling for SQLite. `BEGIN IMMEDIATE` serializes writers and works in the two-request test, but lock timeout errors under sustained contention currently surface as server errors rather than a clear retryable response.

## Remediation Order

1. **Security and correctness gates:** add authentication/authorization; make simulated latency opt-in; enforce capacity; bound request inputs; define production CORS; distinguish liveness/readiness.
2. **Database integrity and scale:** introduce migrations and timezone-safe storage; add PostgreSQL concurrency coverage and assess a database-level overlap constraint; add pagination and query indexes/filters; load test SQLite contention and production PostgreSQL.
3. **Frontend resilience:** stale response handling is implemented in booking list and slot finder; preserve a valid date, expose supported durations, and add component tests. Expand coverage to in-flight filter changes, keyboard-only flows, and timeout/error states.
4. **Operational verification:** run migration-forward/backward checks, full backend/frontend tests, dependency audit, API contract checks, and measured load tests against the production database configuration. Current local tests and build pass; migration, PostgreSQL, and load checks remain open.

## Acceptance Matrix: Availability Classification

Here, a **positive** means “the system says this slot is available”; a **negative** means “the system says it is unavailable.” A false positive recommends or accepts a slot that violates a rule. A false negative hides or rejects a slot that is valid.

| Scenario | Positive case: expected available | Negative case: expected unavailable | False-positive signal | False-negative signal |
|---|---|---|---|---|
| Half-open interval | Existing booking ends 11:00; candidate starts 11:00 | Candidate starts 10:59 and overlaps | Adjacent slot omitted from suggestions or rejected | Overlapping slot suggested or accepted |
| Cleaning buffer | 75-minute booking ends 11:15; next starts 11:30 | Next starts 11:15 | Buffer-period slot returned/accepted | Slot at exact buffer end 11:30 is omitted |
| Office window and weekdays | Monday 09:30 start; end exactly 18:30 | Before 09:30, after 18:30, or weekend | Out-of-window/weekend slot returned or accepted | Exact valid boundary omitted/rejected |
| Duration and grid | 15 and 240 minutes; starts on `:00`, `:15`, `:30`, `:45` | 14, 255, 20-minute duration, 09:35, or nonzero seconds | Invalid duration/alignment accepted | Valid 15-minute duration or aligned boundary rejected |
| Lunch | 30-minute meeting overlapping 13:00–14:00 | 45-minute meeting overlapping lunch | Long lunch-overlap returned/accepted | Short permitted lunch slot omitted/rejected |
| Room restriction | Employee in Board Room; intern in another room | Any intern in Board Room | Intern Board Room slot returned/accepted | Non-intern or other-room slot omitted/rejected |
| Room availability | Different room or non-overlapping time | Same room with true overlap | Conflicting room time returned/accepted | Available room/time omitted/rejected |
| Attendee availability | Attendee free, including exact back-to-back boundary | Attendee booked in another room over candidate | Participant conflict returned/accepted | Free participant time omitted/rejected |
| Participant and capacity | Distinct valid users within configured capacity | Unknown user or participant count above capacity | Unknown/over-capacity meeting accepted | Valid attendee list rejected |
| Timezone | `04:00Z` normalizes to `09:30+05:30` | Offset conversion moves slot outside business rules | Mislocalized slot returned/accepted | Equivalent instant rejected because of its source offset |
| Concurrency | One request wins an uncontended slot | Two overlapping requests race for same room or attendee | Both requests return success | Both fail, or loser gets a 5xx instead of `409` |

## Performance and Failure Scenarios

- Measure p50/p95/p99 for `GET /bookings`, `POST /rooms/{id}/suggest`, and `POST /bookings` with 1, 10, and 100 concurrent clients; include simulated latency disabled and explicit local simulation enabled.
- Seed increasing room/user/booking volumes (for example 1k, 10k, and 100k bookings) and measure database query time, ORM hydration, Python slot scan time, response size, and peak memory separately.
- Exercise empty dates, days with no availability, one room with a dense calendar, many unrelated rooms with bookings, and requests with the maximum allowed attendees.
- Run concurrency tests against PostgreSQL with independent connections and verify one `201` plus one `409` for same-room conflicts and shared-attendee conflicts. Add retry/timeout tests for database lock and connection failures.
- Verify API failure behavior for malformed JSON, invalid date/time, missing room/requester/attendee, database unavailable, frontend network timeout, and stale responses after changing date/room.
