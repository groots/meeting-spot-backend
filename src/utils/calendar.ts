// Shared helpers to build "add to calendar" artifacts for a finalized meeting:
// a Google Calendar template URL and a minimal RFC 5545 .ics VEVENT. Hand-rolled
// (no new deps), mirroring directions.ts.
//
// PRIVACY: `location` is the public venue name + address ONLY. Never embed
// location_a/location_b, anyone's home address, or coordinates in a calendar
// event — both parties (and any app they import the .ics into) can read it.

export interface CalendarEvent {
  requestId: string;
  title: string;
  // Venue name + formatted address only (public). Used as the event location.
  location: string;
  description?: string;
  start: Date;
  // End time; callers derive it from start + duration (default 60 min).
  end: Date;
}

/**
 * Format a Date as a UTC "basic" timestamp (YYYYMMDDTHHMMSSZ) as required by
 * both Google Calendar's `dates` param and iCalendar DTSTART/DTEND.
 */
export function toBasicUtc(d: Date): string {
  return d.toISOString().replace(/[-:]/g, '').replace(/\.\d{3}/, '');
}

/**
 * Build a Google Calendar "render" template URL that pre-fills a new event.
 * Times are encoded as a UTC basic-format range. text/location/details are
 * URL-encoded via URLSearchParams.
 */
export function buildCalendarUrl(event: CalendarEvent): string {
  const params = new URLSearchParams({
    action: 'TEMPLATE',
    text: event.title,
    dates: `${toBasicUtc(event.start)}/${toBasicUtc(event.end)}`,
    location: event.location,
  });
  if (event.description) {
    params.set('details', event.description);
  }
  return `https://calendar.google.com/calendar/render?${params.toString()}`;
}

/**
 * Escape a text value for an iCalendar property per RFC 5545 §3.3.11:
 * backslash, semicolon, comma are escaped, and newlines become "\n".
 */
function escapeIcsText(value: string): string {
  return value
    .replace(/\\/g, '\\\\')
    .replace(/;/g, '\\;')
    .replace(/,/g, '\\,')
    .replace(/\r\n|\r|\n/g, '\\n');
}

/**
 * Fold a content line to a maximum of 75 octets per RFC 5545 §3.1, continuing
 * wrapped segments with a leading space. Counts UTF-8 octets (not code units)
 * so multi-byte characters aren't split mid-sequence.
 */
function foldLine(line: string): string {
  const out: string[] = [];
  let current = '';
  let currentOctets = 0;
  // First line allows 75 octets; continuation lines allow 74 (the leading space
  // counts toward the 75-octet limit).
  let limit = 75;

  for (const ch of line) {
    const chOctets = Buffer.byteLength(ch, 'utf8');
    if (currentOctets + chOctets > limit) {
      out.push(current);
      current = ' ' + ch;
      currentOctets = 1 + chOctets;
      limit = 75;
    } else {
      current += ch;
      currentOctets += chOctets;
    }
  }
  out.push(current);
  return out.join('\r\n');
}

/**
 * Build a minimal single-VEVENT iCalendar document for the meeting. Lines are
 * CRLF-terminated, text values RFC-escaped, and each property folded to 75
 * octets. UID is stable per request so re-imports update the same event.
 */
export function buildIcs(event: CalendarEvent): string {
  const dtstamp = toBasicUtc(new Date());
  const lines = [
    'BEGIN:VCALENDAR',
    'VERSION:2.0',
    'PRODID:-//Find A Meeting Spot//Scheduling//EN',
    'BEGIN:VEVENT',
    `UID:${event.requestId}@findameetingspot.com`,
    `DTSTAMP:${dtstamp}`,
    `DTSTART:${toBasicUtc(event.start)}`,
    `DTEND:${toBasicUtc(event.end)}`,
    `SUMMARY:${escapeIcsText(event.title)}`,
    `LOCATION:${escapeIcsText(event.location)}`,
  ];
  if (event.description) {
    lines.push(`DESCRIPTION:${escapeIcsText(event.description)}`);
  }
  lines.push('END:VEVENT', 'END:VCALENDAR');
  return lines.map(foldLine).join('\r\n') + '\r\n';
}

/**
 * Resolve the event end time from a start + optional duration (minutes,
 * defaulting to 60). Shared by the controller so URL and ICS agree.
 */
export function endFromDuration(start: Date, durationMin: number | null | undefined): Date {
  const minutes = typeof durationMin === 'number' && durationMin > 0 ? durationMin : 60;
  return new Date(start.getTime() + minutes * 60 * 1000);
}
