import { useState } from "react";
import DateNav from "./components/DateNav.jsx";
import RoomList from "./components/RoomList.jsx";
import BookingList from "./components/BookingList.jsx";
import SlotFinder from "./components/SlotFinder.jsx";

const FIRST_SEEDED_DAY = "2026-12-07";

export default function App() {
  const [date, setDate] = useState(FIRST_SEEDED_DAY);
  const [bookingRevision, setBookingRevision] = useState(0);

  return (
    <div className="app-frame">
      <header className="topbar">
        <a className="wordmark" href="#top" aria-label="RoomBook home">
          <span className="wordmark-symbol">R</span>
          <span>ROOMBOOK</span>
        </a>
        <div className="workspace-label"><span className="status-dot" /> WORKPLACE · INDIA</div>
        <DateNav date={date} onChange={setDate} />
      </header>
      <main id="top">
        <section className="page-intro">
          <div>
            <p className="eyebrow">MEETING ROOMS / DAILY VIEW</p>
            <h1>Make room for<br className="desktop-break" /> the work.</h1>
            <p className="intro-copy">Find a time that works for your people and the room.</p>
          </div>
          <div className="date-context">
            <span>SELECTED DAY</span>
            <strong>{date}</strong>
            <small>09:30–18:30 · IST</small>
          </div>
        </section>
        <section className="workspace-grid" aria-label="Room booking workspace">
          <aside className="booking-rail">
            <SlotFinder date={date} onBooked={() => setBookingRevision((revision) => revision + 1)} />
            <RoomList />
          </aside>
          <BookingList date={date} refreshKey={bookingRevision} />
        </section>
        <footer className="page-footer">
          <span>ROOMBOOK / WORKPLACE SCHEDULING</span>
          <span>ALL TIMES IN INDIA STANDARD TIME</span>
        </footer>
      </main>
    </div>
  );
}
