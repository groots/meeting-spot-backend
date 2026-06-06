// Stripe integration helpers. Ported from app/utils/stripe_helpers.py.
// The Stripe client is lazily constructed so the app boots without a key
// (endpoints degrade gracefully / tests mock this module).
import Stripe from 'stripe';
import { User } from '@prisma/client';
import { prisma } from '../config/prisma.js';
import { env } from '../config/env.js';

export interface PlanDetail {
  name: string;
  description: string;
  price: number;
  interval: string | null;
  features: string[];
}

export const PLAN_DETAILS: Record<string, PlanDetail> = {
  free: {
    name: 'Free',
    description: 'Basic features with limited usage',
    price: 0,
    interval: null,
    features: [
      'Create up to 3 meeting requests per month',
      'Basic meeting locations',
      'Email notifications',
    ],
  },
  basic: {
    name: 'Basic',
    description: 'Enhanced features for casual users',
    price: 4.99,
    interval: 'month',
    features: [
      'Unlimited meeting requests',
      'Enhanced location recommendations',
      'Priority support',
      'SMS notifications',
    ],
  },
  premium: {
    name: 'Premium',
    description: 'Pro features for power users',
    price: 9.99,
    interval: 'month',
    features: [
      'All Basic features',
      'Advanced location filtering',
      'Custom meeting preferences',
      'Team collaboration',
      'Priority support',
    ],
  },
};

let stripeClient: Stripe | null = null;

export function getStripe(): Stripe {
  if (!env.stripeSecretKey) {
    throw new Error('Stripe is not configured (missing STRIPE_SECRET_KEY)');
  }
  if (!stripeClient) {
    stripeClient = new Stripe(env.stripeSecretKey);
  }
  return stripeClient;
}

/** Get or create a Stripe customer for the user; persists stripeCustomerId. */
export async function getOrCreateStripeCustomer(user: User): Promise<string> {
  if (user.stripeCustomerId) {
    return user.stripeCustomerId;
  }
  const stripe = getStripe();
  const customer = await stripe.customers.create({
    email: user.email,
    name: user.email.split('@')[0],
    metadata: { user_id: user.id },
  });
  await prisma.user.update({
    where: { id: user.id },
    data: { stripeCustomerId: customer.id },
  });
  return customer.id;
}

/** Create a Stripe Checkout Session for a subscription; returns the URL. */
export async function createCheckoutSession(
  user: User,
  priceId: string,
  successUrl: string,
  cancelUrl: string
): Promise<string> {
  const stripe = getStripe();
  const customerId = await getOrCreateStripeCustomer(user);

  const session = await stripe.checkout.sessions.create({
    customer: customerId,
    payment_method_types: ['card'],
    line_items: [{ price: priceId, quantity: 1 }],
    mode: 'subscription',
    success_url: successUrl,
    cancel_url: cancelUrl,
    metadata: { user_id: user.id },
  });

  return session.url ?? `https://checkout.stripe.com/pay/${session.id}`;
}

export interface PriceData {
  id: string;
  product_id: string;
  name: string;
  description: string;
  amount: number;
  currency: string;
  interval: string;
  interval_count: number;
}

/** List active subscription prices (with expanded products). */
export async function getSubscriptionPrices(): Promise<PriceData[]> {
  const stripe = getStripe();
  const prices = await stripe.prices.list({
    active: true,
    limit: 10,
    expand: ['data.product'],
  });

  return prices.data.map((price) => {
    const product = price.product as Stripe.Product;
    return {
      id: price.id,
      product_id: product.id,
      name: product.name,
      description: product.description ?? '',
      amount: (price.unit_amount ?? 0) / 100,
      currency: price.currency,
      interval: price.recurring?.interval ?? '',
      interval_count: price.recurring?.interval_count ?? 1,
    };
  });
}

export interface PaymentMethodData {
  id: string;
  brand: string;
  last4: string;
  exp_month: number;
  exp_year: number;
  is_default: boolean;
}

/** List a user's card payment methods ([] if no Stripe customer). */
export async function getCustomerPaymentMethods(
  user: User
): Promise<PaymentMethodData[]> {
  if (!user.stripeCustomerId) {
    return [];
  }
  const stripe = getStripe();
  const methods = await stripe.paymentMethods.list({
    customer: user.stripeCustomerId,
    type: 'card',
  });

  return methods.data.map((method) => {
    const card = method.card;
    return {
      id: method.id,
      brand: card?.brand ?? '',
      last4: card?.last4 ?? '',
      exp_month: card?.exp_month ?? 0,
      exp_year: card?.exp_year ?? 0,
      is_default: method.metadata?.is_default === 'true',
    };
  });
}

/** Cancel a Stripe subscription at period end. */
export async function cancelStripeSubscription(
  stripeSubscriptionId: string
): Promise<boolean> {
  const stripe = getStripe();
  await stripe.subscriptions.update(stripeSubscriptionId, {
    cancel_at_period_end: true,
  });
  return true;
}

/** Verify and construct a webhook event from the raw body + signature. */
export function constructWebhookEvent(
  rawBody: Buffer,
  signature: string
): Stripe.Event {
  const stripe = getStripe();
  return stripe.webhooks.constructEvent(rawBody, signature, env.stripeWebhookSecret);
}

export function retrieveSubscription(id: string): Promise<Stripe.Subscription> {
  return getStripe().subscriptions.retrieve(id);
}
