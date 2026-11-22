from concurrent.futures import ThreadPoolExecutor

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base, get_db
from app.main import app
from app.seed import seed


def test_simultaneous_overlapping_requests_only_create_one_booking(tmp_path):
    database_path = (tmp_path / "concurrent.sqlite").as_posix()
    engine = create_engine(
        f"sqlite:///{database_path}",
        connect_args={"check_same_thread": False, "timeout": 10},
    )
    Base.metadata.create_all(bind=engine)
    test_session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    with test_session() as db:
        seed(db)

    def override_get_db():
        db = test_session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    payload = {
        "room_id": 3,
        "creator_id": 4,
        "attendee_ids": [4],
        "title": "Concurrent request",
        "start": "2026-12-07T10:00:00+05:30",
        "end": "2026-12-07T10:30:00+05:30",
    }
    try:
        with TestClient(app) as client:
            with ThreadPoolExecutor(max_workers=2) as pool:
                responses = list(pool.map(lambda _: client.post("/bookings", json=payload), range(2)))
        assert sorted(response.status_code for response in responses) == [201, 409]
    finally:
        app.dependency_overrides.clear()
        engine.dispose()
