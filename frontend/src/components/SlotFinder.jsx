import { useCallback, useEffect, useRef, useState } from "react";
import { createBooking, getRooms, getUsers, suggestSlots } from "../api.js";

const DURATIONS = Array.from({ length: 16 }, (_, index) => (index + 1) * 15);

export default function SlotFinder({ date, onBooked }) {
  const [rooms, setRooms] = useState([]);
  const [users, setUsers] = useState([]);
  const [roomId, setRoomId] = useState("");
  const [requesterId, setRequesterId] = useState("");
  const [attendeeIds, setAttendeeIds] = useState([]);
  const [title, setTitle] = useState("");
  const [duration, setDuration] = useState(30);
  const [slots, setSlots] = useState([]);
  const [loading, setLoading] = useState(false);
  const [bookingSlot, setBookingSlot] = useState(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [loaded, setLoaded] = useState(false);
  const [searched, setSearched] = useState(false);
  const searchVersion = useRef(0);
  const searchController = useRef(null);

  const room = rooms.find((item) => String(item.id) === roomId);
  const participantCount = new Set([...attendeeIds, Number(requesterId)].filter(Boolean)).size;
  const overCapacity = room && participantCount > room.capacity;

  const clearSuggestions = useCallback(() => {
    searchVersion.current += 1;
    searchController.current?.abort();
    searchController.current = null;
    setSlots([]);
    setLoading(false);
    setNotice("");
    setSearched(false);
    setError("");
  }, []);

  useEffect(() => {
    let active = true;
    const controller = new AbortController();
    Promise.all([getRooms({ signal: controller.signal }), getUsers({ signal: controller.signal })])
      .then(([roomList, userList]) => {
        if (!active) return;
        setRooms(roomList);
        setUsers(userList);
        setRoomId(String(roomList[0]?.id ?? ""));
        setRequesterId(String(userList[0]?.id ?? ""));
      })
      .catch((err) => active && err.name !== "AbortError" && setError(err.message))
      .finally(() => active && setLoaded(true));
    return () => { active = false; controller.abort(); };
  }, []);

  useEffect(() => {
    clearSuggestions();
  }, [date, clearSuggestions]);

  function toggleAttendee(id) {
    setAttendeeIds((current) => current.includes(id)
      ? current.filter((value) => value !== id)
      : [...current, id]);
    clearSuggestions();
  }

  async function loadSuggestions() {
    if (!roomId || !requesterId || overCapacity || !date) return null;
    searchController.current?.abort();
    const controller = new AbortController();
    searchController.current = controller;
    const version = ++searchVersion.current;
    setLoading(true);
    setError("");
    setNotice("");
    try {
      const result = await suggestSlots(Number(roomId), {
        requester_id: Number(requesterId),
        attendee_ids: attendeeIds,
        duration_minutes: Number(duration),
        date,
      }, controller.signal);
      if (version !== searchVersion.current) return null;
      setSlots(result.slots);
      setSearched(true);
      return result.slots;
    } catch (err) {
      if (version !== searchVersion.current || err.name === "AbortError") return null;
      setError(err.message);
      setSlots([]);
      return null;
    } finally {
      if (version === searchVersion.current) {
        setLoading(false);
        searchController.current = null;
      }
    }
  }

  async function handleBook(slot) {
    if (bookingSlot !== null || overCapacity) return;
    const selectedRoomId = Number(roomId);
    const selectedRequesterId = Number(requesterId);
    const selectedAttendeeIds = [...new Set([...attendeeIds, selectedRequesterId])];
    const queryVersion = searchVersion.current;
    setBookingSlot(slot.start);
    setError("");
    setNotice("");
    try {
      await createBooking({
        room_id: selectedRoomId,
        creator_id: selectedRequesterId,
        title: title.trim() || "Room booking",
        attendee_ids: selectedAttendeeIds,
        start: slot.start,
        end: slot.end,
      });
      setSlots((current) => current.filter((item) => item.start !== slot.start));
      setNotice("Booking confirmed.");
      onBooked();
    } catch (err) {
      if (err.status === 409) {
        if (queryVersion !== searchVersion.current) {
          setNotice("That time was taken. Your date changed; search again for current availability.");
          return;
        }
        const refreshed = await loadSuggestions();
        setNotice(refreshed === null
          ? "That time was taken. Run the search again for current availability."
          : "That time was taken. The available times have been refreshed.");
      } else {
        setError(err.message);
      }
    } finally {
      setBookingSlot(null);
    }
  }

  return (
    <section className="finder-panel" aria-labelledby="slot-finder-title">
      <div className="panel-heading">
        <div className="panel-index">01</div>
        <div>
          <p className="eyebrow">AVAILABILITY</p>
          <h2 id="slot-finder-title">Find a time</h2>
        </div>
      </div>

      {error && <p className="error" role="alert">{error}</p>}
      {!loaded ? <p className="muted" role="status">Loading rooms and people…</p> : (
        <>
          <div className="finder-controls">
            <label className="field">
              <span>Room</span>
              <select value={roomId} onChange={(event) => { setRoomId(event.target.value); clearSuggestions(); }} disabled={bookingSlot !== null}>
                {rooms.map((item) => <option key={item.id} value={item.id}>{item.name} · {item.capacity} seats</option>)}
              </select>
            </label>
            <label className="field">
              <span>Booking for</span>
              <select value={requesterId} onChange={(event) => { setRequesterId(event.target.value); clearSuggestions(); }} disabled={bookingSlot !== null}>
                {users.map((user) => <option key={user.id} value={user.id}>{user.name} · {user.role}</option>)}
              </select>
            </label>
            <label className="field">
              <span>Duration</span>
              <select value={duration} onChange={(event) => { setDuration(event.target.value); clearSuggestions(); }} disabled={bookingSlot !== null}>
                {DURATIONS.map((minutes) => <option key={minutes} value={minutes}>{minutes} minutes</option>)}
              </select>
            </label>
            <label className="field">
              <span>Meeting title <small>OPTIONAL</small></span>
              <input maxLength={200} value={title} onChange={(event) => setTitle(event.target.value)} placeholder="e.g. Product review" disabled={bookingSlot !== null} />
            </label>
          </div>

          <fieldset className="attendee-picker" disabled={bookingSlot !== null}>
            <legend>People <span>{participantCount}{room ? ` / ${room.capacity}` : ""}</span></legend>
            <p className="field-note">Booking for is included automatically.</p>
            <div className="attendee-options">
              {users.filter((user) => String(user.id) !== requesterId).map((user) => (
                <label className="check-option" key={user.id}>
                  <input
                    type="checkbox"
                    checked={attendeeIds.includes(user.id)}
                    onChange={() => toggleAttendee(user.id)}
                    disabled={!attendeeIds.includes(user.id) && Boolean(room) && participantCount >= room.capacity}
                  />
                  <span>{user.name}</span>
                </label>
              ))}
            </div>
            {overCapacity && <p className="error inline-error" role="alert">This room seats {room.capacity}. Remove an attendee to continue.</p>}
          </fieldset>

          <button className="search-button" onClick={loadSuggestions} disabled={!roomId || !requesterId || loading || Boolean(overCapacity)}>
            <span>{loading ? "Checking availability" : "Show available times"}</span>
            <span aria-hidden="true">↗</span>
          </button>

      {notice && <p className="success-note" role="status">{notice}</p>}

          <div className="availability-results" aria-live="polite">
            <div className="results-heading">
              <h3>Suggested times</h3>
              <span>EARLIEST FIRST · IST</span>
            </div>
            {loading && <p className="muted" role="status">Checking rooms and attendees…</p>}
            {!loading && slots.map((slot, index) => (
              <article className={`slot-row ${index === 0 ? "slot-row-first" : ""}`} key={slot.start}>
                <div className="slot-time">
                  <strong>{slot.start.slice(11, 16)}</strong>
                  <span>to {slot.end.slice(11, 16)}</span>
                </div>
                <button className="book-button" onClick={() => handleBook(slot)} disabled={bookingSlot !== null}>
                  {bookingSlot === slot.start ? "Booking…" : "Book"}
                </button>
              </article>
            ))}
            {!loading && slots.length === 0 && (
              <p className="results-empty">
                {searched ? "No times match these choices." : "Choose the room and attendees to check availability."}
              </p>
            )}
          </div>
        </>
      )}
    </section>
  );
}
