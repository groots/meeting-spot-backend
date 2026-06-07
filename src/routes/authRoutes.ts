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

const router = express.Router();

// Registration / login (legacy aliases share handlers)
router.post('/register', register);
router.post('/register/direct', register);
router.post('/login', login);
router.post('/login/direct', login);
router.post('/direct-login', login);

// Google authentication (direct alias verifies the same way)
router.post('/google/callback', googleCallback);
router.post('/google/callback/direct', googleCallback);

// Facebook authentication (direct alias verifies the same way)
router.post('/facebook/callback', facebookCallback);
router.post('/facebook/callback/direct', facebookCallback);

// Token refresh
router.post('/refresh', refreshToken);

// Password reset (always generic 200)
router.post('/reset-password', resetPassword);
router.post('/reset-password/confirm', resetPasswordConfirm);

// Email verification
router.post('/verify-email', verifyEmail);
router.post('/resend-verification', resendVerification);

// Current user
router.get('/me', authenticate, getCurrentUser);

// Profile picture upload / serve
router.post('/me/picture', authenticate, uploadPicture);
router.get('/profile/picture/:filename', getProfilePicture);

export default router;
