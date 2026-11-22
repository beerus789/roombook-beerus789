import { shiftDate } from "../dates.js";

export default function DateNav({ date, onChange }) {
  return (
    <div className="date-nav" aria-label="Choose schedule date">
      <button type="button" onClick={() => onChange(shiftDate(date, -1))} aria-label="Previous day">
        <span aria-hidden="true">←</span>
      </button>
      <label>
        <span className="visually-hidden">Schedule date</span>
        <input type="date" value={date} onChange={(event) => { if (event.target.value) onChange(event.target.value); }} />
      </label>
      <button type="button" onClick={() => onChange(shiftDate(date, 1))} aria-label="Next day">
        <span aria-hidden="true">→</span>
      </button>
    </div>
  );
}
