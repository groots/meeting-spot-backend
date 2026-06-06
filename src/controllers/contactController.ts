// Contact controllers. Premium gating mirrors the Python contacts blueprint:
// - GET /        : soft gate (non-premium → [] + X-Premium-Required header)
// - POST/PUT/DELETE/from-meeting : hard gate (402 for non-premium)
// - GET /:id     : premium → meeting history; non-premium → meeting_count only
import { Request, Response, NextFunction } from 'express';
import { ContactType } from '@prisma/client';
import * as contactService from '../services/contactService.js';
import * as meetingRequestService from '../services/meetingRequestService.js';
import { isPremium } from '../services/subscriptionService.js';
import { decryptContact } from '../utils/encryption.js';
import { BadRequest, Forbidden, NotFound, PaymentRequired, Unauthorized } from '../utils/errors.js';

const PREMIUM_MESSAGE =
  'This feature requires a premium subscription. Please upgrade your plan to use contacts management.';

/** GET / — soft-gated list. */
export async function listContacts(
  req: Request,
  res: Response,
  next: NextFunction
): Promise<void> {
  try {
    const userId = req.user?.id;
    if (!userId) throw Unauthorized('Not authenticated');

    if (!(await isPremium(userId))) {
      res.setHeader('X-Premium-Required', 'true');
      res.setHeader('X-Premium-Feature', 'contacts');
      res.status(200).json([]);
      return;
    }

    const contacts = await contactService.listByUser(userId);
    res.status(200).json(contacts.map((c) => contactService.toDict(c)));
  } catch (e) {
    next(e);
  }
}

/** POST / — hard-gated create. */
export async function createContact(
  req: Request,
  res: Response,
  next: NextFunction
): Promise<void> {
  try {
    const userId = req.user?.id;
    if (!userId) throw Unauthorized('Not authenticated');
    if (!(await isPremium(userId))) throw PaymentRequired(PREMIUM_MESSAGE);

    const data = req.body ?? {};
    if (!data.name) throw BadRequest('Name is required');

    const contact = await contactService.createContact(userId, {
      name: data.name,
      email: data.email,
      phone: data.phone,
      company: data.company,
      notes: data.notes,
    });
    res.status(201).json(contactService.toDict(contact));
  } catch (e) {
    next(e);
  }
}

/** GET /:id — premium adds meeting history; non-premium gets meeting_count. */
export async function getContact(
  req: Request,
  res: Response,
  next: NextFunction
): Promise<void> {
  try {
    const userId = req.user?.id;
    if (!userId) throw Unauthorized('Not authenticated');

    const contact = await contactService.findByIdForUser(req.params.id, userId);
    if (!contact) throw NotFound(`Contact ${req.params.id} not found`);

    const result = contactService.toDict(contact);

    if (await isPremium(userId)) {
      const meetings = await contactService.findMeetingsForContact(contact.id);
      result.meetings = meetings.map((m) => {
        const entry: Record<string, unknown> = {
          id: m.requestId,
          status: m.status,
          created_at: m.createdAt.toISOString(),
          updated_at: m.updatedAt.toISOString(),
        };
        if (m.selectedPlace) {
          entry.selected_place = {
            name: m.selectedPlace.name,
            address: m.selectedPlace.address,
            google_place_id: m.selectedPlace.googlePlaceId,
          };
        }
        return entry;
      });
    } else {
      result.meeting_count = await contactService.countMeetings(contact.id);
      result.premium_required = true;
    }

    res.status(200).json(result);
  } catch (e) {
    next(e);
  }
}

/** PUT /:id — hard-gated update. */
export async function updateContact(
  req: Request,
  res: Response,
  next: NextFunction
): Promise<void> {
  try {
    const userId = req.user?.id;
    if (!userId) throw Unauthorized('Not authenticated');
    if (!(await isPremium(userId))) throw PaymentRequired(PREMIUM_MESSAGE);

    const contact = await contactService.findByIdForUser(req.params.id, userId);
    if (!contact) throw NotFound(`Contact ${req.params.id} not found`);

    const data = req.body ?? {};
    const update: Record<string, unknown> = { updatedAt: new Date() };
    for (const field of ['name', 'email', 'phone', 'company', 'notes'] as const) {
      if (field in data) update[field] = data[field];
    }

    const updated = await contactService.updateContact(contact.id, update);
    res.status(200).json(contactService.toDict(updated));
  } catch (e) {
    next(e);
  }
}

/** DELETE /:id — hard-gated delete. */
export async function deleteContact(
  req: Request,
  res: Response,
  next: NextFunction
): Promise<void> {
  try {
    const userId = req.user?.id;
    if (!userId) throw Unauthorized('Not authenticated');
    if (!(await isPremium(userId))) throw PaymentRequired(PREMIUM_MESSAGE);

    const contact = await contactService.findByIdForUser(req.params.id, userId);
    if (!contact) throw NotFound(`Contact ${req.params.id} not found`);

    await contactService.deleteContact(contact.id);
    res.status(200).json({ message: `Contact ${req.params.id} deleted successfully` });
  } catch (e) {
    next(e);
  }
}

/** POST /from-meeting/:meetingId — hard-gated; creates a contact from a meeting. */
export async function createContactFromMeeting(
  req: Request,
  res: Response,
  next: NextFunction
): Promise<void> {
  try {
    const userId = req.user?.id;
    if (!userId) throw Unauthorized('Not authenticated');
    if (!(await isPremium(userId))) throw PaymentRequired(PREMIUM_MESSAGE);

    const meeting = await meetingRequestService.findById(req.params.meetingId);
    if (!meeting) throw NotFound(`Meeting request ${req.params.meetingId} not found`);
    if (meeting.userAId !== userId) {
      throw Forbidden('You are not authorized to access this meeting request');
    }

    // Derive User B's email from the meeting (EMAIL contact type only).
    let email: string | null = null;
    if (meeting.userBContactType === ContactType.EMAIL) {
      try {
        email = decryptContact(meeting.userBContactEncrypted);
      } catch {
        email = null;
      }
    }

    const data = req.body ?? {};
    const contact = await contactService.createContact(userId, {
      name: data.name ?? '',
      email,
      phone: data.phone,
      company: data.company,
      notes: data.notes,
    });

    // Associate the contact with the meeting request.
    await meetingRequestService.updateRequest(meeting.requestId, {
      contacts: { connect: { id: contact.id } },
    });

    res.status(201).json(contactService.toDict(contact));
  } catch (e) {
    next(e);
  }
}
