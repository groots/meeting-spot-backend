import express from 'express';
import {
  register,
  login,
  getCurrentUser,
  googleCallback,
  refreshToken,
} from '../controllers/authController';
import { authenticate } from '../middleware/authMiddleware';

const router = express.Router();

// Authentication routes - using the same paths as the Python backend
router.post('/register', register);
router.post('/register/direct', register); // Legacy endpoint, uses same handler
router.post('/login', login);
router.post('/login/direct', login); // Legacy endpoint, uses same handler
router.post('/direct-login', login); // Another legacy endpoint

// Google authentication
router.post('/google/callback', googleCallback);

// Token refresh
router.post('/refresh', refreshToken);

// Get current user - requires authentication
router.get('/me', authenticate, getCurrentUser);

export default router;
