import express from 'express';
import {
  createMeetingRequest,
  listMeetingRequests,
  getMeetingRequest,
  updateMeetingRequest,
  deleteMeetingRequest,
  getMeetingRequestStatus,
  respondToMeetingRequest,
  getMeetingRequestResults,
  resendInvitation,
  chooseMeetingPlace,
  refineSuggestions,
  sendDirections,
  proposeMeetingTime,
  getAvailability,
  getCalendarLinks,
  sendCalendar,
} from '../controllers/meetingRequestController.js';
import { authenticate, authenticateOptional } from '../middleware/authMiddleware.js';
import { softPremiumGate } from '../middleware/premiumMiddleware.js';
import { respondLimiter } from '../middleware/rateLimit.js';
import { validateBody } from '../middleware/validate.js';
import {
  createMeetingRequestSchema,
  respondSchema,
  chooseSchema,
  sendDirectionsSchema,
  scheduleSchema,
  sendCalendarSchema,
  refineSchema,
} from '../schemas/meetingRequestSchemas.js';

const router = express.Router();

// Public, token-gated endpoints (User B from the invite link). Declared before
// the authenticated routes; they do NOT require `authenticate`. status/results
// use optional auth so the owner (Bearer) OR User B (?token=) can read them; the
// controllers enforce owner-id-or-tokenB.
router.post('/:id/respond', respondLimiter, validateBody(respondSchema), respondToMeetingRequest);
router.get('/:id/status', authenticateOptional, getMeetingRequestStatus);
router.get('/:id/results', authenticateOptional, getMeetingRequestResults);

// Collaborative selection (optional auth: owner via Bearer OR invitee via token
// in the body; the controller enforces role + mode). send-directions reuses the
// respondLimiter to bound SMS abuse.
router.post('/:id/choose', authenticateOptional, validateBody(chooseSchema), chooseMeetingPlace);
router.post(
  '/:id/send-directions',
  respondLimiter,
  authenticateOptional,
  validateBody(sendDirectionsSchema),
  sendDirections
);

// Scheduling (Phase 1). Mirrors the place-selection gate: optional auth (owner
// via Bearer OR invitee via token); the controller enforces role + mode. Time
// selection happens after the place is locked (status='completed'). schedule &
// calendar reads are owner-or-tokenB; send-calendar reuses respondLimiter.
router.post('/:id/schedule', authenticateOptional, validateBody(scheduleSchema), proposeMeetingTime);
router.get('/:id/availability', authenticateOptional, getAvailability);
router.get('/:id/calendar', authenticateOptional, getCalendarLinks);
router.post(
  '/:id/send-calendar',
  respondLimiter,
  authenticateOptional,
  validateBody(sendCalendarSchema),
  sendCalendar
);

// Owner-only refine (re-run suggestions, no new invite). softPremiumGate flags
// req.isPremium (and the X-Premium-Required header for non-premium) so the
// controller can gate the travel-time fairness re-rank without hard-blocking.
router.post(
  '/:id/refine',
  authenticate,
  softPremiumGate,
  validateBody(refineSchema),
  refineSuggestions
);

// All remaining endpoints require authentication.
router.post('/', authenticate, validateBody(createMeetingRequestSchema), createMeetingRequest);
router.get('/', authenticate, listMeetingRequests);
router.get('/:id', authenticate, getMeetingRequest);
router.put('/:id', authenticate, updateMeetingRequest);
router.delete('/:id', authenticate, deleteMeetingRequest);
router.post('/:id/resend-invitation', authenticate, resendInvitation);

export default router;
