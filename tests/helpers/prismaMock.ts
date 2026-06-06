// Shared, deeply-mocked PrismaClient.
//
// Usage in a test file (the jest.mock MUST be declared in the test file so it is
// hoisted above that file's imports):
//
//   jest.mock('../src/config/prisma', () => {
//     const { mockDeep } = require('jest-mock-extended');
//     const m = mockDeep();
//     return { __esModule: true, prisma: m, default: m };
//   });
//   import { prismaMock } from './helpers/prismaMock';
//
// The helper resolves the (already-mocked) prisma instance and exposes it with
// the right type, plus resets it before each test.
import type { PrismaClient } from '@prisma/client';
import { mockReset, DeepMockProxy } from 'jest-mock-extended';
import { prisma } from '../../src/config/prisma';

export const prismaMock = prisma as unknown as DeepMockProxy<PrismaClient>;

beforeEach(() => {
  mockReset(prismaMock);
});
