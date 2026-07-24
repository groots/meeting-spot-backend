// Pure availability helpers + Google FreeBusy orchestration.
//
// PRIVACY: FreeBusy returns opaque busy intervals (no titles). We never persist
// those intervals — only compute open slots for the current request response.
import axios from 'axios';
import { OAuth2Client } from 'google-auth-library';
import { env } from '../config/env.js';
import * as calendarConnectionService from './calendarConnectionService.js';

export interface TimeInterval {
  start: Date;
  end: Date;
}

export interface AvailabilitySlot {
  start: string; // ISO
  end: string; // ISO
}

const FREEBUSY_URL = 'https://www.googleapis.com/calendar/v3/freeBusy';
const DEFAULT_WINDOW_DAYS = 7;
const DEFAULT_SLOT_MIN = 60;
const DEFAULT_STEP_MIN = 30;
/** Local wall-clock business hours used when generating candidate slots. */
const BUSINESS_START_HOUR = 9;
const BUSINESS_END_HOUR = 18;

export function mergeIntervals(intervals: TimeInterval[]): TimeInterval[] {
  if (intervals.length === 0) return [];
  const sorted = [...intervals].sort((a, b) => a.start.getTime() - b.start.getTime());
  const out: TimeInterval[] = [{ ...sorted[0] }];
  for (let i = 1; i < sorted.length; i++) {
    const cur = sorted[i];
    const last = out[out.length - 1];
    if (cur.start.getTime() <= last.end.getTime()) {
      if (cur.end.getTime() > last.end.getTime()) last.end = cur.end;
    } else {
      out.push({ ...cur });
    }
  }
  return out;
}

/** Free intervals inside [windowStart, windowEnd] after subtracting busy. */
export function freeIntervals(
  windowStart: Date,
  windowEnd: Date,
  busy: TimeInterval[]
): TimeInterval[] {
  const merged = mergeIntervals(
    busy.filter((b) => b.end > windowStart && b.start < windowEnd)
  );
  const free: TimeInterval[] = [];
  let cursor = windowStart;
  for (const b of merged) {
    const busyStart = b.start < windowStart ? windowStart : b.start;
    const busyEnd = b.end > windowEnd ? windowEnd : b.end;
    if (busyStart > cursor) {
      free.push({ start: cursor, end: busyStart });
    }
    if (busyEnd > cursor) cursor = busyEnd;
  }
  if (cursor < windowEnd) {
    free.push({ start: cursor, end: windowEnd });
  }
  return free;
}

/** Intersect two free-interval lists (both parties free). */
export function intersectFree(a: TimeInterval[], b: TimeInterval[]): TimeInterval[] {
  const out: TimeInterval[] = [];
  let i = 0;
  let j = 0;
  while (i < a.length && j < b.length) {
    const start = a[i].start > b[j].start ? a[i].start : b[j].start;
    const end = a[i].end < b[j].end ? a[i].end : b[j].end;
    if (start < end) out.push({ start, end });
    if (a[i].end < b[j].end) i++;
    else j++;
  }
  return out;
}

/**
 * Emit fixed-duration slots on step boundaries within free intervals, limited
 * to local business hours (viewer/server local for Phase 1).
 */
export function generateSlots(
  free: TimeInterval[],
  opts: { durationMin?: number; stepMin?: number; maxSlots?: number } = {}
): AvailabilitySlot[] {
  const durationMs = (opts.durationMin ?? DEFAULT_SLOT_MIN) * 60_000;
  const stepMs = (opts.stepMin ?? DEFAULT_STEP_MIN) * 60_000;
  const maxSlots = opts.maxSlots ?? 24;
  const slots: AvailabilitySlot[] = [];

  for (const interval of free) {
    // Align to step from epoch-minutes for stable boundaries.
    let t = Math.ceil(interval.start.getTime() / stepMs) * stepMs;
    while (t + durationMs <= interval.end.getTime()) {
      const start = new Date(t);
      const end = new Date(t + durationMs);
      if (isWithinBusinessHours(start, end)) {
        slots.push({ start: start.toISOString(), end: end.toISOString() });
        if (slots.length >= maxSlots) return slots;
      }
      t += stepMs;
    }
  }
  return slots;
}

function isWithinBusinessHours(start: Date, end: Date): boolean {
  // Same local calendar day and inside [BUSINESS_START, BUSINESS_END].
  if (
    start.getFullYear() !== end.getFullYear() ||
    start.getMonth() !== end.getMonth() ||
    start.getDate() !== end.getDate()
  ) {
    return false;
  }
  const startMinutes = start.getHours() * 60 + start.getMinutes();
  const endMinutes = end.getHours() * 60 + end.getMinutes();
  return (
    startMinutes >= BUSINESS_START_HOUR * 60 && endMinutes <= BUSINESS_END_HOUR * 60
  );
}

