// Password reset token persistence. 32-byte URL-safe token, 1h expiry,
// single-use (matches the Python PasswordReset model defaults).
import crypto from 'crypto';
import { prisma } from '../config/prisma.js';

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
