import { useEffect, useState } from "react";
import { getBookings } from "../api.js";
import { formatTime } from "../dates.js";

export default function BookingList({ date, refreshKey }) {
  const [bookings, setBookings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const controller = new AbortController();
    let current = true;
    setLoading(true);
    setError(null);
    getBookings(date, { signal: controller.signal })
      .then((result) => current && setBookings(result))
      .catch((err) => {
        if (current && err.name !== "AbortError") setError(err.message);
      })
      .finally(() => current && setLoading(false));
    return () => {
      current = false;
      controller.abort();
    };
  }, [date, refreshKey]);

  return (
    <section className="schedule-panel" aria-labelledby="schedule-title">
      <div className="panel-heading schedule-heading">
        <div className="panel-index">02</div>
        <div>
          <p className="eyebrow">OFFICE CALENDAR</p>
          <h2 id="schedule-title">Daily schedule</h2>
        </div>
        {!loading && !error && <span className="booking-count">{bookings.length} {bookings.length === 1 ? "MEETING" : "MEETINGS"}</span>}
      </div>
      {loading && <p className="muted state-message" role="status">Loading the schedule…</p>}
      {error && <p className="error state-message" role="alert">{error}</p>}
      {!loading && !error && bookings.length === 0 && <p className="empty-schedule">Nothing booked yet. Use Find a time to make the first reservation.</p>}
      {!loading && !error && bookings.length > 0 && (
        <ol className="schedule-list">
          {bookings.map((booking) => (
            <li className="schedule-row" key={booking.id}>
              <div className="schedule-time">
                <strong>{formatTime(booking.start)}</strong>
                <span>{formatTime(booking.end)}</span>
              </div>
              <div className="schedule-marker" aria-hidden="true" />
              <div className="schedule-detail">
                <div className="schedule-title-line">
                  <h3>{booking.title || "Room booking"}</h3>
                  <span className="room-label">{booking.room.name}</span>
                </div>
                <p>{booking.attendees.length ? booking.attendees.map((attendee) => attendee.name).join(" · ") : "No additional attendees"}</p>
              </div>
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}
