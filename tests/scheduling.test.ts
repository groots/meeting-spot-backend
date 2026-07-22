// Phase 1 scheduling tests: pure helpers (timeKey/choicesAgree/isValidFutureTime/
// recordTimeChoice) + the /schedule and /calendar controller endpoints.
//
// Security contract mirrored from place selection:
//   * /schedule is owner-or-tokenB; OWNER mode keeps the invitee read-only (403).
//   * time selection only after the place is locked (completed + selectedPlace).
//   * a finalized meeting_time can't be re-proposed.
//   * time DTOs never carry coordinates/token/contact.
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

import request from 'supertest';
import jwt from 'jsonwebtoken';
import { prismaMock } from './helpers/prismaMock';
import { makeUser, makeMeetingRequest } from './helpers/fixtures';
import {
  timeKey,
  choicesAgree,
  isValidFutureTime,
  recordTimeChoice,
} from '../src/services/meetingRequestService';
import { sendMeetingScheduledEmail } from '../src/services/emailService';
import { encryptContact } from '../src/utils/encryption';
import app from '../src/server';

function tokenFor(userId: string, email = 'a@example.com'): string {
  return jwt.sign({ sub: userId, email }, 'test-secret', { algorithm: 'HS256' });
}

// A request whose place is already locked (the precondition for scheduling).
function completedRequest(overrides = {}) {
  return makeMeetingRequest({
    status: 'COMPLETED' as ReturnType<typeof makeMeetingRequest>['status'],
    selectedPlaceDetails: { name: 'Cafe', address: '1 A St', place_id: 'p1' },
    ...overrides,
  });
}

// Minute-aligned so "same minute" comparisons are deterministic (not flaky on
// the current second).
const FUTURE = new Date(Math.floor((Date.now() + 7 * 24 * 60 * 60 * 1000) / 60000) * 60000);
const FUTURE_ISO = FUTURE.toISOString();

describe('scheduling pure helpers', () => {
  describe('timeKey', () => {
    it('floors to the minute and is stable across sub-minute differences', () => {
      const a = timeKey(new Date('2026-07-01T17:30:15.000Z'));
      const b = timeKey(new Date('2026-07-01T17:30:59.999Z'));
      expect(a).toBe(b);
      expect(a).toBe('2026-07-01T17:30:00.000Z');
    });
    it('returns "" for null/invalid', () => {
      expect(timeKey(null)).toBe('');
      expect(timeKey(new Date('nope'))).toBe('');
    });
  });

  describe('choicesAgree', () => {
    it('true only when all keys present and identical', () => {
      expect(choicesAgree(['k', 'k'])).toBe(true);
      expect(choicesAgree(['k', 'j'])).toBe(false);
      expect(choicesAgree(['', 'k'])).toBe(false);
      expect(choicesAgree([])).toBe(false);
    });
  });

  describe('isValidFutureTime', () => {
    it('accepts a bounded future time', () => {
      expect(isValidFutureTime(FUTURE)).toBe(true);
    });
    it('rejects past, invalid, and >1yr out', () => {
      expect(isValidFutureTime(new Date(Date.now() - 1000))).toBe(false);
      expect(isValidFutureTime(new Date('nope'))).toBe(false);
      expect(isValidFutureTime(new Date(Date.now() + 400 * 24 * 60 * 60 * 1000))).toBe(false);
    });
  });

  describe('recordTimeChoice', () => {
    it('OWNER mode sets meeting_time immediately', async () => {
      const req = completedRequest({ selectionMode: 'OWNER' });
      prismaMock.meetingRequest.update.mockImplementation(((args: any) =>
        Promise.resolve({ ...req, ...args.data })) as any);
      const updated = await recordTimeChoice(req, 'A', FUTURE);
      expect(updated.meetingTime).toEqual(FUTURE);
    });

    it('MUTUAL mode stores the proposal but does not lock on mismatch', async () => {
      const other = new Date(Date.now() + 8 * 24 * 60 * 60 * 1000);
      const req = completedRequest({ selectionMode: 'MUTUAL', userBTimeChoice: other });
      prismaMock.meetingRequest.update.mockImplementation(((args: any) =>
        Promise.resolve({ ...req, ...args.data })) as any);
      const updated = await recordTimeChoice(req, 'A', FUTURE);
      expect(updated.userATimeChoice).toEqual(FUTURE);
      expect(updated.meetingTime ?? null).toBeNull();
    });

    it('MUTUAL mode locks meeting_time when the other party already matches', async () => {
      const other = new Date(FUTURE.getTime() + 20 * 1000); // same minute
      const req = completedRequest({ selectionMode: 'MUTUAL', userBTimeChoice: other });
      prismaMock.meetingRequest.update.mockImplementation(((args: any) =>
        Promise.resolve({ ...req, ...args.data })) as any);
      const updated = await recordTimeChoice(req, 'A', FUTURE);
      expect(updated.meetingTime).toEqual(FUTURE);
    });
  });
});

