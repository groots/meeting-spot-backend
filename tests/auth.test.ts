// Auth flow tests on the Prisma-backed app. Prisma is deeply mocked; no DB.
jest.mock('../src/config/prisma', () => {
  const { mockDeep } = require('jest-mock-extended');
  const m = mockDeep();
  return { __esModule: true, prisma: m, default: m };
});

import request from 'supertest';
import { prismaMock } from './helpers/prismaMock';
import { makeUser } from './helpers/fixtures';
import app from '../src/server';

describe('Auth API', () => {
  describe('POST /api/v1/auth/register', () => {
    it('creates a user and returns { message, access_token, user }', async () => {
      prismaMock.user.findUnique.mockResolvedValue(null); // email not taken
      prismaMock.user.create.mockResolvedValue(makeUser());
      prismaMock.subscription.findMany.mockResolvedValue([]); // not premium

      const res = await request(app)
        .post('/api/v1/auth/register')
        .send({ email: 'a@example.com', password: 'password123' });

      expect(res.status).toBe(201);
      expect(typeof res.body.access_token).toBe('string');
      expect(res.body.message).toBe('User created successfully');
      expect(res.body.user).toMatchObject({
        id: 'user-a-id',
        email: 'a@example.com',
        is_premium: false,
      });
      // Never leak the password hash.
      expect(JSON.stringify(res.body)).not.toContain('passwordHash');
      expect(res.body.user).not.toHaveProperty('password_hash');
    });

    it('rejects missing fields with 400', async () => {
      const res = await request(app)
        .post('/api/v1/auth/register')
        .send({ email: 'a@example.com' });
      expect(res.status).toBe(400);
    });

    it('returns 409 if the user already exists', async () => {
      prismaMock.user.findUnique.mockResolvedValue(makeUser());
      const res = await request(app)
        .post('/api/v1/auth/register')
        .send({ email: 'a@example.com', password: 'password123' });
      expect(res.status).toBe(409);
    });
  });

  describe('POST /api/v1/auth/login', () => {
    it('returns 200 + token for valid credentials', async () => {
      const bcrypt = await import('bcryptjs');
      const passwordHash = await bcrypt.hash('password123', 10);
      prismaMock.user.findUnique.mockResolvedValue(makeUser({ passwordHash }));
      prismaMock.subscription.findMany.mockResolvedValue([]);

      const res = await request(app)
        .post('/api/v1/auth/login')
        .send({ email: 'a@example.com', password: 'password123' });

      expect(res.status).toBe(200);
      expect(res.body.access_token).toBeDefined();
      expect(res.body.message).toBe('Login successful');
    });

    it('returns 401 for an invalid password', async () => {
      const bcrypt = await import('bcryptjs');
      const passwordHash = await bcrypt.hash('correct-password', 10);
      prismaMock.user.findUnique.mockResolvedValue(makeUser({ passwordHash }));

      const res = await request(app)
        .post('/api/v1/auth/login')
        .send({ email: 'a@example.com', password: 'wrong-password' });

      expect(res.status).toBe(401);
    });

    it('returns 401 for an unknown user', async () => {
      prismaMock.user.findUnique.mockResolvedValue(null);
      const res = await request(app)
        .post('/api/v1/auth/login')
        .send({ email: 'nobody@example.com', password: 'password123' });
      expect(res.status).toBe(401);
    });
  });

  describe('GET /api/v1/auth/me', () => {
    it('returns 401 without a token', async () => {
      const res = await request(app).get('/api/v1/auth/me');
      expect(res.status).toBe(401);
    });

    it('returns the current user with a valid token', async () => {
      // Register to obtain a real token, then hit /me.
      prismaMock.user.findUnique.mockResolvedValue(null);
      prismaMock.user.create.mockResolvedValue(makeUser());
      prismaMock.subscription.findMany.mockResolvedValue([]);

      const reg = await request(app)
        .post('/api/v1/auth/register')
        .send({ email: 'a@example.com', password: 'password123' });
      const token = reg.body.access_token as string;

      // authenticate() + getCurrentUser() both look the user up by id.
      prismaMock.user.findUnique.mockResolvedValue(makeUser());

      const res = await request(app)
        .get('/api/v1/auth/me')
        .set('Authorization', `Bearer ${token}`);

      expect(res.status).toBe(200);
      expect(res.body).toMatchObject({ id: 'user-a-id', email: 'a@example.com' });
    });
  });
});
