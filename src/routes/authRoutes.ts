import express from 'express';
import {
  register,
  login,
  getCurrentUser,
  googleCallback,
  facebookCallback,
  refreshToken,
  resetPassword,
  resetPasswordConfirm,
  verifyEmail,
  resendVerification,
  uploadPicture,
  getProfilePicture,
} from '../controllers/authController.js';
import { authenticate } from '../middleware/authMiddleware.js';
import { authLimiter } from '../middleware/rateLimit.js';
import { validateBody } from '../middleware/validate.js';
import {
  loginSchema,
  registerSchema,
  resetPasswordSchema,
  resetPasswordConfirmSchema,
  resendVerificationSchema,
} from '../schemas/authSchemas.js';

const router = express.Router();

// Registration / login (legacy aliases share handlers)
router.post('/register', authLimiter, validateBody(registerSchema), register);
router.post('/register/direct', authLimiter, validateBody(registerSchema), register);
router.post('/login', authLimiter, validateBody(loginSchema), login);
router.post('/login/direct', authLimiter, validateBody(loginSchema), login);
router.post('/direct-login', authLimiter, validateBody(loginSchema), login);

// Google authentication (direct alias verifies the same way)
router.post('/google/callback', googleCallback);
router.post('/google/callback/direct', googleCallback);

// Facebook authentication (direct alias verifies the same way)
router.post('/facebook/callback', facebookCallback);
router.post('/facebook/callback/direct', facebookCallback);

// Token refresh
router.post('/refresh', authLimiter, refreshToken);

// Password reset (always generic 200)
router.post('/reset-password', authLimiter, validateBody(resetPasswordSchema), resetPassword);
router.post(
  '/reset-password/confirm',
  authLimiter,
  validateBody(resetPasswordConfirmSchema),
  resetPasswordConfirm
);

// Email verification
router.post('/verify-email', verifyEmail);
router.post(
  '/resend-verification',
  authLimiter,
  validateBody(resendVerificationSchema),
  resendVerification
);

// Current user
router.get('/me', authenticate, getCurrentUser);

// Profile picture upload / serve
router.post('/me/picture', authenticate, uploadPicture);
router.get('/profile/picture/:filename', getProfilePicture);

export default router;
