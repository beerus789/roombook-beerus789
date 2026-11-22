// @vitest-environment jsdom
import { act, cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("../api.js", () => ({
  createBooking: vi.fn(),
  getBookings: vi.fn(),
  getRooms: vi.fn(),
  getUsers: vi.fn(),
  suggestSlots: vi.fn(),
}));

import { createBooking, getBookings, getRooms, getUsers, suggestSlots } from "../api.js";
import BookingList from "./BookingList.jsx";
import SlotFinder from "./SlotFinder.jsx";

const rooms = [{ id: 1, name: "Focus Room", capacity: 2 }];
const users = [
  { id: 1, name: "Asha", role: "employee" },
  { id: 2, name: "Ben", role: "employee" },
  { id: 3, name: "Chen", role: "manager" },
];
const firstSlot = {
  start: "2026-12-07T11:30:00+05:30",
  end: "2026-12-07T12:00:00+05:30",
};

afterEach(cleanup);

beforeEach(() => {
  vi.clearAllMocks();
  getRooms.mockResolvedValue(rooms);
  getUsers.mockResolvedValue(users);
  suggestSlots.mockResolvedValue({ slots: [firstSlot] });
  createBooking.mockResolvedValue({ id: 100 });
});

describe("slot finder", () => {
  it("limits attendee selection by room capacity and books a suggested slot", async () => {
    const user = userEvent.setup();
    const onBooked = vi.fn();
    render(<SlotFinder date="2026-12-07" onBooked={onBooked} />);

    await screen.findByRole("button", { name: "Show available times" });
    const ben = screen.getByRole("checkbox", { name: "Ben" });
    const chen = screen.getByRole("checkbox", { name: "Chen" });
    await user.click(ben);
    expect(chen.disabled).toBe(true);

    await user.click(screen.getByRole("button", { name: "Show available times" }));
    await screen.findByRole("button", { name: "Book" });
    await user.click(screen.getByRole("button", { name: "Book" }));

    await screen.findByText("Booking confirmed.");
    expect(createBooking).toHaveBeenCalledWith(expect.objectContaining({
      room_id: 1,
      creator_id: 1,
      attendee_ids: [2, 1],
      start: firstSlot.start,
    }));
    expect(onBooked).toHaveBeenCalledTimes(1);
  });

  it("refreshes suggestions when the chosen slot has been taken", async () => {
    const user = userEvent.setup();
    const nextSlot = {
      start: "2026-12-07T12:00:00+05:30",
      end: "2026-12-07T12:30:00+05:30",
    };
    suggestSlots
      .mockResolvedValueOnce({ slots: [firstSlot] })
      .mockResolvedValueOnce({ slots: [nextSlot] });
    createBooking.mockRejectedValueOnce(Object.assign(new Error("Conflict"), { status: 409 }));
    render(<SlotFinder date="2026-12-07" onBooked={vi.fn()} />);

    await screen.findByRole("button", { name: "Show available times" });
    await user.click(screen.getByRole("button", { name: "Show available times" }));
    await screen.findByRole("button", { name: "Book" });
    await user.click(screen.getByRole("button", { name: "Book" }));

    await screen.findByText("That time was taken. The available times have been refreshed.");
    expect(screen.getByText("12:00")).toBeTruthy();
    expect(suggestSlots).toHaveBeenCalledTimes(2);
  });
});

describe("booking list request ordering", () => {
  it("does not replace the current date with a slower response from the previous date", async () => {
    let resolveOld;
    let resolveCurrent;
    getBookings
      .mockImplementationOnce(() => new Promise((resolve) => { resolveOld = resolve; }))
      .mockImplementationOnce(() => new Promise((resolve) => { resolveCurrent = resolve; }));
    const oldBooking = {
      id: 1, title: "Old date", room: { name: "Focus Room" }, attendees: [],
      start: "2026-12-07T10:00:00+05:30", end: "2026-12-07T10:30:00+05:30",
    };
    const currentBooking = {
      id: 2, title: "Current date", room: { name: "Huddle" }, attendees: [],
      start: "2026-12-08T10:00:00+05:30", end: "2026-12-08T10:30:00+05:30",
    };
    const view = render(<BookingList date="2026-12-07" refreshKey={0} />);
    await waitFor(() => expect(getBookings).toHaveBeenCalledTimes(1));
    view.rerender(<BookingList date="2026-12-08" refreshKey={0} />);
    await waitFor(() => expect(getBookings).toHaveBeenCalledTimes(2));

    await act(async () => { resolveCurrent([currentBooking]); });
    expect(await screen.findByText("Current date")).toBeTruthy();
    await act(async () => { resolveOld([oldBooking]); });

    expect(screen.getByText("Current date")).toBeTruthy();
    expect(screen.queryByText("Old date")).toBeNull();
  });
});



