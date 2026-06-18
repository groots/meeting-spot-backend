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
} from '../controllers/meetingRequestController.js';
import { authenticate, authenticateOptional } from '../middleware/authMiddleware.js';
import { respondLimiter } from '../middleware/rateLimit.js';
import { validateBody } from '../middleware/validate.js';
import {
  createMeetingRequestSchema,
  respondSchema,
} from '../schemas/meetingRequestSchemas.js';

const router = express.Router();

// Public, token-gated endpoints (User B from the invite link). Declared before
// the authenticated routes; they do NOT require `authenticate`. status/results
// use optional auth so the owner (Bearer) OR User B (?token=) can read them; the
// controllers enforce owner-id-or-tokenB.
router.post('/:id/respond', respondLimiter, validateBody(respondSchema), respondToMeetingRequest);
router.get('/:id/status', authenticateOptional, getMeetingRequestStatus);
router.get('/:id/results', authenticateOptional, getMeetingRequestResults);

// All remaining endpoints require authentication.
router.post('/', authenticate, validateBody(createMeetingRequestSchema), createMeetingRequest);
router.get('/', authenticate, listMeetingRequests);
router.get('/:id', authenticate, getMeetingRequest);
router.put('/:id', authenticate, updateMeetingRequest);
router.delete('/:id', authenticate, deleteMeetingRequest);
router.post('/:id/resend-invitation', authenticate, resendInvitation);

export default router;
