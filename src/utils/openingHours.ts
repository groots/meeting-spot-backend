// Time-of-day opening-hours matching. Given a venue's weekly opening `periods`
// (from Google Place Details) and a coarse time-of-day window, decide whether
// the venue is open at some point during that window on any day. This excludes
// venues that never open during the requested window (e.g. a dinner-only
// restaurant for a morning meet) without needing a specific calendar day.

import type { GoogleOpeningPeriod } from '../services/placesClient.js';

export type TimeOfDay = 'morning' | 'afternoon' | 'evening';

// Window bounds in minutes-from-midnight, inclusive start, inclusive end.
//   morning   06:00–11:59
//   afternoon 12:00–16:59
//   evening   17:00–22:59
const TIME_OF_DAY_WINDOWS: Record<TimeOfDay, { start: number; end: number }> = {
  morning: { start: 6 * 60, end: 11 * 60 + 59 },
  afternoon: { start: 12 * 60, end: 16 * 60 + 59 },
  evening: { start: 17 * 60, end: 22 * 60 + 59 },
};

/** Validate/parse an incoming time-of-day value; null if not one of the three. */
export function parseTimeOfDay(value: unknown): TimeOfDay | null {
  if (typeof value !== 'string') return null;
  const v = value.trim().toLowerCase();
  if (v === 'morning' || v === 'afternoon' || v === 'evening') return v;
  return null;
}

// Parse a Google "HHMM" time string to minutes-from-midnight (0–1439), or null.
function parseHHMM(time: string | undefined): number | null {
  if (typeof time !== 'string' || !/^\d{4}$/.test(time)) return null;
  const hours = Number(time.slice(0, 2));
  const minutes = Number(time.slice(2, 4));
  if (hours > 23 || minutes > 59) return null;
  return hours * 60 + minutes;
}

// Do two minute-intervals [aStart, aEnd] and [bStart, bEnd] overlap? Treated as
// half-open at the end for openness (a place closing at 12:00 isn't "open" at
// 12:00), but the window end is inclusive so any true overlap counts.
function intervalsOverlap(
  aStart: number,
  aEnd: number,
  bStart: number,
  bEnd: number
): boolean {
  return aStart <= bEnd && bStart < aEnd;
}

/**
 * True when any weekly opening period overlaps the given time-of-day window on
 * any day. Handles three period shapes:
 *   - Normal: open.time < close.time on the same day.
 *   - 24-hour: an `open` at 0000 with no `close` (Google's "always open").
 *   - Overnight: close day/time is earlier than open (wraps past midnight); the
 *     portion before midnight counts on the open day, the portion after counts
 *     as early-morning (only relevant to the morning window's start).
 *
 * The window is day-agnostic (we don't know which weekday the meet lands on), so
 * a single matching day is enough.
 */
export function isOpenDuringTimeOfDay(
  periods: GoogleOpeningPeriod[] | null | undefined,
  tod: TimeOfDay
): boolean {
  if (!periods || periods.length === 0) return false;
  const win = TIME_OF_DAY_WINDOWS[tod];

  for (const period of periods) {
    const openTime = parseHHMM(period.open?.time);
    if (openTime === null) continue;

    // 24-hour: open with no close ⇒ open across every window.
    if (!period.close || period.close.time === undefined) {
      return true;
    }

    const closeTime = parseHHMM(period.close.time);
    if (closeTime === null) continue;

    const openDay = period.open?.day;
    const closeDay = period.close?.day;
    const overnight =
      closeTime <= openTime ||
      (typeof openDay === 'number' && typeof closeDay === 'number' && closeDay !== openDay);

    if (!overnight) {
      // Same-day period [openTime, closeTime).
      if (intervalsOverlap(openTime, closeTime, win.start, win.end)) {
        return true;
      }
    } else {
      // Overnight period splits into [openTime, 1440) on the open day and
      // [0, closeTime) on the following day.
      if (intervalsOverlap(openTime, 24 * 60, win.start, win.end)) {
        return true;
      }
      if (intervalsOverlap(0, closeTime, win.start, win.end)) {
        return true;
      }
    }
  }

  return false;
}
