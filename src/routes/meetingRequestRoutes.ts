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

const router = express.Router();

// Public, token-gated endpoints (User B from the invite link). Declared before
// the authenticated routes; they do NOT require `authenticate`. status/results
// use optional auth so the owner (Bearer) OR User B (?token=) can read them; the
// controllers enforce owner-id-or-tokenB.
router.post('/:id/respond', respondToMeetingRequest);
router.get('/:id/status', authenticateOptional, getMeetingRequestStatus);
router.get('/:id/results', authenticateOptional, getMeetingRequestResults);

// All remaining endpoints require authentication.
router.post('/', authenticate, createMeetingRequest);
router.get('/', authenticate, listMeetingRequests);
router.get('/:id', authenticate, getMeetingRequest);
router.put('/:id', authenticate, updateMeetingRequest);
router.delete('/:id', authenticate, deleteMeetingRequest);
router.post('/:id/resend-invitation', authenticate, resendInvitation);

export default router;
