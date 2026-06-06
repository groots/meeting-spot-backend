// Meeting-request tests — including the CRITICAL coordinate-leak assertions.
//
// The security contract under test:
//   * POST /:id/respond returns EXACTLY { request_id, status } and never any
//     of address_a coords, token_b, user_b_contact_encrypted, user_a_id,
//     session_identifier_a, or location_a.
//   * GET /:id/results is owner-only (401 unauth, 403 non-owner) and exposes
//     only { request_id, status, suggested_options, selected_place }.
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
  sendPasswordResetEmail: jest.fn().mockResolvedValue(undefined),
}));

import request from 'supertest';
import jwt from 'jsonwebtoken';
import { prismaMock } from './helpers/prismaMock';
import { makeUser, makeMeetingRequest } from './helpers/fixtures';
import { geocodeAddress } from '../src/services/geocodingService';
import { processMeetingRequest } from '../src/services/locationService';
import app from '../src/server';

const mockGeocode = geocodeAddress as jest.Mock;
const mockProcess = processMeetingRequest as jest.Mock;

function tokenFor(userId: string, email = 'a@example.com'): string {
  return jwt.sign({ sub: userId, email }, 'test-secret', { algorithm: 'HS256' });
}

// Sensitive material that must NEVER appear in /respond or /results responses.
const SENSITIVE_VALUES = [
  'valid-token-b', // tokenB
  'session-a-secret', // sessionIdentifierA
  'encrypted-placeholder', // userBContactEncrypted
  '37.7749', // addressALat
  '-122.4194', // addressALon
];
const SENSITIVE_KEYS = [
  'address_a_lat',
  'address_a_lon',
  'token_b',
  'tokenB',
  'user_b_contact_encrypted',
  'user_a_id',
  'session_identifier_a',
  'location_a',
];

function assertNoSensitive(body: unknown): void {
  const str = JSON.stringify(body);
  for (const v of SENSITIVE_VALUES) {
    expect(str).not.toContain(v);
  }
  for (const k of SENSITIVE_KEYS) {
    expect(str).not.toContain(k);
  }
}

