import request from 'supertest';
import app from '../src/server';
import { UserModel } from '../src/models/User';

// Mock the database functions
jest.mock('../src/config/database', () => ({
  connectToDatabase: jest.fn().mockResolvedValue(true),
  query: jest.fn().mockImplementation((text, params) => {
    // Mock user creation
    if (text.includes('INSERT INTO users')) {
      return {
        rows: [
          {
            id: '123e4567-e89b-12d3-a456-426614174000',
            email: params[1],
            created_at: new Date(),
            updated_at: new Date(),
            password_hash: params.find((p: any) => p.startsWith('$2a$')),
          },
        ],
      };
    }

    // Mock user lookup by email
    if (text.includes('SELECT * FROM users WHERE email')) {
      if (params[0] === 'existing@example.com') {
        return {
          rows: [
            {
              id: '123e4567-e89b-12d3-a456-426614174000',
              email: 'existing@example.com',
              password_hash: '$2a$10$XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX',
              created_at: new Date(),
              updated_at: new Date(),
            },
          ],
        };
      }
      return { rows: [] };
    }

    // Mock user lookup by ID
    if (text.includes('SELECT * FROM users WHERE id')) {
      return {
        rows: [
          {
            id: params[0],
            email: 'test@example.com',
            password_hash: '$2a$10$XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX',
            created_at: new Date(),
            updated_at: new Date(),
          },
        ],
      };
    }

    return { rows: [] };
  }),
}));

// Mock the password verification
jest.mock('bcryptjs', () => ({
  genSalt: jest.fn().mockResolvedValue('$2a$10$XXXX'),
  hash: jest.fn().mockResolvedValue('$2a$10$XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX'),
  compare: jest.fn().mockImplementation((password, hash) => {
    return Promise.resolve(password === 'correctpassword');
  }),
}));

// Mock JWT functions
jest.mock('jsonwebtoken', () => ({
  sign: jest.fn().mockReturnValue('test.jwt.token'),
  verify: jest.fn().mockImplementation((token, secret) => {
    if (token === 'valid.token.here') {
      return { sub: '123e4567-e89b-12d3-a456-426614174000' };
    }
    if (token === 'expired.token.here') {
      throw { name: 'TokenExpiredError' };
    }
    throw new Error('Invalid token');
  }),
  decode: jest.fn().mockImplementation((token) => {
    if (token === 'valid.token.here' || token === 'expired.token.here') {
      return { sub: '123e4567-e89b-12d3-a456-426614174000' };
    }
    return null;
  }),
}));

describe('Authentication API', () => {
  describe('POST /api/v1/auth/register', () => {
    it('should register a new user successfully', async () => {
      const res = await request(app).post('/api/v1/auth/register').send({
        email: 'test@example.com',
        password: 'password123',
        first_name: 'Test',
        last_name: 'User',
      });

      expect(res.statusCode).toEqual(201);
      expect(res.body).toHaveProperty('access_token');
      expect(res.body).toHaveProperty('user');
      expect(res.body.user.email).toEqual('test@example.com');
    });

    it('should return 400 if email or password is missing', async () => {
      const res = await request(app).post('/api/v1/auth/register').send({
        email: 'test@example.com',
      });

      expect(res.statusCode).toEqual(400);
      expect(res.body).toHaveProperty('error');
    });

    it('should return 409 if user already exists', async () => {
      const res = await request(app).post('/api/v1/auth/register').send({
        email: 'existing@example.com',
        password: 'password123',
      });

      expect(res.statusCode).toEqual(409);
      expect(res.body).toHaveProperty('error');
    });
  });

  describe('POST /api/v1/auth/login', () => {
    it('should login successfully with correct credentials', async () => {
      const res = await request(app).post('/api/v1/auth/login').send({
        email: 'existing@example.com',
        password: 'correctpassword',
      });

      expect(res.statusCode).toEqual(200);
      expect(res.body).toHaveProperty('access_token');
      expect(res.body).toHaveProperty('user');
    });

    it('should return 401 with incorrect password', async () => {
      const res = await request(app).post('/api/v1/auth/login').send({
        email: 'existing@example.com',
        password: 'wrongpassword',
      });

      expect(res.statusCode).toEqual(401);
      expect(res.body).toHaveProperty('error');
    });

    it('should return 401 if user does not exist', async () => {
      const res = await request(app).post('/api/v1/auth/login').send({
        email: 'nonexistent@example.com',
        password: 'password123',
      });

      expect(res.statusCode).toEqual(401);
      expect(res.body).toHaveProperty('error');
    });
  });

  describe('POST /api/v1/auth/refresh', () => {
    it('should refresh a valid token', async () => {
      const res = await request(app)
        .post('/api/v1/auth/refresh')
        .set('Authorization', 'Bearer valid.token.here')
        .send();

      expect(res.statusCode).toEqual(200);
      expect(res.body).toHaveProperty('access_token');
    });

    it('should refresh an expired token if user still exists', async () => {
      const res = await request(app)
        .post('/api/v1/auth/refresh')
        .set('Authorization', 'Bearer expired.token.here')
        .send();

      expect(res.statusCode).toEqual(200);
      expect(res.body).toHaveProperty('access_token');
    });

    it('should return 401 for an invalid token', async () => {
      const res = await request(app)
        .post('/api/v1/auth/refresh')
        .set('Authorization', 'Bearer invalid.token.here')
        .send();

      expect(res.statusCode).toEqual(401);
      expect(res.body).toHaveProperty('error');
    });
  });
});
