// Payment tests: public plans, free/paid subscription creation, and the Stripe
// webhook (signature verification + handler dispatch). Stripe network calls are
// stubbed via a partial mock so PLAN_DETAILS and pure logic stay real.
jest.mock('../src/config/prisma', () => {
  const { mockDeep } = require('jest-mock-extended');
  const m = mockDeep();
  return { __esModule: true, prisma: m, default: m };
});
jest.mock('../src/services/stripeService', () => {
  const actual = jest.requireActual('../src/services/stripeService');
  return {
    __esModule: true,
    ...actual,
    constructWebhookEvent: jest.fn(),
    getOrCreateStripeCustomer: jest.fn().mockResolvedValue('cus_test'),
    createCheckoutSession: jest.fn().mockResolvedValue('https://checkout.stripe.com/session_x'),
    retrieveSubscription: jest.fn(),
  };
});

import request from 'supertest';
import jwt from 'jsonwebtoken';
import { prismaMock } from './helpers/prismaMock';
import { makeUser, makeSubscription } from './helpers/fixtures';
import { constructWebhookEvent } from '../src/services/stripeService';
import app from '../src/server';

const mockConstruct = constructWebhookEvent as jest.Mock;
const token = jwt.sign({ sub: 'user-a-id', email: 'a@example.com' }, 'test-secret', {
  algorithm: 'HS256',
});

describe('Payments API', () => {
  describe('GET /api/v1/payments/plans (public)', () => {
    it('returns the canonical plan list', async () => {
      const res = await request(app).get('/api/v1/payments/plans');
      expect(res.status).toBe(200);
      expect(Array.isArray(res.body)).toBe(true);
      const ids = res.body.map((p: { id: string }) => p.id);
      expect(ids).toEqual(expect.arrayContaining(['free', 'basic', 'premium']));
      const premium = res.body.find((p: { id: string }) => p.id === 'premium');
      expect(premium).toMatchObject({ name: 'Premium', currency: 'usd', popular: true });
    });
  });

  describe('POST /api/v1/payments/subscriptions', () => {
    it('free plan → 201 active subscription', async () => {
      prismaMock.user.findUnique.mockResolvedValue(makeUser());
      prismaMock.subscription.findFirst.mockResolvedValue(null); // no existing free
      prismaMock.subscription.create.mockResolvedValue(
        makeSubscription({ planId: 'free' })
      );

      const res = await request(app)
        .post('/api/v1/payments/subscriptions')
        .set('Authorization', `Bearer ${token}`)
        .send({ plan_id: 'free' });

      expect(res.status).toBe(201);
      expect(res.body).toMatchObject({ plan_id: 'free', status: 'active' });
    });

    it('paid plan → 201 with checkout_url + pending_payment', async () => {
      prismaMock.user.findUnique.mockResolvedValue(makeUser());

      const res = await request(app)
        .post('/api/v1/payments/subscriptions')
        .set('Authorization', `Bearer ${token}`)
        .send({ plan_id: 'premium' });

      expect(res.status).toBe(201);
      expect(res.body).toMatchObject({
        checkout_url: 'https://checkout.stripe.com/session_x',
        status: 'pending_payment',
      });
    });

    it('missing plan_id → 400', async () => {
      prismaMock.user.findUnique.mockResolvedValue(makeUser());
      const res = await request(app)
        .post('/api/v1/payments/subscriptions')
        .set('Authorization', `Bearer ${token}`)
        .send({});
      expect(res.status).toBe(400);
    });

    it('requires auth (401)', async () => {
      const res = await request(app)
        .post('/api/v1/payments/subscriptions')
        .send({ plan_id: 'free' });
      expect(res.status).toBe(401);
    });
  });

  describe('POST /api/v1/payments/webhook', () => {
    it('returns 400 when the Stripe-Signature header is missing', async () => {
      const res = await request(app)
        .post('/api/v1/payments/webhook')
        .set('Content-Type', 'application/json')
        .send(Buffer.from(JSON.stringify({ id: 'evt' })));
      expect(res.status).toBe(400);
      expect(mockConstruct).not.toHaveBeenCalled();
    });

    it('returns 400 for an invalid signature', async () => {
      mockConstruct.mockImplementation(() => {
        throw new Error('No signatures found matching the expected signature');
      });
      const res = await request(app)
        .post('/api/v1/payments/webhook')
        .set('Stripe-Signature', 'bad-sig')
        .set('Content-Type', 'application/json')
        .send(Buffer.from(JSON.stringify({ id: 'evt' })));
      expect(res.status).toBe(400);
      expect(res.body.error).toContain('Webhook signature verification failed');
    });

    it('processes a verified subscription.deleted event → 200', async () => {
      mockConstruct.mockReturnValue({
        type: 'customer.subscription.deleted',
        data: { object: { id: 'sub_123' } },
      });
      // markCanceledByStripeId → findByStripeSubscriptionId → null (no-op).
      prismaMock.subscription.findUnique.mockResolvedValue(null);

      const res = await request(app)
        .post('/api/v1/payments/webhook')
        .set('Stripe-Signature', 'good-sig')
        .set('Content-Type', 'application/json')
        .send(Buffer.from(JSON.stringify({ id: 'evt' })));

      expect(res.status).toBe(200);
      expect(res.body).toEqual({ status: 'success' });
      expect(mockConstruct).toHaveBeenCalledTimes(1);
    });

    it('acknowledges an unhandled event type → 200', async () => {
      mockConstruct.mockReturnValue({
        type: 'invoice.paid',
        data: { object: {} },
      });
      const res = await request(app)
        .post('/api/v1/payments/webhook')
        .set('Stripe-Signature', 'good-sig')
        .set('Content-Type', 'application/json')
        .send(Buffer.from(JSON.stringify({ id: 'evt' })));
      expect(res.status).toBe(200);
      expect(res.body).toEqual({ status: 'success' });
    });
  });
});
