import express from 'express';
import {
  getPlans,
  getPrices,
  getSubscriptions,
  createSubscription,
  getSubscription,
  cancelSubscription,
  createCheckout,
  listPaymentMethods,
  webhook,
} from '../controllers/paymentController.js';
import { authenticate } from '../middleware/authMiddleware.js';

const router = express.Router();

// Public endpoints.
router.get('/plans', getPlans);
router.get('/prices', getPrices);

// Stripe webhook (no auth; raw body is provided by an express.raw middleware
// mounted on this exact path BEFORE express.json in server.ts).
router.post('/webhook', webhook);

// Authenticated subscription management.
router.get('/subscriptions', authenticate, getSubscriptions);
router.post('/subscriptions', authenticate, createSubscription);
router.get('/subscriptions/:id', authenticate, getSubscription);
router.delete('/subscriptions/:id', authenticate, cancelSubscription);
router.post('/checkout', authenticate, createCheckout);
router.get('/payment-methods', authenticate, listPaymentMethods);

export default router;
