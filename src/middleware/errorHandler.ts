// Central error handler + 404. Converts HttpError into `{ error, message }`
// (plus any extra details) and falls back to 500 for unexpected errors.
import { Request, Response, NextFunction } from 'express';
import { HttpError } from '../utils/errors.js';
import { env } from '../config/env.js';

export function notFoundHandler(req: Request, res: Response): void {
  res.status(404).json({
    error: 'Route not found',
    message: `Cannot ${req.method} ${req.originalUrl}`,
  });
}

// eslint-disable-next-line @typescript-eslint/no-unused-vars
export function errorHandler(err: unknown, req: Request, res: Response, _next: NextFunction): void {
  if (err instanceof HttpError) {
    res.status(err.status).json({
      error: err.errorLabel,
      message: err.message,
      ...(err.details ?? {}),
    });
    return;
  }

  console.error('Unhandled error:', err);
  res.status(500).json({
    error: 'Internal server error',
    message: env.isProduction ? 'Something went wrong' : (err as Error)?.message ?? 'Unknown error',
  });
}
