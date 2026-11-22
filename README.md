# RoomBook

A small meeting-room booking app: FastAPI backend, React frontend.

The task is in [ASSIGNMENT.md](ASSIGNMENT.md).

## Requirements

- Python 3.11+
- Node 22.12+ (the frontend test runner requires this patched runtime)
- Optional: Docker (for PostgreSQL). Without it, the backend uses a local SQLite file.

## Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m app.seed          # resets the database and loads sample data
uvicorn app.main:app --reload
```

The API runs on http://localhost:8000. Interactive docs are at http://localhost:8000/docs.

### Using PostgreSQL instead of SQLite

```bash
docker compose up -d
export DATABASE_URL=postgresql+psycopg://roombook:roombook@localhost:5432/roombook
python -m app.seed
uvicorn app.main:app --reload
```

### Settings

| Variable | Default | Meaning |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./roombook.db` | SQLAlchemy database URL |
| `SIMULATED_LATENCY_MS` | `0` | Optional local-dev random 0–N ms delay for GET requests. Enable only when you want to simulate a slower network. |
| `CORS_ALLOWED_ORIGINS` | `http://localhost:5173` | Comma-separated exact origins allowed by the API, for example `https://rooms.example.com`. |

`GET /health/live` checks that the process is running. `GET /health/ready` (also available at `/health`) checks database connectivity.

### Tests

```bash
cd backend
pytest
```

Tests use an in-memory SQLite database with the same sample data as `app/seed.py`.

## Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. The dev server proxies `/api/*` to the backend on port 8000.

Frontend checks:

```bash
npm test
npm run build
```

## Sample data

`python -m app.seed` loads 6 users, 3 rooms and a few bookings. Most bookings are on **Monday 2026-12-07**, and there are some on the days around it. The frontend opens on that date.

| id | User | Role |
|---|---|---|
| 1 | Asha | employee |
| 2 | Ben | employee |
| 3 | Chen | manager |
| 4 | Divya | intern |
| 5 | Eli | employee |
| 6 | Farah | employee |

| id | Room | Capacity |
|---|---|---|
| 1 | Focus Room | 4 |
| 2 | Board Room | 12 |
| 3 | Huddle | 6 |

## API

| Method | Path | Notes |
|---|---|---|
| GET | `/rooms` | |
| GET | `/rooms/{id}` | |
| POST | `/rooms` | `{name, capacity}` |
| GET | `/users` | |
| GET | `/bookings?date=YYYY-MM-DD&room_id=&limit=100&offset=0` | Filters optional; limit is 1–500 and results have stable start/id ordering |
| POST | `/bookings` | `{room_id, creator_id, title, attendee_ids, start, end}`; returns `409` if the room or a participant is unavailable |
| POST | `/rooms/{id}/suggest` | `{requester_id, attendee_ids, duration_minutes, date}`; returns up to 3 earliest available slots |

Booking timestamps are interpreted as IST when no UTC offset is supplied. Offset-aware timestamps are converted to IST, and API responses include the `+05:30` offset. Booking creation enforces office hours, 15-minute increments, lunch and room rules, attendee availability, and cleaning buffers in addition to preventing room conflicts. Conflict responses use `409`.

The creator counts as a participant for room capacity. The request may include at most 100 attendee IDs, and distinct participant count cannot exceed room capacity. Room names are trimmed and case-insensitive duplicates are rejected.

The slot suggestion endpoint returns an empty list on weekends. Its candidate slots begin on 15-minute boundaries and are limited to 09:30–18:30 IST, Monday through Friday. A requester is treated as a participant even when not repeated in `attendee_ids`.

Booking writes use PostgreSQL row locks for rooms and participants. SQLite uses an immediate write transaction to serialize availability checks. Availability queries are filtered to the requested room and participants, with indexes for the reverse attendee lookup and room/time range. This protects writes made through the application; direct database writes can bypass the checks. See [`DECISIONS.md`](DECISIONS.md) for trade-offs and remaining work.

### Examples

```bash
curl -s "localhost:8000/bookings?date=2026-12-07&room_id=3"
```

```bash
curl -s -X POST localhost:8000/bookings \
  -H 'Content-Type: application/json' \
  -d '{"room_id": 3, "creator_id": 2, "title": "Pairing", "attendee_ids": [2],
       "start": "2026-12-07T12:15:00+05:30", "end": "2026-12-07T12:45:00+05:30"}'
```
