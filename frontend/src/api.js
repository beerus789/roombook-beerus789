const BASE = "/api";

async function request(path, options = {}) {
  const timeout = AbortSignal.timeout(15000);
  const signal = options.signal
    ? AbortSignal.any([options.signal, timeout])
    : timeout;
  const res = await fetch(BASE + path, { ...options, signal });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    const detail = typeof body.detail === "string"
      ? body.detail
      : Array.isArray(body.detail)
        ? body.detail.map((item) => item.msg).join("; ")
        : null;
    const error = new Error(detail || `Request failed (${res.status})`);
    error.status = res.status;
    throw error;
  }
  return res.json();
}

export const getRooms = (options = {}) => request("/rooms", options);

export const getUsers = (options = {}) => request("/users", options);

export const getBookings = (date, options = {}) =>
  request(`/bookings?date=${encodeURIComponent(date)}`, options);

export const suggestSlots = (roomId, criteria, signal) =>
  request(`/rooms/${roomId}/suggest`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(criteria),
    signal,
  });

export const createBooking = (booking) =>
  request("/bookings", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(booking),
  });