describe('POST /api/v1/meeting-requests/:id/schedule', () => {
  it('OWNER mode: owner sets the time (200) with no leaked fields', async () => {
    prismaMock.user.findUnique.mockResolvedValue(makeUser());
    const req = completedRequest({ selectionMode: 'OWNER' });
    prismaMock.meetingRequest.findUnique.mockResolvedValue(req);
    prismaMock.meetingRequest.update.mockResolvedValue(
      completedRequest({ selectionMode: 'OWNER', meetingTime: FUTURE })
    );

    const res = await request(app)
      .post('/api/v1/meeting-requests/req-1/schedule')
      .set('Authorization', `Bearer ${tokenFor('user-a-id')}`)
      .send({ meeting_time: FUTURE_ISO });

    expect(res.status).toBe(200);
    expect(res.body.meeting_time).toBe(FUTURE.toISOString());
    const str = JSON.stringify(res.body);
    for (const k of ['address_a_lat', 'address_a_lon', 'token_b', 'user_b_contact', 'location_a']) {
      expect(str).not.toContain(k);
    }
  });

  it('OWNER mode: invitee (token) is read-only → 403', async () => {
    const req = completedRequest({ selectionMode: 'OWNER' });
    prismaMock.meetingRequest.findUnique.mockResolvedValue(req);

    const res = await request(app)
      .post('/api/v1/meeting-requests/req-1/schedule')
      .send({ token: 'valid-token-b', meeting_time: FUTURE_ISO });

    expect(res.status).toBe(403);
  });

  it('MUTUAL mode: invitee (token) may propose; stays pending until agreement', async () => {
    const req = completedRequest({ selectionMode: 'MUTUAL' });
    prismaMock.meetingRequest.findUnique.mockResolvedValue(req);
    prismaMock.meetingRequest.update.mockResolvedValue(
      completedRequest({ selectionMode: 'MUTUAL', userBTimeChoice: FUTURE })
    );

    const res = await request(app)
      .post('/api/v1/meeting-requests/req-1/schedule')
      .send({ token: 'valid-token-b', meeting_time: FUTURE_ISO });

    expect(res.status).toBe(200);
    expect(res.body.user_b_time_choice).toBe(FUTURE.toISOString());
    expect(res.body.meeting_time).toBeNull();
    expect(sendMeetingScheduledEmail).not.toHaveBeenCalled();
  });

  it('MUTUAL mode: agreeing on a time locks it and emails both parties', async () => {
    const inviteeEmail = 'bob@example.com';
    const req = completedRequest({
      selectionMode: 'MUTUAL',
      userATimeChoice: FUTURE,
      userBContactEncrypted: encryptContact(inviteeEmail),
    });
    prismaMock.user.findUnique.mockResolvedValue(makeUser());
    prismaMock.meetingRequest.findUnique.mockResolvedValue(req);
    const locked = completedRequest({
      selectionMode: 'MUTUAL',
      userATimeChoice: FUTURE,
      userBTimeChoice: FUTURE,
      meetingTime: FUTURE,
      userBContactEncrypted: req.userBContactEncrypted,
    });
    prismaMock.meetingRequest.update.mockResolvedValue(locked);

    const res = await request(app)
      .post('/api/v1/meeting-requests/req-1/schedule')
      .send({ token: 'valid-token-b', meeting_time: FUTURE_ISO });

    expect(res.status).toBe(200);
    expect(res.body.meeting_time).toBe(FUTURE.toISOString());
    expect(sendMeetingScheduledEmail).toHaveBeenCalledTimes(2);
    const recipients = (sendMeetingScheduledEmail as jest.Mock).mock.calls.map((c) => c[0]);
    expect(recipients).toEqual(expect.arrayContaining(['a@example.com', inviteeEmail]));
    for (const call of (sendMeetingScheduledEmail as jest.Mock).mock.calls) {
      expect(call[4]).toContain('calendar.google.com');
    }
  });

  it('blocks scheduling before the place is finalized (400)', async () => {
    prismaMock.user.findUnique.mockResolvedValue(makeUser());
    prismaMock.meetingRequest.findUnique.mockResolvedValue(
      makeMeetingRequest({ status: 'READY' as ReturnType<typeof makeMeetingRequest>['status'] })
    );

    const res = await request(app)
      .post('/api/v1/meeting-requests/req-1/schedule')
      .set('Authorization', `Bearer ${tokenFor('user-a-id')}`)
      .send({ meeting_time: FUTURE_ISO });

    expect(res.status).toBe(400);
  });

  it('rejects a double-set once meeting_time exists (400)', async () => {
    prismaMock.user.findUnique.mockResolvedValue(makeUser());
    prismaMock.meetingRequest.findUnique.mockResolvedValue(
      completedRequest({ selectionMode: 'OWNER', meetingTime: FUTURE })
    );

    const res = await request(app)
      .post('/api/v1/meeting-requests/req-1/schedule')
      .set('Authorization', `Bearer ${tokenFor('user-a-id')}`)
      .send({ meeting_time: FUTURE_ISO });

    expect(res.status).toBe(400);
  });

  it('rejects a past meeting_time (400)', async () => {
    prismaMock.user.findUnique.mockResolvedValue(makeUser());
    prismaMock.meetingRequest.findUnique.mockResolvedValue(
      completedRequest({ selectionMode: 'OWNER' })
    );

    const res = await request(app)
      .post('/api/v1/meeting-requests/req-1/schedule')
      .set('Authorization', `Bearer ${tokenFor('user-a-id')}`)
      .send({ meeting_time: new Date(Date.now() - 1000).toISOString() });

    expect(res.status).toBe(400);
  });
});

