// Unit tests for FreeBusy interval math + availability endpoint gate.
jest.mock('../src/config/prisma', () => {
  const { mockDeep } = require('jest-mock-extended');
  const m = mockDeep();
  return { __esModule: true, prisma: m, default: m };
});
jest.mock('../src/services/geocodingService', () => ({
  __esModule: true,
  geocodeAddress: jest.fn(),
}));
jest.mock('../src/services/locationService', () => ({
  __esModule: true,
  processMeetingRequest: jest.fn(),
}));
jest.mock('../src/services/emailService', () => ({
  __esModule: true,
  sendMeetingInviteEmail: jest.fn().mockResolvedValue(undefined),
  sendMeetingScheduledEmail: jest.fn().mockResolvedValue(undefined),
  sendPasswordResetEmail: jest.fn().mockResolvedValue(undefined),
}));
jest.mock('../src/services/availabilityService', () => {
  const actual = jest.requireActual('../src/services/availabilityService');
  return {
    __esModule: true,
    ...actual,
    computeMeetingAvailability: jest.fn(),
    fetchBusyIntervals: jest.fn(),
  };
});

import request from 'supertest';
import jwt from 'jsonwebtoken';
import { prismaMock } from './helpers/prismaMock';
import { makeUser, makeMeetingRequest } from './helpers/fixtures';
import {
  mergeIntervals,
  freeIntervals,
  intersectFree,
  generateSlots,
  computeMeetingAvailability,
} from '../src/services/availabilityService';
import app from '../src/server';

function tokenFor(userId: string, email = 'a@example.com'): string {
  return jwt.sign({ sub: userId, email }, 'test-secret', { algorithm: 'HS256' });
}

function completedRequest(overrides = {}) {
  return makeMeetingRequest({
    status: 'COMPLETED' as ReturnType<typeof makeMeetingRequest>['status'],
    selectedPlaceDetails: { name: 'Cafe', address: '1 A St', place_id: 'p1' },
    ...overrides,
  });
}

describe('availability interval helpers', () => {
  it('mergeIntervals coalesces overlaps', () => {
    const a = new Date('2026-07-24T10:00:00.000Z');
    const b = new Date('2026-07-24T11:00:00.000Z');
    const c = new Date('2026-07-24T10:30:00.000Z');
    const d = new Date('2026-07-24T12:00:00.000Z');
    const e = new Date('2026-07-24T14:00:00.000Z');
    const f = new Date('2026-07-24T15:00:00.000Z');
    expect(mergeIntervals([
      { start: a, end: b },
      { start: c, end: d },
      { start: e, end: f },
    ])).toEqual([
      { start: a, end: d },
      { start: e, end: f },
    ]);
  });

  it('freeIntervals subtracts busy from the window', () => {
    const windowStart = new Date('2026-07-24T09:00:00.000Z');
    const windowEnd = new Date('2026-07-24T17:00:00.000Z');
    const busy = [
      { start: new Date('2026-07-24T10:00:00.000Z'), end: new Date('2026-07-24T11:00:00.000Z') },
    ];
    expect(freeIntervals(windowStart, windowEnd, busy)).toEqual([
      { start: windowStart, end: busy[0].start },
      { start: busy[0].end, end: windowEnd },
    ]);
  });

  it('intersectFree keeps only shared open time', () => {
    const a = [
      { start: new Date('2026-07-24T09:00:00.000Z'), end: new Date('2026-07-24T12:00:00.000Z') },
    ];
    const b = [
      { start: new Date('2026-07-24T11:00:00.000Z'), end: new Date('2026-07-24T15:00:00.000Z') },
    ];
    expect(intersectFree(a, b)).toEqual([
      {
        start: new Date('2026-07-24T11:00:00.000Z'),
        end: new Date('2026-07-24T12:00:00.000Z'),
      },
    ]);
  });

  it('generateSlots emits duration-aligned candidates inside free time', () => {
    // Use a local business-hour window so the business-hours filter accepts it.
    const start = new Date();
    start.setHours(10, 0, 0, 0);
    start.setDate(start.getDate() + 1);
    const end = new Date(start);
    end.setHours(13, 0, 0, 0);
    const slots = generateSlots([{ start, end }], { durationMin: 60, stepMin: 60, maxSlots: 5 });
    expect(slots.length).toBeGreaterThan(0);
    for (const slot of slots) {
      const s = new Date(slot.start);
      const e = new Date(slot.end);
      expect(e.getTime() - s.getTime()).toBe(60 * 60 * 1000);
    }
  });
});

describe('GET /api/v1/meeting-requests/:id/availability', () => {
  it('returns computed slots for the owner once the place is locked', async () => {
    prismaMock.user.findUnique.mockResolvedValue(makeUser());
    prismaMock.meetingRequest.findUnique.mockResolvedValue(completedRequest());
    (computeMeetingAvailability as jest.Mock).mockResolvedValue({
      slots: [{ start: '2026-07-24T15:00:00.000Z', end: '2026-07-24T16:00:00.000Z' }],
      my_connected: true,
      their_connected: false,
      partial: true,
      window_start: '2026-07-24T14:00:00.000Z',
      window_end: '2026-07-31T14:00:00.000Z',
    });

    const res = await request(app)
      .get('/api/v1/meeting-requests/req-1/availability')
      .set('Authorization', `Bearer ${tokenFor('user-a-id')}`);

    expect(res.status).toBe(200);
    expect(res.body.slots).toHaveLength(1);
    expect(res.body.partial).toBe(true);
    expect(JSON.stringify(res.body)).not.toContain('address_a');
  });

  it('403 for a caller who is neither owner nor invitee', async () => {
    prismaMock.meetingRequest.findUnique.mockResolvedValue(completedRequest());
    const res = await request(app).get('/api/v1/meeting-requests/req-1/availability');
    expect(res.status).toBe(403);
  });

  it('400 before a place is finalized', async () => {
    prismaMock.user.findUnique.mockResolvedValue(makeUser());
    prismaMock.meetingRequest.findUnique.mockResolvedValue(
      makeMeetingRequest({ status: 'READY' as ReturnType<typeof makeMeetingRequest>['status'] })
    );
    const res = await request(app)
      .get('/api/v1/meeting-requests/req-1/availability')
      .set('Authorization', `Bearer ${tokenFor('user-a-id')}`);
    expect(res.status).toBe(400);
  });
});
