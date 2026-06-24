// Unit tests for the hand-rolled calendar util (Google Calendar URL + ICS).
// Verifies UTC date formatting, RFC 5545 escaping/folding, and that the public
// venue-only `location` is what lands in the event (no coordinates/addresses A/B).
import {
  buildCalendarUrl,
  buildIcs,
  toBasicUtc,
  endFromDuration,
  CalendarEvent,
} from '../src/utils/calendar';

const baseEvent = (overrides: Partial<CalendarEvent> = {}): CalendarEvent => ({
  requestId: 'req-1',
  title: 'Meeting at Blue Bottle',
  location: 'Blue Bottle, 1 Main St, San Francisco, CA',
  description: 'Scheduled via Find A Meeting Spot.',
  start: new Date('2026-07-01T17:30:00.000Z'),
  end: new Date('2026-07-01T18:30:00.000Z'),
  ...overrides,
});

describe('toBasicUtc', () => {
  it('formats a Date as YYYYMMDDTHHMMSSZ (UTC basic)', () => {
    expect(toBasicUtc(new Date('2026-07-01T17:30:00.000Z'))).toBe('20260701T173000Z');
  });

  it('drops milliseconds', () => {
    expect(toBasicUtc(new Date('2026-12-31T23:59:59.999Z'))).toBe('20261231T235959Z');
  });
});

describe('endFromDuration', () => {
  it('defaults to 60 minutes when duration is null/undefined/invalid', () => {
    const start = new Date('2026-07-01T17:00:00.000Z');
    expect(endFromDuration(start, null).toISOString()).toBe('2026-07-01T18:00:00.000Z');
    expect(endFromDuration(start, undefined).toISOString()).toBe('2026-07-01T18:00:00.000Z');
    expect(endFromDuration(start, 0).toISOString()).toBe('2026-07-01T18:00:00.000Z');
  });

  it('adds the provided minutes', () => {
    const start = new Date('2026-07-01T17:00:00.000Z');
    expect(endFromDuration(start, 90).toISOString()).toBe('2026-07-01T18:30:00.000Z');
  });
});

describe('buildCalendarUrl', () => {
  it('builds a Google Calendar TEMPLATE url with a UTC basic date range', () => {
    const url = buildCalendarUrl(baseEvent());
    expect(url.startsWith('https://calendar.google.com/calendar/render?')).toBe(true);
    const params = new URL(url).searchParams;
    expect(params.get('action')).toBe('TEMPLATE');
    expect(params.get('text')).toBe('Meeting at Blue Bottle');
    expect(params.get('dates')).toBe('20260701T173000Z/20260701T183000Z');
    expect(params.get('location')).toBe('Blue Bottle, 1 Main St, San Francisco, CA');
    expect(params.get('details')).toBe('Scheduled via Find A Meeting Spot.');
  });

  it('omits details when no description is given', () => {
    const url = buildCalendarUrl(baseEvent({ description: undefined }));
    expect(new URL(url).searchParams.has('details')).toBe(false);
  });
});

describe('buildIcs', () => {
  it('emits a single VEVENT with the required properties and CRLF lines', () => {
    const ics = buildIcs(baseEvent());
    expect(ics).toContain('\r\n');
    expect(ics.startsWith('BEGIN:VCALENDAR\r\n')).toBe(true);
    expect(ics).toContain('VERSION:2.0');
    expect(ics).toContain('PRODID:-//Find A Meeting Spot//Scheduling//EN');
    expect(ics).toContain('BEGIN:VEVENT');
    expect(ics).toContain('UID:req-1@findameetingspot.com');
    expect(ics).toContain('DTSTAMP:');
    expect(ics).toContain('DTSTART:20260701T173000Z');
    expect(ics).toContain('DTEND:20260701T183000Z');
    expect(ics).toContain('SUMMARY:Meeting at Blue Bottle');
    expect(ics).toContain('END:VEVENT');
    expect(ics.trimEnd().endsWith('END:VCALENDAR')).toBe(true);
  });

  it('escapes commas/semicolons/backslashes/newlines per RFC 5545', () => {
    const ics = buildIcs(
      baseEvent({
        title: 'Lunch; coffee, tea \\ more',
        location: 'Cafe, 5 A St',
        description: 'line1\nline2',
      })
    );
    expect(ics).toContain('SUMMARY:Lunch\\; coffee\\, tea \\\\ more');
    expect(ics).toContain('LOCATION:Cafe\\, 5 A St');
    expect(ics).toContain('DESCRIPTION:line1\\nline2');
  });

  it('folds content lines longer than 75 octets with a leading space', () => {
    const longTitle = 'A'.repeat(200);
    const ics = buildIcs(baseEvent({ title: longTitle }));
    const lines = ics.split('\r\n');
    // Every physical line must be <= 75 octets.
    for (const line of lines) {
      expect(Buffer.byteLength(line, 'utf8')).toBeLessThanOrEqual(75);
    }
    // Continuation lines begin with a single space.
    const summaryIdx = lines.findIndex((l) => l.startsWith('SUMMARY:'));
    expect(summaryIdx).toBeGreaterThanOrEqual(0);
    expect(lines[summaryIdx + 1].startsWith(' ')).toBe(true);
  });

  it('uses only the public venue location (no coordinates/home address)', () => {
    const ics = buildIcs(baseEvent());
    expect(ics).toContain('LOCATION:Blue Bottle\\, 1 Main St\\, San Francisco\\, CA');
    // Sanity: no lat/lng leak from a caller mistake — the event has none here.
    expect(ics).not.toMatch(/lat|lng|location_a|location_b/);
  });
});
