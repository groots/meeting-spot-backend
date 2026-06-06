// Contacts premium-gating tests:
//   * GET /          soft gate  → non-premium gets 200 [] + X-Premium-Required
//   * POST/PUT/DELETE hard gate → non-premium gets 402
//   * premium users get full CRUD
jest.mock('../src/config/prisma', () => {
  const { mockDeep } = require('jest-mock-extended');
  const m = mockDeep();
  return { __esModule: true, prisma: m, default: m };
});

import request from 'supertest';
import jwt from 'jsonwebtoken';
import { prismaMock } from './helpers/prismaMock';
import { makeUser, makeContact, makeSubscription } from './helpers/fixtures';
import app from '../src/server';

const token = jwt.sign({ sub: 'user-a-id', email: 'a@example.com' }, 'test-secret', {
  algorithm: 'HS256',
});

function asPremium(): void {
  prismaMock.user.findUnique.mockResolvedValue(makeUser());
  prismaMock.subscription.findMany.mockResolvedValue([makeSubscription()]);
}
function asFree(): void {
  prismaMock.user.findUnique.mockResolvedValue(makeUser());
  prismaMock.subscription.findMany.mockResolvedValue([]);
}

describe('Contacts API gating', () => {
  describe('GET /api/v1/contacts (soft gate)', () => {
    it('non-premium → 200 [] with X-Premium-Required header', async () => {
      asFree();
      const res = await request(app)
        .get('/api/v1/contacts')
        .set('Authorization', `Bearer ${token}`);
      expect(res.status).toBe(200);
      expect(res.body).toEqual([]);
      expect(res.headers['x-premium-required']).toBe('true');
      expect(res.headers['x-premium-feature']).toBe('contacts');
    });

    it('premium → 200 with serialized contacts', async () => {
      asPremium();
      prismaMock.contact.findMany.mockResolvedValue([makeContact()]);
      const res = await request(app)
        .get('/api/v1/contacts')
        .set('Authorization', `Bearer ${token}`);
      expect(res.status).toBe(200);
      expect(res.body).toHaveLength(1);
      expect(res.body[0]).toMatchObject({ id: 'contact-1', name: 'Bob' });
      expect(res.headers['x-premium-required']).toBeUndefined();
    });

    it('requires auth (401)', async () => {
      const res = await request(app).get('/api/v1/contacts');
      expect(res.status).toBe(401);
    });
  });

  describe('POST /api/v1/contacts (hard gate)', () => {
    it('non-premium → 402', async () => {
      asFree();
      const res = await request(app)
        .post('/api/v1/contacts')
        .set('Authorization', `Bearer ${token}`)
        .send({ name: 'Bob' });
      expect(res.status).toBe(402);
    });

    it('premium → 201 created', async () => {
      asPremium();
      prismaMock.contact.create.mockResolvedValue(makeContact());
      const res = await request(app)
        .post('/api/v1/contacts')
        .set('Authorization', `Bearer ${token}`)
        .send({ name: 'Bob', email: 'bob@example.com' });
      expect(res.status).toBe(201);
      expect(res.body).toMatchObject({ id: 'contact-1', name: 'Bob' });
    });

    it('premium + missing name → 400', async () => {
      asPremium();
      const res = await request(app)
        .post('/api/v1/contacts')
        .set('Authorization', `Bearer ${token}`)
        .send({ email: 'bob@example.com' });
      expect(res.status).toBe(400);
    });
  });

  describe('DELETE /api/v1/contacts/:id (hard gate)', () => {
    it('non-premium → 402', async () => {
      asFree();
      const res = await request(app)
        .delete('/api/v1/contacts/contact-1')
        .set('Authorization', `Bearer ${token}`);
      expect(res.status).toBe(402);
    });

    it('premium → 200 with confirmation message', async () => {
      asPremium();
      prismaMock.contact.findFirst.mockResolvedValue(makeContact());
      prismaMock.contact.delete.mockResolvedValue(makeContact());
      const res = await request(app)
        .delete('/api/v1/contacts/contact-1')
        .set('Authorization', `Bearer ${token}`);
      expect(res.status).toBe(200);
      expect(res.body.message).toContain('deleted successfully');
    });
  });

  describe('GET /api/v1/contacts/:id', () => {
    it('non-premium → meeting_count + premium_required', async () => {
      asFree();
      prismaMock.contact.findFirst.mockResolvedValue(makeContact());
      prismaMock.contact.findUnique.mockResolvedValue({
        ...makeContact(),
        _count: { meetingRequests: 2 },
      } as never);
      const res = await request(app)
        .get('/api/v1/contacts/contact-1')
        .set('Authorization', `Bearer ${token}`);
      expect(res.status).toBe(200);
      expect(res.body.premium_required).toBe(true);
      expect(res.body.meeting_count).toBe(2);
      expect(res.body).not.toHaveProperty('meetings');
    });

    it('premium → includes meetings history', async () => {
      asPremium();
      prismaMock.contact.findFirst.mockResolvedValue(makeContact());
      prismaMock.meetingRequest.findMany.mockResolvedValue([] as never);
      const res = await request(app)
        .get('/api/v1/contacts/contact-1')
        .set('Authorization', `Bearer ${token}`);
      expect(res.status).toBe(200);
      expect(res.body.meetings).toEqual([]);
      expect(res.body).not.toHaveProperty('premium_required');
    });
  });
});
