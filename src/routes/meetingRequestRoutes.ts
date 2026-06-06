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
} from '../controllers/meetingRequestController.js';
import { authenticate } from '../middleware/authMiddleware.js';

const router = express.Router();

// Public, token-gated endpoint (User B submitting their address). Declared
// before the authenticated routes; it does NOT use `authenticate`.
router.post('/:id/respond', respondToMeetingRequest);

// All remaining endpoints require authentication.
router.post('/', authenticate, createMeetingRequest);
router.get('/', authenticate, listMeetingRequests);
router.get('/:id', authenticate, getMeetingRequest);
router.put('/:id', authenticate, updateMeetingRequest);
router.delete('/:id', authenticate, deleteMeetingRequest);
router.get('/:id/status', authenticate, getMeetingRequestStatus);
router.get('/:id/results', authenticate, getMeetingRequestResults);

export default router;
