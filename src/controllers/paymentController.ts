// Payment + subscription controllers. Ported from app/api/payments.py with the
// Stripe webhook hardened to verify the signature against the raw request body.
import { Request, Response, NextFunction } from 'express';
import Stripe from 'stripe';
import * as subscriptionService from '../services/subscriptionService.js';
import * as stripeService from '../services/stripeService.js';
import * as userService from '../services/userService.js';
import { env } from '../config/env.js';
import { BadRequest, NotFound, Unauthorized } from '../utils/errors.js';

/** GET /plans — public list of plan definitions. */
export function getPlans(_req: Request, res: Response): void {
  const plans = Object.entries(stripeService.PLAN_DETAILS).map(([id, details]) => ({
    id,
    name: details.name,
    description: details.description,
    features: details.features,
    price: details.price,
    interval: details.interval,
    currency: 'usd',
    popular: id === 'premium',
  }));
  res.status(200).json(plans);
}

/** GET /prices — public list of active Stripe prices. */
export async function getPrices(_req: Request, res: Response): Promise<void> {
  try {
    const prices = await stripeService.getSubscriptionPrices();
    res.status(200).json(prices);
  } catch (e) {
    res.status(500).json({ error: (e as Error).message });
  }
}

/** GET /subscriptions — caller's subscriptions. */
export async function getSubscriptions(
  req: Request,
  res: Response,
  next: NextFunction
): Promise<void> {
  try {
    const userId = req.user?.id;
    if (!userId) throw Unauthorized('Not authenticated');

    const subs = await subscriptionService.listByUser(userId);
    res.status(200).json(subs.map((s) => subscriptionService.toDict(s)));
  } catch (e) {
    next(e);
  }
}

/** POST /subscriptions — free plan creates immediately; paid returns checkout. */
export async function createSubscription(
  req: Request,
  res: Response,
  next: NextFunction
): Promise<void> {
  try {
    const userId = req.user?.id;
    if (!userId) throw Unauthorized('Not authenticated');

    const data = req.body ?? {};
    if (!data.plan_id) throw BadRequest('Missing required field: plan_id');

    const planId = data.plan_id as string;
    const paymentProvider = (data.payment_provider as string) ?? 'stripe';
    const paymentId = data.payment_id as string | undefined;

    if (planId === 'free') {
      const existing = await subscriptionService.findActiveByPlan(userId, planId);
      if (existing) throw BadRequest('User already has an active free plan');

      const user = await userService.findById(userId);
      let stripeCustomerId: string | null = null;
      if (paymentProvider === 'stripe' && user) {
        try {
          stripeCustomerId = await stripeService.getOrCreateStripeCustomer(user);
        } catch (e) {
          console.error('Error creating Stripe customer:', e);
        }
      }

      const subscription = await subscriptionService.createFreeSubscription({
        userId,
        planId,
        stripeCustomerId,
        stripeSubscriptionId: paymentId ?? null,
      });
      res.status(201).json(subscriptionService.toDict(subscription));
      return;
    }

    // Paid plan → Stripe checkout session.
    if (paymentProvider === 'stripe') {
      const user = await userService.findById(userId);
      if (!user) throw NotFound('User not found');

      const priceId = resolvePriceId(planId);
      const successUrl = (data.return_url as string) ?? `${env.frontendUrl}/subscription`;
      const cancelUrl = (data.return_url as string) ?? `${env.frontendUrl}/pricing`;

      try {
        const checkoutUrl = await stripeService.createCheckoutSession(
          user,
          priceId,
          successUrl,
          cancelUrl
        );
        res.status(201).json({
          checkout_url: checkoutUrl,
          status: 'pending_payment',
          message: 'Please complete payment to activate subscription',
        });
      } catch (e) {
        console.error('Error creating checkout session:', e);
        res.status(500).json({ error: 'Failed to create payment customer' });
      }
      return;
    }

    throw BadRequest(`Unsupported payment provider: ${paymentProvider}`);
  } catch (e) {
    next(e);
  }
}

/** GET /subscriptions/:id — single subscription (owner). */
export async function getSubscription(
  req: Request,
  res: Response,
  next: NextFunction
): Promise<void> {
  try {
    const userId = req.user?.id;
    if (!userId) throw Unauthorized('Not authenticated');

    const sub = await subscriptionService.findByIdForUser(req.params.id, userId);
    if (!sub) throw NotFound(`Subscription ${req.params.id} not found`);

    res.status(200).json(subscriptionService.toDict(sub));
  } catch (e) {
    next(e);
  }
}

/** DELETE /subscriptions/:id — cancel (Stripe or local). */
export async function cancelSubscription(
  req: Request,
  res: Response,
  next: NextFunction
): Promise<void> {
  try {
    const userId = req.user?.id;
    if (!userId) throw Unauthorized('Not authenticated');

    const sub = await subscriptionService.findByIdForUser(req.params.id, userId);
    if (!sub) throw NotFound(`Subscription ${req.params.id} not found`);

    if (sub.status !== 'active') {
      throw BadRequest('Cannot cancel a subscription that is not active');
    }

    if (sub.stripeSubscriptionId) {
      try {
        await stripeService.cancelStripeSubscription(sub.stripeSubscriptionId);
        res.status(200).json({
          id: sub.id,
          status: 'canceling',
          cancel_at_period_end: true,
          message: 'Subscription will be canceled at the end of the billing period',
        });
        return;
      } catch (e) {
        console.error('Error canceling Stripe subscription:', e);
        // Fall through to local cancellation.
      }
    }

    const canceled = await subscriptionService.cancelLocal(sub.id);
    res.status(200).json({
      ...subscriptionService.toDict(canceled),
      message: 'Subscription has been canceled',
    });
  } catch (e) {
    next(e);
  }
}