describe('GET /api/v1/meeting-requests/:id/calendar', () => {
  it('returns google_url + ics once the time is finalized (no coord leak)', async () => {
    prismaMock.user.findUnique.mockResolvedValue(makeUser());
    prismaMock.meetingRequest.findUnique.mockResolvedValue(
      completedRequest({ selectionMode: 'OWNER', meetingTime: FUTURE })
    );

    const res = await request(app)
      .get('/api/v1/meeting-requests/req-1/calendar')
      .set('Authorization', `Bearer ${tokenFor('user-a-id')}`);

    expect(res.status).toBe(200);
    expect(typeof res.body.google_url).toBe('string');
    expect(res.body.ics).toContain('BEGIN:VEVENT');
    const str = JSON.stringify(res.body);
    expect(str).not.toContain('address_a');
    expect(str).not.toContain('location_a');
  });

  it('400 before a time is finalized', async () => {
    prismaMock.user.findUnique.mockResolvedValue(makeUser());
    prismaMock.meetingRequest.findUnique.mockResolvedValue(
      completedRequest({ selectionMode: 'OWNER' })
    );

    const res = await request(app)
      .get('/api/v1/meeting-requests/req-1/calendar')
      .set('Authorization', `Bearer ${tokenFor('user-a-id')}`);

    expect(res.status).toBe(400);
  });

  it('403 for a caller who is neither owner nor invitee', async () => {
    prismaMock.meetingRequest.findUnique.mockResolvedValue(
      completedRequest({ selectionMode: 'OWNER', meetingTime: FUTURE })
    );
    const res = await request(app).get('/api/v1/meeting-requests/req-1/calendar');
    expect(res.status).toBe(403);
  });
});
