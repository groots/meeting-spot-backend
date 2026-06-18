// Per-IP rate limiters (express-rate-limit). Keyed on req.ip, which is the real
// client IP because server.ts sets `trust proxy = 1` (Render's single proxy).
//
// All limiters emit 429 in the app-wide `{ error, message }` shape via the
// shared handler. Limiters are disabled under NODE_ENV=test so the existing
// suites can hammer endpoints without tripping limits.
import rateLimit, { Options } from 'express-rate-limit';
import { Request, Response } from 'express';
import { env } from '../config/env.js';
import { TooManyRequests } from '../utils/errors.js';

const FIFTEEN_MINUTES = 15 * 60 * 1000;

// Shared 429 handler: serialize through the same HttpError → { error, message }.
function tooManyHandler(message: string) {
  return (_req: Request, res: Response): void => {
    const err = TooManyRequests(message);
    res.status(err.status).json({ error: err.errorLabel, message: err.message });
  };
}

const baseOptions: Partial<Options> = {
  windowMs: FIFTEEN_MINUTES,
  standardHeaders: true,
  legacyHeaders: false,
  // Disable entirely in tests so existing suites aren't rate-limited.
  skip: () => env.isTest,
};

// Auth-sensitive endpoints (login/register/refresh/reset/verify). Tight cap to
// blunt credential stuffing and slow-hash DoS.
export const authLimiter = rateLimit({
  ...baseOptions,
  limit: 10,
  handler: tooManyHandler('Too many authentication attempts. Please try again later.'),
});

// User B coordinate submission. Token-gated but unauthenticated, so cap per IP.
export const respondLimiter = rateLimit({
  ...baseOptions,
  limit: 10,
  handler: tooManyHandler('Too many submissions. Please try again later.'),
});

// Geocoding proxy. Protects the Google Maps key/cost from abuse.
export const geocodeLimiter = rateLimit({
  ...baseOptions,
  limit: 30,
  handler: tooManyHandler('Too many geocoding requests. Please try again later.'),
});
