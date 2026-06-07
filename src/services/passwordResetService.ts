// Password reset token persistence. 32-byte URL-safe token, 1h expiry,
// single-use (matches the Python PasswordReset model defaults).
import crypto from 'crypto';
import { prisma } from '../config/prisma.js';
import { updatePassword } from './userService.js';
import { BadRequest } from '../utils/errors.js';

const TOKEN_TTL_MS = 60 * 60 * 1000; // 1 hour

export async function createResetToken(userId: string): Promise<string> {
  const token = crypto.randomBytes(32).toString('base64url');
  const now = new Date();
  await prisma.passwordReset.create({
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
 * Validate a reset token (exists, unused, not expired), update the user's
 * password, and mark the token used. Throws BadRequest on any invalidity so the
 * caller returns a single generic error (no token-state enumeration).
 */
export async function consumeResetToken(token: string, newPassword: string): Promise<void> {
  if (!token || !newPassword) {
    throw BadRequest('Token and password are required');
  }

  const record = await prisma.passwordReset.findUnique({ where: { token } });
  if (!record || record.used || new Date() > record.expiresAt) {
    throw BadRequest('Invalid or expired reset token');
  }

  await updatePassword(record.userId, newPassword);
  await prisma.passwordReset.update({ where: { id: record.id }, data: { used: true } });
}
