// Health-check tests: 200 when the DB responds, 503 when it doesn't.
jest.mock('../src/config/prisma', () => {
  const { mockDeep } = require('jest-mock-extended');
  const m = mockDeep();
  return { __esModule: true, prisma: m, default: m };
});

import request from 'supertest';
import { prismaMock } from './helpers/prismaMock';
import app from '../src/server';

describe('GET /api/v1/health', () => {
  it('returns 200 with database "up" when the DB responds', async () => {
    prismaMock.$queryRaw.mockResolvedValue([{ '?column?': 1 }] as never);
    const res = await request(app).get('/api/v1/health');
    expect(res.status).toBe(200);
    expect(res.body).toMatchObject({ status: 'OK', database: 'up' });
  });

  it('returns 503 with database "down" when the DB query fails', async () => {
    prismaMock.$queryRaw.mockRejectedValue(new Error('P1001: unreachable') as never);
    const res = await request(app).get('/api/v1/health');
    expect(res.status).toBe(503);
    expect(res.body).toMatchObject({ status: 'DEGRADED', database: 'down' });
  });
});
