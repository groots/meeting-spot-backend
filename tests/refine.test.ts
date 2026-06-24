// Phase 2b tests: the owner-only POST /:id/refine endpoint and the
// applyRefinedOptions stale-choice sweep.
//
// Security/behavior contract:
//   * owner-only (Bearer); a non-owner authed user → 403, no auth → 401.
//   * allowed only while status === 'ready'; blocked once a place/time is locked.
//   * premium (softPremiumGate) toggles the fairness re-rank flag passed to
//     processMeetingRequest; non-premium still refines (distance ranking).
//   * choices that fall out of the new option set are cleared.
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
import { Prisma } from '@prisma/client';
import { prismaMock } from './helpers/prismaMock';
import { makeUser, makeMeetingRequest, makeSubscription } from './helpers/fixtures';
import { processMeetingRequest } from '../src/services/locationService';
import { applyRefinedOptions } from '../src/services/meetingRequestService';
import app from '../src/server';

const mockProcess = processMeetingRequest as jest.Mock;

function tokenFor(userId: string, email = 'a@example.com'): string {
  return jwt.sign({ sub: userId, email }, 'test-secret', { algorithm: 'HS256' });
}

const OPT_A = { name: 'Cafe A', address: '1 A St', place_id: 'pA' };
const OPT_B = { name: 'Cafe B', address: '2 B St', place_id: 'pB' };

// A READY request with two suggestions (the refine precondition).
function readyRequest(overrides = {}) {
  return makeMeetingRequest({
    status: 'READY' as ReturnType<typeof makeMeetingRequest>['status'],
    addressBLat: 37.1,
    addressBLon: -122.1,
    suggestedOptions: [OPT_A, OPT_B] as unknown as ReturnType<
      typeof makeMeetingRequest
    >['suggestedOptions'],
    ...overrides,
  });
}