/** POST /checkout — create a Stripe checkout session ({checkout_url}). */
export async function createCheckout(
  req: Request,
  res: Response,
  next: NextFunction
): Promise<void> {
  try {
    const userId = req.user?.id;
    if (!userId) throw Unauthorized('Not authenticated');

    const data = req.body ?? {};
    // Frontend sends {price_id, success_url, cancel_url}; tolerate {plan_id, return_url}.
    const priceId = (data.price_id as string) ?? resolvePriceId(data.plan_id as string);
    if (!priceId) throw BadRequest('Missing required field: price_id');

    const user = await userService.findById(userId);
    if (!user) throw NotFound('User not found');

    const successUrl =
      (data.success_url as string) ?? (data.return_url as string) ?? `${env.frontendUrl}/subscription`;
    const cancelUrl =
      (data.cancel_url as string) ?? (data.return_url as string) ?? `${env.frontendUrl}/pricing`;

    const checkoutUrl = await stripeService.createCheckoutSession(
      user,
      priceId,
      successUrl,
      cancelUrl
    );
    res.status(201).json({ checkout_url: checkoutUrl });
  } catch (e) {
    next(e);
  }
}

/** GET /payment-methods — caller's cards ([] on error). */
export async function listPaymentMethods(
  req: Request,
  res: Response,
  next: NextFunction
): Promise<void> {
  try {
    const userId = req.user?.id;
    if (!userId) throw Unauthorized('Not authenticated');

    const user = await userService.findById(userId);
    if (!user) {
      res.status(200).json([]);
      return;
    }
    try {
      const methods = await stripeService.getCustomerPaymentMethods(user);
      res.status(200).json(methods);
    } catch (e) {
      console.error('Error retrieving payment methods:', e);
      res.status(200).json([]);
    }
  } catch (e) {
    next(e);
  }
}

/**
 * POST /webhook — verifies the Stripe signature against the raw body, then
 * handles checkout.session.completed and subscription updated/deleted events.
 * Bad signature → 400.
 */
export async function webhook(req: Request, res: Response): Promise<void> {
  const signature = req.headers['stripe-signature'];
  if (!signature || typeof signature !== 'string') {
    res.status(400).json({ error: 'Missing Stripe-Signature header' });
    return;
  }

  let event: Stripe.Event;
  try {
    // req.body is a Buffer here (express.raw mounted on this path).
    event = stripeService.constructWebhookEvent(req.body as Buffer, signature);
  } catch (e) {
    res.status(400).json({ error: `Webhook signature verification failed: ${(e as Error).message}` });
    return;
  }

  try {
    switch (event.type) {
      case 'checkout.session.completed':
        await handleCheckoutCompleted(event.data.object as Stripe.Checkout.Session);
        break;
      case 'customer.subscription.updated':
        await handleSubscriptionUpdated(event.data.object as Stripe.Subscription);
        break;
      case 'customer.subscription.deleted':
        await subscriptionService.markCanceledByStripeId(
          (event.data.object as Stripe.Subscription).id
        );
        break;
      default:
        // Unhandled event type — acknowledge without action.
        break;
    }
    res.status(200).json({ status: 'success' });
  } catch (e) {
    console.error('Error processing webhook:', e);
    res.status(400).json({ error: (e as Error).message });
  }
}

// --- Webhook helpers ---

async function handleCheckoutCompleted(session: Stripe.Checkout.Session): Promise<void> {
  const subscriptionId =
    typeof session.subscription === 'string'
      ? session.subscription
      : session.subscription?.id;
  if (!subscriptionId) return;

  const userId = session.metadata?.user_id;
  if (!userId) return;

  const stripeSub = await stripeService.retrieveSubscription(subscriptionId);
  await subscriptionService.upsertFromStripe(
    mapStripeSubscription(userId, stripeSub, sessionCustomerId(session))
  );
}

async function handleSubscriptionUpdated(stripeSub: Stripe.Subscription): Promise<void> {
  const existing = await subscriptionService.findByStripeSubscriptionId(stripeSub.id);
  if (!existing) return;
  await subscriptionService.upsertFromStripe(
    mapStripeSubscription(existing.userId, stripeSub, customerIdOf(stripeSub))
  );
}

function mapStripeSubscription(
  userId: string,
  stripeSub: Stripe.Subscription,
  stripeCustomerId: string | null
): subscriptionService.UpsertFromStripeInput {
  const item = stripeSub.items?.data?.[0];
  const planId = (item?.price?.metadata?.plan_id as string | undefined) ?? 'basic';
  return {
    userId,
    stripeSubscriptionId: stripeSub.id,
    stripeCustomerId,
    planId,
    status: stripeSub.status,
    currentPeriodStart: new Date(stripeSub.current_period_start * 1000),
    currentPeriodEnd: new Date(stripeSub.current_period_end * 1000),
    cancelAtPeriodEnd: stripeSub.cancel_at_period_end,
  };
}

function sessionCustomerId(session: Stripe.Checkout.Session): string | null {
  if (!session.customer) return null;
  return typeof session.customer === 'string' ? session.customer : session.customer.id;
}

function customerIdOf(stripeSub: Stripe.Subscription): string | null {
  if (!stripeSub.customer) return null;
  return typeof stripeSub.customer === 'string'
    ? stripeSub.customer
    : stripeSub.customer.id;
}

/** Map a plan id ("basic"/"premium") to a Stripe price id from env config. */
function resolvePriceId(planId: string | undefined): string {
  if (!planId) return '';
  if (planId === 'premium' && env.stripePriceYearly) return env.stripePriceYearly;
  if (planId === 'basic' && env.stripePriceMonthly) return env.stripePriceMonthly;
  // Fall back to using the supplied value directly (may already be a price id).
  return planId;
}
