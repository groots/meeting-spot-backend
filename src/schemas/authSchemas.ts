// Zod schemas for auth request bodies. Kept intentionally permissive where the
// existing API is permissive; the goal is to reject obviously-malformed bodies
// before they reach controllers, not to tighten the public contract.
import { z } from 'zod';

const email = z.string().trim().min(1, 'Email is required').email('Invalid email address');
const password = z.string().min(8, 'Password must be at least 8 characters');

// Login must allow unknown keys: the frontend also sends `remember_me`.
export const loginSchema = z
  .object({
    email,
    password: z.string().min(1, 'Password is required'),
  })
  .passthrough();

export const registerSchema = z
  .object({
    email,
    password,
    first_name: z.string().optional(),
    last_name: z.string().optional(),
    username: z.string().optional(),
    phone: z.string().optional(),
  })
  .passthrough();

export const resetPasswordSchema = z
  .object({
    email,
  })
  .passthrough();

export const resetPasswordConfirmSchema = z
  .object({
    token: z.string().min(1, 'Token is required'),
    password,
  })
  .passthrough();

export const resendVerificationSchema = z
  .object({
    email,
  })
  .passthrough();
