// Typed HTTP error used across controllers/services. The central errorHandler
// serializes these to `{ error, message }` with the right status code.

export class HttpError extends Error {
  status: number;
  // Short machine-ish label used as the `error` field; defaults per status.
  errorLabel: string;
  // Optional extra fields merged into the JSON response (e.g. premium_required).
  details?: Record<string, unknown>;

  constructor(status: number, message: string, errorLabel?: string, details?: Record<string, unknown>) {
    super(message);
    this.name = 'HttpError';
    this.status = status;
    this.errorLabel = errorLabel ?? defaultLabel(status);
    this.details = details;
  }
}

function defaultLabel(status: number): string {
  switch (status) {
    case 400:
      return 'Bad request';
    case 401:
      return 'Unauthorized';
    case 402:
      return 'Payment required';
    case 403:
      return 'Forbidden';
    case 404:
      return 'Not found';
    case 409:
      return 'Conflict';
    case 429:
      return 'Too many requests';
    default:
      return 'Server error';
  }
}

export const BadRequest = (message: string, details?: Record<string, unknown>) =>
  new HttpError(400, message, 'Bad request', details);
export const Unauthorized = (message = 'Not authenticated', details?: Record<string, unknown>) =>
  new HttpError(401, message, 'Unauthorized', details);
export const PaymentRequired = (message = 'Premium subscription required', details?: Record<string, unknown>) =>
  new HttpError(402, message, 'Payment required', details);
export const Forbidden = (message = 'Access forbidden', details?: Record<string, unknown>) =>
  new HttpError(403, message, 'Forbidden', details);
export const NotFound = (message = 'Resource not found', details?: Record<string, unknown>) =>
  new HttpError(404, message, 'Not found', details);
export const Conflict = (message: string, details?: Record<string, unknown>) =>
  new HttpError(409, message, 'Conflict', details);
export const TooManyRequests = (message = 'Too many requests', details?: Record<string, unknown>) =>
  new HttpError(429, message, 'Too many requests', details);