export function defaultWindow(now = new Date()): { start: Date; end: Date } {
  const start = new Date(now.getTime() + 60 * 60 * 1000); // at least 1h out
  const end = new Date(start.getTime() + DEFAULT_WINDOW_DAYS * 24 * 60 * 60 * 1000);
  return { start, end };
}

async function accessTokenForUser(userId: string): Promise<string | null> {
  const connection = await calendarConnectionService.findActive(userId);
  if (!connection) return null;

  const refreshToken = calendarConnectionService.decryptRefreshToken(connection);
  const client = new OAuth2Client(
    env.googleClientId,
    env.googleClientSecret,
    env.googleCalendarRedirectUri
  );
  client.setCredentials({ refresh_token: refreshToken });
  const tokenResponse = await client.getAccessToken();
  const token = typeof tokenResponse === 'string' ? tokenResponse : tokenResponse?.token;
  return token || null;
}

export async function fetchBusyIntervals(
  userId: string,
  windowStart: Date,
  windowEnd: Date
): Promise<TimeInterval[] | null> {
  const accessToken = await accessTokenForUser(userId);
  if (!accessToken) return null;

  const res = await axios.post(
    FREEBUSY_URL,
    {
      timeMin: windowStart.toISOString(),
      timeMax: windowEnd.toISOString(),
      items: [{ id: 'primary' }],
    },
    {
      headers: {
        Authorization: `Bearer ${accessToken}`,
        'Content-Type': 'application/json',
      },
      timeout: 10_000,
    }
  );

  const busyRaw = res.data?.calendars?.primary?.busy ?? [];
  return (busyRaw as Array<{ start?: string; end?: string }>)
    .map((b) => ({
      start: new Date(b.start ?? ''),
      end: new Date(b.end ?? ''),
    }))
    .filter((b) => !Number.isNaN(b.start.getTime()) && !Number.isNaN(b.end.getTime()));
}

export interface MeetingAvailability {
  slots: AvailabilitySlot[];
  my_connected: boolean;
  their_connected: boolean;
  partial: boolean;
  window_start: string;
  window_end: string;
}

/**
 * Compute open slots for a meeting. Phase 1: organizer (A) FreeBusy only when
 * invitee is not yet linked; when both user ids are provided and connected,
 * intersect. Falls back to empty slots (UI keeps manual propose).
 */
export async function computeMeetingAvailability(opts: {
  organizerUserId: string | null;
  inviteeUserId?: string | null;
  viewerIsOrganizer: boolean;
  durationMin?: number | null;
}): Promise<MeetingAvailability> {
  const { start, end } = defaultWindow();
  const durationMin =
    typeof opts.durationMin === 'number' && opts.durationMin > 0
      ? opts.durationMin
      : DEFAULT_SLOT_MIN;

  const organizerId = opts.organizerUserId;
  const inviteeId = opts.inviteeUserId ?? null;

  const myId = opts.viewerIsOrganizer ? organizerId : inviteeId;
  const theirId = opts.viewerIsOrganizer ? inviteeId : organizerId;

  const myConnected = myId ? await calendarConnectionService.isConnected(myId) : false;
  const theirConnected = theirId ? await calendarConnectionService.isConnected(theirId) : false;

  let slots: AvailabilitySlot[] = [];

  if (organizerId && inviteeId && myConnected && theirConnected) {
    const [busyA, busyB] = await Promise.all([
      fetchBusyIntervals(organizerId, start, end),
      fetchBusyIntervals(inviteeId, start, end),
    ]);
    if (busyA && busyB) {
      const freeA = freeIntervals(start, end, busyA);
      const freeB = freeIntervals(start, end, busyB);
      slots = generateSlots(intersectFree(freeA, freeB), { durationMin });
    }
  } else if (organizerId && (await calendarConnectionService.isConnected(organizerId))) {
    // Organizer-only Phase 1 path: show times that work for the organizer.
    const busyA = await fetchBusyIntervals(organizerId, start, end);
    if (busyA) {
      slots = generateSlots(freeIntervals(start, end, busyA), { durationMin });
    }
  }

  return {
    slots,
    my_connected: myConnected,
    their_connected: theirConnected,
    partial: !(myConnected && theirConnected),
    window_start: start.toISOString(),
    window_end: end.toISOString(),
  };
}
