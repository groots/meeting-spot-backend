// Unit tests for the time-of-day opening-hours matcher. Windows:
//   morning 06:00–11:59, afternoon 12:00–16:59, evening 17:00–22:59.
import { isOpenDuringTimeOfDay, parseTimeOfDay } from '../src/utils/openingHours';
import type { GoogleOpeningPeriod } from '../src/services/placesClient';

const p = (openTime: string, closeTime?: string, openDay = 1, closeDay = 1): GoogleOpeningPeriod =>
  closeTime === undefined
    ? { open: { day: openDay, time: openTime } }
    : { open: { day: openDay, time: openTime }, close: { day: closeDay, time: closeTime } };

describe('parseTimeOfDay', () => {
  it('accepts the three windows (case-insensitive, trimmed)', () => {
    expect(parseTimeOfDay('morning')).toBe('morning');
    expect(parseTimeOfDay(' Afternoon ')).toBe('afternoon');
    expect(parseTimeOfDay('EVENING')).toBe('evening');
  });
  it('rejects anything else', () => {
    expect(parseTimeOfDay('')).toBeNull();
    expect(parseTimeOfDay('night')).toBeNull();
    expect(parseTimeOfDay(null)).toBeNull();
    expect(parseTimeOfDay(42)).toBeNull();
  });
});

describe('isOpenDuringTimeOfDay — normal periods', () => {
  it('a 07:00–11:00 cafe matches morning only', () => {
    const periods = [p('0700', '1100')];
    expect(isOpenDuringTimeOfDay(periods, 'morning')).toBe(true);
    expect(isOpenDuringTimeOfDay(periods, 'afternoon')).toBe(false);
    expect(isOpenDuringTimeOfDay(periods, 'evening')).toBe(false);
  });

  it('a 17:00–22:00 dinner spot matches evening only', () => {
    const periods = [p('1700', '2200')];
    expect(isOpenDuringTimeOfDay(periods, 'morning')).toBe(false);
    expect(isOpenDuringTimeOfDay(periods, 'afternoon')).toBe(false);
    expect(isOpenDuringTimeOfDay(periods, 'evening')).toBe(true);
  });

  it('an 11:00–15:00 lunch spot matches morning and afternoon', () => {
    const periods = [p('1100', '1500')];
    expect(isOpenDuringTimeOfDay(periods, 'morning')).toBe(true);
    expect(isOpenDuringTimeOfDay(periods, 'afternoon')).toBe(true);
    expect(isOpenDuringTimeOfDay(periods, 'evening')).toBe(false);
  });

  it('a place closing exactly at the window start does not match that window', () => {
    // Closes at 12:00 → not "open" during the afternoon window (starts 12:00).
    const periods = [p('0800', '1200')];
    expect(isOpenDuringTimeOfDay(periods, 'afternoon')).toBe(false);
    expect(isOpenDuringTimeOfDay(periods, 'morning')).toBe(true);
  });
});

describe('isOpenDuringTimeOfDay — 24-hour periods', () => {
  it('open with no close matches every window', () => {
    const periods = [p('0000')];
    expect(isOpenDuringTimeOfDay(periods, 'morning')).toBe(true);
    expect(isOpenDuringTimeOfDay(periods, 'afternoon')).toBe(true);
    expect(isOpenDuringTimeOfDay(periods, 'evening')).toBe(true);
  });
});

describe('isOpenDuringTimeOfDay — overnight periods', () => {
  it('a 20:00–02:00 bar matches evening (pre-midnight portion)', () => {
    const periods = [p('2000', '0200', 1, 2)];
    expect(isOpenDuringTimeOfDay(periods, 'evening')).toBe(true);
    expect(isOpenDuringTimeOfDay(periods, 'afternoon')).toBe(false);
  });

  it('a 22:00–08:00 diner matches morning (post-midnight portion)', () => {
    const periods = [p('2200', '0800', 1, 2)];
    expect(isOpenDuringTimeOfDay(periods, 'morning')).toBe(true);
    expect(isOpenDuringTimeOfDay(periods, 'evening')).toBe(true);
    // 02:00–08:00 morning portion doesn't reach the afternoon window.
    expect(isOpenDuringTimeOfDay(periods, 'afternoon')).toBe(false);
  });
});

describe('isOpenDuringTimeOfDay — closed / empty', () => {
  it('returns false for no periods', () => {
    expect(isOpenDuringTimeOfDay([], 'morning')).toBe(false);
    expect(isOpenDuringTimeOfDay(null, 'morning')).toBe(false);
    expect(isOpenDuringTimeOfDay(undefined, 'evening')).toBe(false);
  });

  it('multiple periods across days: a Monday-morning-only place still matches morning', () => {
    const periods = [p('0700', '1100', 1, 1), p('0700', '1100', 3, 3)];
    expect(isOpenDuringTimeOfDay(periods, 'morning')).toBe(true);
    expect(isOpenDuringTimeOfDay(periods, 'evening')).toBe(false);
  });
});