describe('Meeting Requests API', () => {
  describe('POST /api/v1/meeting-requests (create)', () => {
    it('geocodes address_a and returns a minimal created DTO (201)', async () => {
      prismaMock.user.findUnique.mockResolvedValue(makeUser()); // authenticate
      mockGeocode.mockResolvedValue({
        success: true,
        lat: 37.7749,
        lng: -122.4194,
        formatted_address: '1 A St, San Francisco, CA',
        quality: 'high',
        coordinates: { lat: 37.7749, lng: -122.4194 },
      });
      prismaMock.meetingRequest.create.mockResolvedValue(makeMeetingRequest());

      const res = await request(app)
        .post('/api/v1/meeting-requests')
        .set('Authorization', `Bearer ${tokenFor('user-a-id')}`)
        .send({
          address_a: '1 A St',
          location_type: 'Food & Drink',
          user_b_contact_type: 'email',
          user_b_contact: 'bob@example.com',
        });

      expect(res.status).toBe(201);
      expect(mockGeocode).toHaveBeenCalledWith('1 A St');
      expect(res.body).toMatchObject({
        request_id: 'req-1',
        status: 'pending_b_address',
        user_b_contact_type: 'email',
      });
      assertNoSensitive(res.body);
    });

    it('rejects missing fields with 400', async () => {
      prismaMock.user.findUnique.mockResolvedValue(makeUser());
      const res = await request(app)
        .post('/api/v1/meeting-requests')
        .set('Authorization', `Bearer ${tokenFor('user-a-id')}`)
        .send({ address_a: '1 A St' });
      expect(res.status).toBe(400);
    });

    it('requires authentication (401)', async () => {
      const res = await request(app)
        .post('/api/v1/meeting-requests')
        .send({ address_a: '1 A St' });
      expect(res.status).toBe(401);
    });
  });

  describe('POST /api/v1/meeting-requests/:id/respond (token-gated)', () => {
    it('CRITICAL: returns EXACTLY {request_id,status} with no leaked fields', async () => {
      const pending = makeMeetingRequest();
      const completed = makeMeetingRequest({
        status: 'COMPLETED' as ReturnType<typeof makeMeetingRequest>['status'],
        addressBLat: 40.0,
        addressBLon: -120.0,
        suggestedOptions: [
          { name: 'Cafe', place_id: 'p1', location: { lat: 39, lng: -121 } },
        ],
      });
      // findById is called twice: initial lookup, then the "fresh" re-read.
      prismaMock.meetingRequest.findUnique
        .mockResolvedValueOnce(pending)
        .mockResolvedValueOnce(completed);
      prismaMock.meetingRequest.update.mockResolvedValue(completed);
      mockProcess.mockResolvedValue({
        success: true,
        suggestedOptions: completed.suggestedOptions,
        status: 'completed',
      });

      const res = await request(app)
        .post('/api/v1/meeting-requests/req-1/respond')
        .send({ token: 'valid-token-b', address_b_lat: 40.0, address_b_lon: -120.0 });

      expect(res.status).toBe(200);
      // Exactly two keys, nothing else.
      expect(Object.keys(res.body).sort()).toEqual(['request_id', 'status']);
      expect(res.body).toEqual({ request_id: 'req-1', status: 'completed' });
      assertNoSensitive(res.body);
    });

    it('returns 400 when required fields are missing', async () => {
      const res = await request(app)
        .post('/api/v1/meeting-requests/req-1/respond')
        .send({ token: 'valid-token-b' });
      expect(res.status).toBe(400);
    });

    it('returns 404 when the request does not exist', async () => {
      prismaMock.meetingRequest.findUnique.mockResolvedValue(null);
      const res = await request(app)
        .post('/api/v1/meeting-requests/missing/respond')
        .send({ token: 'x', address_b_lat: 1, address_b_lon: 2 });
      expect(res.status).toBe(404);
    });

    it('returns 403 for an invalid token', async () => {
      prismaMock.meetingRequest.findUnique.mockResolvedValue(makeMeetingRequest());
      const res = await request(app)
        .post('/api/v1/meeting-requests/req-1/respond')
        .send({ token: 'wrong-token', address_b_lat: 1, address_b_lon: 2 });
      expect(res.status).toBe(403);
    });

    it('returns 403 for an expired request', async () => {
      prismaMock.meetingRequest.findUnique.mockResolvedValue(
        makeMeetingRequest({ expiresAt: new Date(Date.now() - 1000) })
      );
      const res = await request(app)
        .post('/api/v1/meeting-requests/req-1/respond')
        .send({ token: 'valid-token-b', address_b_lat: 1, address_b_lon: 2 });
      expect(res.status).toBe(403);
    });

    it('still returns only {request_id,status} when processing fails', async () => {
      const errSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
      const pending = makeMeetingRequest();
      const failed = makeMeetingRequest({
        status: 'FAILED' as ReturnType<typeof makeMeetingRequest>['status'],
      });
      prismaMock.meetingRequest.findUnique
        .mockResolvedValueOnce(pending)
        .mockResolvedValueOnce(failed);
      prismaMock.meetingRequest.update.mockResolvedValue(failed);
      mockProcess.mockRejectedValue(new Error('places down'));

      const res = await request(app)
        .post('/api/v1/meeting-requests/req-1/respond')
        .send({ token: 'valid-token-b', address_b_lat: 40, address_b_lon: -120 });

      expect(res.status).toBe(200);
      expect(Object.keys(res.body).sort()).toEqual(['request_id', 'status']);
      expect(res.body.status).toBe('failed');
      assertNoSensitive(res.body);
      errSpy.mockRestore();
    });
  });

  describe('GET /api/v1/meeting-requests/:id/results (owner-only)', () => {
    it('returns 401 without authentication', async () => {
      const res = await request(app).get('/api/v1/meeting-requests/req-1/results');
      expect(res.status).toBe(401);
    });

    it('returns 403 for a non-owner', async () => {
      // authenticate resolves the *caller* (a different user).
      prismaMock.user.findUnique.mockResolvedValue(
        makeUser({ id: 'intruder-id', email: 'intruder@example.com' })
      );
      prismaMock.meetingRequest.findUnique.mockResolvedValue(
        makeMeetingRequest({ userAId: 'user-a-id' })
      );

      const res = await request(app)
        .get('/api/v1/meeting-requests/req-1/results')
        .set('Authorization', `Bearer ${tokenFor('intruder-id', 'intruder@example.com')}`);

      expect(res.status).toBe(403);
    });

    it('returns 404 when the request is missing', async () => {
      prismaMock.user.findUnique.mockResolvedValue(makeUser());
      prismaMock.meetingRequest.findUnique.mockResolvedValue(null);
      const res = await request(app)
        .get('/api/v1/meeting-requests/req-1/results')
        .set('Authorization', `Bearer ${tokenFor('user-a-id')}`);
      expect(res.status).toBe(404);
    });

    it('owner gets only {request_id,status,suggested_options,selected_place}', async () => {
      prismaMock.user.findUnique.mockResolvedValue(makeUser());
      prismaMock.meetingRequest.findUnique.mockResolvedValue(
        makeMeetingRequest({
          status: 'COMPLETED' as ReturnType<typeof makeMeetingRequest>['status'],
          suggestedOptions: [{ name: 'Cafe', place_id: 'p1' }],
          selectedPlaceDetails: { name: 'Cafe', place_id: 'p1' },
        })
      );

      const res = await request(app)
        .get('/api/v1/meeting-requests/req-1/results')
        .set('Authorization', `Bearer ${tokenFor('user-a-id')}`);

      expect(res.status).toBe(200);
      expect(Object.keys(res.body).sort()).toEqual([
        'request_id',
        'selected_place',
        'status',
        'suggested_options',
      ]);
      assertNoSensitive(res.body);
    });
  });
});
