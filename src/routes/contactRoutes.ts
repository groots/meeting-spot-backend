import express from 'express';
import {
  listContacts,
  createContact,
  getContact,
  updateContact,
  deleteContact,
  createContactFromMeeting,
} from '../controllers/contactController.js';
import { authenticate } from '../middleware/authMiddleware.js';

const router = express.Router();

// All contact endpoints require authentication; premium gating is per-handler.
router.use(authenticate);

router.get('/', listContacts);
router.post('/', createContact);
router.post('/from-meeting/:meetingId', createContactFromMeeting);
router.get('/:id', getContact);
router.put('/:id', updateContact);
router.delete('/:id', deleteContact);

export default router;
