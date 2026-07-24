// Persist Google (and later other) calendar OAuth connections.
// Refresh tokens are encrypted at rest; busy event details are never stored.
import { CalendarConnection } from '@prisma/client';
import { prisma } from '../config/prisma.js';
import { encryptSecret, decryptSecret } from '../utils/encryption.js';

export const GOOGLE_PROVIDER = 'google';

export async function findActive(
  userId: string,
  provider = GOOGLE_PROVIDER
): Promise<CalendarConnection | null> {
  return prisma.calendarConnection.findFirst({
    where: { userId, provider, revokedAt: null },
  });
}

export async function isConnected(userId: string, provider = GOOGLE_PROVIDER): Promise<boolean> {
  const row = await findActive(userId, provider);
  return Boolean(row);
}

export async function upsertGoogleConnection(input: {
  userId: string;
  accountEmail: string;
  refreshToken: string;
  scopes: string;
  timezone?: string | null;
}): Promise<CalendarConnection> {
  const now = new Date();
  const refreshTokenEncrypted = encryptSecret(input.refreshToken);

  return prisma.calendarConnection.upsert({
    where: {
      userId_provider: { userId: input.userId, provider: GOOGLE_PROVIDER },
    },
    create: {
      userId: input.userId,
      provider: GOOGLE_PROVIDER,
      accountEmail: input.accountEmail,
      refreshTokenEncrypted,
      scopes: input.scopes,
      timezone: input.timezone ?? null,
      createdAt: now,
      updatedAt: now,
    },
    update: {
      accountEmail: input.accountEmail,
      refreshTokenEncrypted,
      scopes: input.scopes,
      timezone: input.timezone ?? null,
      revokedAt: null,
      updatedAt: now,
    },
  });
}

export function decryptRefreshToken(connection: CalendarConnection): string {
  return decryptSecret(connection.refreshTokenEncrypted);
}

export async function revoke(userId: string, provider = GOOGLE_PROVIDER): Promise<boolean> {
  const existing = await findActive(userId, provider);
  if (!existing) return false;
  await prisma.calendarConnection.update({
    where: { id: existing.id },
    data: { revokedAt: new Date(), refreshTokenEncrypted: encryptSecret('revoked') },
  });
  return true;
}

export function toPublicStatus(connection: CalendarConnection | null): {
  connected: boolean;
  provider: string | null;
  account_email: string | null;
} {
  if (!connection) {
    return { connected: false, provider: null, account_email: null };
  }
  return {
    connected: true,
    provider: connection.provider,
    account_email: connection.accountEmail,
  };
}
