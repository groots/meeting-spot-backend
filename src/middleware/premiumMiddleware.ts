// Premium gating. `requirePremium` hard-blocks with 402. `softPremiumGate`
// flags the request (and a response header) without blocking, so list
// endpoints can return an empty result for non-premium users.
import { Request, Response, NextFunction } from 'express';
import { isPremium } from '../services/subscriptionService.js';
import { Unauthorized, PaymentRequired } from '../utils/errors.js';

declare global {
  // eslint-disable-next-line @typescript-eslint/no-namespace
  namespace Express {
    interface Request {
      isPremium?: boolean;
    }
  }
}

export async function requirePremium(req: Request, res: Response, next: NextFunction): Promise<void> {
  try {
    const userId = req.user?.id;
    if (!userId) throw Unauthorized();

    const premium = await isPremium(userId);
    if (!premium) {
      throw PaymentRequired('Premium subscription required', { premium_required: true });
    }
    req.isPremium = true;
    next();
  } catch (e) {
    next(e);
  }
}

export async function softPremiumGate(req: Request, res: Response, next: NextFunction): Promise<void> {
  try {
    const userId = req.user?.id;
    const premium = userId ? await isPremium(userId) : false;
    req.isPremium = premium;
    if (!premium) {
      res.setHeader('X-Premium-Required', 'true');
    }
    next();
  } catch (e) {
    next(e);
  }
}
