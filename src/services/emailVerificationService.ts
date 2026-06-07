// Email verification token persistence. 32-byte URL-safe token, 24h expiry,
// single-use. Mirrors passwordResetService.
import crypto from 'crypto';
import { prisma } from '../config/prisma.js';
import { markEmailVerified } from './userService.js';
import { BadRequest } from '../utils/errors.js';

const TOKEN_TTL_MS = 24 * 60 * 60 * 1000; // 24 hours

export async function createVerificationToken(userId: string): Promise<string> {
  const token = crypto.randomBytes(32).toString('base64url');
  const now = new Date();
  await prisma.emailVerification.create({
    data: {
      userId,
      token,
      createdAt: now,
      expiresAt: new Date(now.getTime() + TOKEN_TTL_MS),
      used: false,
    },
  });
  return token;
}

/**
 * Validate a verification token (exists, unused, not expired), flip the user's
 * emailVerified flag, and mark the token used. Throws BadRequest on invalidity.
 */
export async function consumeVerificationToken(token: string): Promise<void> {
  if (!token) {
    throw BadRequest('Token is required');
  }

  const record = await prisma.emailVerification.findUnique({ where: { token } });
  if (!record || record.used || new Date() > record.expiresAt) {
    throw BadRequest('Invalid or expired verification token');
  }

  await markEmailVerified(record.userId);
  await prisma.emailVerification.update({ where: { id: record.id }, data: { used: true } });
}
