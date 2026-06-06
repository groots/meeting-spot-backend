// Subscription helpers. `isPremium` mirrors the Python Subscription.is_active()
// (status === 'active' AND current_period_end in the future) and the User
// is_premium derivation (has at least one active subscription).
import { Subscription } from '@prisma/client';
import { prisma } from '../config/prisma.js';
import { env } from '../config/env.js';

export function isSubscriptionActive(sub: {
  status: string;
  currentPeriodEnd: Date | null;
}): boolean {
  if (sub.status !== 'active') return false;
  if (!sub.currentPeriodEnd) return false;
  return sub.currentPeriodEnd.getTime() > Date.now();
}

export async function isPremium(userId: string): Promise<boolean> {
  // Dev/test convenience: bypass gating when explicitly enabled (never in prod).
  if (env.premiumBypass && !env.isProduction) {
    return true;
  }

  const subs = await prisma.subscription.findMany({ where: { userId } });
  return subs.some((s) => isSubscriptionActive(s));
}

// --- Persistence ---

export function listByUser(userId: string): Promise<Subscription[]> {
  return prisma.subscription.findMany({
    where: { userId },
    orderBy: { createdAt: 'desc' },
  });
}

export function findByIdForUser(id: string, userId: string): Promise<Subscription | null> {
  return prisma.subscription.findFirst({ where: { id, userId } });
}

export function findActiveByPlan(
  userId: string,
  planId: string
): Promise<Subscription | null> {
  return prisma.subscription.findFirst({
    where: { userId, planId, status: 'active' },
  });
}

export function findByStripeSubscriptionId(
  stripeSubscriptionId: string
): Promise<Subscription | null> {
  return prisma.subscription.findUnique({ where: { stripeSubscriptionId } });
}

export interface CreateFreeInput {
  userId: string;
  planId: string;
  stripeCustomerId?: string | null;
  stripeSubscriptionId?: string | null;
}

export function createFreeSubscription(input: CreateFreeInput): Promise<Subscription> {
  const now = new Date();
  const yearLater = new Date(now.getTime() + 365 * 24 * 60 * 60 * 1000);
  return prisma.subscription.create({
    data: {
      userId: input.userId,
      planId: input.planId,
      status: 'active',
      currentPeriodStart: now,
      currentPeriodEnd: yearLater,
      cancelAtPeriodEnd: false,
      stripeCustomerId: input.stripeCustomerId ?? null,
      stripeSubscriptionId: input.stripeSubscriptionId ?? null,
      createdAt: now,
      updatedAt: now,
    },
  });
}

export function cancelLocal(id: string): Promise<Subscription> {
  return prisma.subscription.update({
    where: { id },
    data: { status: 'canceled', cancelAtPeriodEnd: true, updatedAt: new Date() },
  });
}

export interface UpsertFromStripeInput {
  userId: string;
  stripeSubscriptionId: string;
  stripeCustomerId: string | null;
  planId: string;
  status: string;
  currentPeriodStart: Date;
  currentPeriodEnd: Date;
  cancelAtPeriodEnd: boolean;
}

export async function upsertFromStripe(
  input: UpsertFromStripeInput
): Promise<Subscription> {
  const now = new Date();
  const existing = await findByStripeSubscriptionId(input.stripeSubscriptionId);
  if (existing) {
    return prisma.subscription.update({
      where: { id: existing.id },
      data: {
        status: input.status,
        currentPeriodStart: input.currentPeriodStart,
        currentPeriodEnd: input.currentPeriodEnd,
        cancelAtPeriodEnd: input.cancelAtPeriodEnd,
        updatedAt: now,
      },
    });
  }
  return prisma.subscription.create({
    data: {
      userId: input.userId,
      stripeSubscriptionId: input.stripeSubscriptionId,
      stripeCustomerId: input.stripeCustomerId,
      planId: input.planId,
      status: input.status,
      currentPeriodStart: input.currentPeriodStart,
      currentPeriodEnd: input.currentPeriodEnd,
      cancelAtPeriodEnd: input.cancelAtPeriodEnd,
      createdAt: now,
      updatedAt: now,
    },
  });
}

export async function markCanceledByStripeId(
  stripeSubscriptionId: string
): Promise<void> {
  const existing = await findByStripeSubscriptionId(stripeSubscriptionId);
  if (existing) {
    await prisma.subscription.update({
      where: { id: existing.id },
      data: { status: 'canceled', updatedAt: new Date() },
    });
  }
}

/** Serializer matching the Python Subscription.to_dict. */
export function toDict(sub: Subscription): Record<string, unknown> {
  return {
    id: sub.id,
    user_id: sub.userId,
    plan_id: sub.planId,
    status: sub.status,
    current_period_start: sub.currentPeriodStart
      ? sub.currentPeriodStart.toISOString()
      : null,
    current_period_end: sub.currentPeriodEnd ? sub.currentPeriodEnd.toISOString() : null,
    cancel_at_period_end: sub.cancelAtPeriodEnd,
    created_at: sub.createdAt.toISOString(),
    updated_at: sub.updatedAt.toISOString(),
  };
}
