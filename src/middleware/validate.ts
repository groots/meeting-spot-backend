// Body-validation middleware (zod). Runs after rate limiting and before the
// controller. On failure it throws BadRequest (→ 400 in the `{ error, message }`
// shape via the central error handler). On success it replaces req.body with
// the parsed value so controllers receive clean, typed input.
import { Request, Response, NextFunction } from 'express';
import { ZodType } from 'zod';
import { BadRequest } from '../utils/errors.js';

export function validateBody(schema: ZodType) {
  return (req: Request, _res: Response, next: NextFunction): void => {
    const result = schema.safeParse(req.body ?? {});
    if (!result.success) {
      const first = result.error.issues[0];
      const path = first?.path?.join('.') ?? '';
      const message = path ? `${path}: ${first.message}` : first?.message || 'Invalid request body';
      next(BadRequest(message));
      return;
    }
    req.body = result.data;
    next();
  };
}