describe('POST /api/v1/meeting-requests/:id/refine', () => {
  it('owner refines while ready (200) and persists new options', async () => {
    const req = readyRequest();
    prismaMock.user.findUnique.mockResolvedValue(makeUser());
    prismaMock.meetingRequest.findUnique.mockResolvedValue(req);
    prismaMock.subscription.findMany.mockResolvedValue([]); // non-premium
    mockProcess.mockResolvedValue({
      success: true,
      status: 'completed',
      suggestedOptions: [OPT_B],
    });
    prismaMock.meetingRequest.update.mockImplementation(((args: any) =>
      Promise.resolve({ ...req, ...args.data })) as any);

    const res = await request(app)
      .post('/api/v1/meeting-requests/req-1/refine')
      .set('Authorization', `Bearer ${tokenFor('user-a-id')}`)
      .send({ open_now: true, location_type: 'Cafe' });

    expect(res.status).toBe(200);
    expect(res.body.suggested_options).toEqual([OPT_B]);
    // Non-premium → fairness flag is false.
    expect(mockProcess).toHaveBeenCalledWith(
      expect.objectContaining({ isPremium: false, openNow: true, locationType: 'Cafe' })
    );
  });

  it('premium owner passes the fairness flag through', async () => {
    const req = readyRequest();
    prismaMock.user.findUnique.mockResolvedValue(makeUser());
    prismaMock.meetingRequest.findUnique.mockResolvedValue(req);
    prismaMock.subscription.findMany.mockResolvedValue([makeSubscription()]);
    mockProcess.mockResolvedValue({
      success: true,
      status: 'completed',
      suggestedOptions: [OPT_A],
    });
    prismaMock.meetingRequest.update.mockImplementation(((args: any) =>
      Promise.resolve({ ...req, ...args.data })) as any);

    const res = await request(app)
      .post('/api/v1/meeting-requests/req-1/refine')
      .set('Authorization', `Bearer ${tokenFor('user-a-id')}`)
      .send({});

    expect(res.status).toBe(200);
    expect(mockProcess).toHaveBeenCalledWith(expect.objectContaining({ isPremium: true }));
  });

  it('rejects an unauthenticated caller (401)', async () => {
    const res = await request(app).post('/api/v1/meeting-requests/req-1/refine').send({});
    expect(res.status).toBe(401);
  });

  it('rejects a non-owner authenticated user (403)', async () => {
    prismaMock.user.findUnique.mockResolvedValue(makeUser({ id: 'someone-else' }));
    prismaMock.meetingRequest.findUnique.mockResolvedValue(readyRequest());
    prismaMock.subscription.findMany.mockResolvedValue([]);

    const res = await request(app)
      .post('/api/v1/meeting-requests/req-1/refine')
      .set('Authorization', `Bearer ${tokenFor('someone-else')}`)
      .send({});

    expect(res.status).toBe(403);
  });

  it('blocks refine unless status is ready (400)', async () => {
    prismaMock.user.findUnique.mockResolvedValue(makeUser());
    prismaMock.meetingRequest.findUnique.mockResolvedValue(
      readyRequest({ status: 'COMPLETED' as ReturnType<typeof makeMeetingRequest>['status'] })
    );
    prismaMock.subscription.findMany.mockResolvedValue([]);

    const res = await request(app)
      .post('/api/v1/meeting-requests/req-1/refine')
      .set('Authorization', `Bearer ${tokenFor('user-a-id')}`)
      .send({});

    expect(res.status).toBe(400);
    expect(mockProcess).not.toHaveBeenCalled();
  });

  it('blocks refine once a place is finalized (400)', async () => {
    prismaMock.user.findUnique.mockResolvedValue(makeUser());
    prismaMock.meetingRequest.findUnique.mockResolvedValue(
      readyRequest({ selectedPlaceDetails: OPT_A as unknown as object })
    );
    prismaMock.subscription.findMany.mockResolvedValue([]);

    const res = await request(app)
      .post('/api/v1/meeting-requests/req-1/refine')
      .set('Authorization', `Bearer ${tokenFor('user-a-id')}`)
      .send({});

    expect(res.status).toBe(400);
  });

  it('400s when the refined search finds nothing', async () => {
    const req = readyRequest();
    prismaMock.user.findUnique.mockResolvedValue(makeUser());
    prismaMock.meetingRequest.findUnique.mockResolvedValue(req);
    prismaMock.subscription.findMany.mockResolvedValue([]);
    mockProcess.mockResolvedValue({ success: false, status: 'failed', suggestedOptions: null });

    const res = await request(app)
      .post('/api/v1/meeting-requests/req-1/refine')
      .set('Authorization', `Bearer ${tokenFor('user-a-id')}`)
      .send({ radius: 10000 });

    expect(res.status).toBe(400);
  });
});

describe('applyRefinedOptions (stale-choice sweep)', () => {
  it('clears a recorded choice that is no longer in the new options', async () => {
    const req = makeMeetingRequest({
      status: 'READY' as ReturnType<typeof makeMeetingRequest>['status'],
      userBChoice: OPT_A as unknown as ReturnType<typeof makeMeetingRequest>['userBChoice'],
    });
    let captured: any = null;
    prismaMock.meetingRequest.update.mockImplementation(((args: any) => {
      captured = args.data;
      return Promise.resolve({ ...req, ...args.data });
    }) as any);

    // New options drop OPT_A (B's pick) — it must be cleared.
    await applyRefinedOptions(req, [OPT_B]);
    expect(captured.userBChoice).toBe(Prisma.JsonNull);
  });

  it('retains a choice that is still present in the new options', async () => {
    const req = makeMeetingRequest({
      status: 'READY' as ReturnType<typeof makeMeetingRequest>['status'],
      userBChoice: OPT_B as unknown as ReturnType<typeof makeMeetingRequest>['userBChoice'],
    });
    let captured: any = null;
    prismaMock.meetingRequest.update.mockImplementation(((args: any) => {
      captured = args.data;
      return Promise.resolve({ ...req, ...args.data });
    }) as any);

    await applyRefinedOptions(req, [OPT_A, OPT_B]);
    expect(captured.userBChoice).toBeUndefined(); // not touched → retained
  });
});
