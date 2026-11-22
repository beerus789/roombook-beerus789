import { useEffect, useState } from "react";
import { getRooms } from "../api.js";

export default function RoomList() {
  const [rooms, setRooms] = useState([]);
  const [error, setError] = useState(null);

  useEffect(() => {
    const controller = new AbortController();
    let current = true;
    getRooms({ signal: controller.signal })
      .then((result) => current && setRooms(result))
      .catch((err) => current && err.name !== "AbortError" && setError(err.message));
    return () => {
      current = false;
      controller.abort();
    };
  }, []);

  return (
    <section className="rooms-panel" aria-labelledby="rooms-title">
      <div className="rooms-heading">
        <div>
          <p className="eyebrow">SPACE DIRECTORY</p>
          <h2 id="rooms-title">Rooms</h2>
        </div>
        {!error && <span>{rooms.length.toString().padStart(2, "0")}</span>}
      </div>
      {error && <p className="error" role="alert">{error}</p>}
      <ul className="room-list">
        {rooms.map((room, index) => (
          <li key={room.id}>
            <span className="room-number">{String(index + 1).padStart(2, "0")}</span>
            <strong>{room.name}</strong>
            <span className="room-capacity">{room.capacity} seats</span>
          </li>
        ))}
      </ul>
    </section>
  );
}
