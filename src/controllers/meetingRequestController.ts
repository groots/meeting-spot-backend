// Meeting request controllers.
//
// SECURITY MODEL:
// - All endpoints except POST /:id/respond require authentication (router).
// - Owner endpoints verify request.userAId === req.user.id (403 otherwise).
// - POST /:id/respond is token-gated (no auth) and returns ONLY {request_id,
//   status} — it must never leak address_a, suggestions, tokenB, or contact.
// - GET /:id/results is owner-only and returns only status/suggestions/selected.
import { Request, Response, NextFunction } from 'express';
import { Prisma } from '@prisma/client';
import * as meetingRequestService from '../services/meetingRequestService.js';
import { geocodeAddress } from '../services/geocodingService.js';
import { processMeetingRequest } from '../services/locationService.js';
import { sendMeetingInviteEmail } from '../services/emailService.js';
import { sendSms } from '../services/smsService.js';
import { decryptContact } from '../utils/encryption.js';
import { env } from '../config/env.js';
import { ContactType } from '@prisma/client';
import { BadRequest, Forbidden, NotFound, Unauthorized } from '../utils/errors.js';

/** POST / — create a meeting request (auth). Geocodes address_a on create. */
export async function createMeetingRequest(
  req: Request,
  res: Response,
  next: NextFunction
): Promise<void> {
  try {
    const userId = req.user?.id;
    if (!userId) throw Unauthorized('Not authenticated');

    const body = req.body ?? {};
    const { address_a, location_type, user_b_contact_type, user_b_contact } = body;

    if (!address_a || !location_type || !user_b_contact_type || !user_b_contact) {
      throw BadRequest('Missing required fields');
    }

    const contactType = meetingRequestService.parseContactType(user_b_contact_type);
    if (!contactType) {
      throw BadRequest('Invalid user_b_contact_type');
    }

    // Geocode address_a (fixes the Python dummy-coordinate bug).
    const geo = await geocodeAddress(address_a);
    if (!geo.success) {
      throw BadRequest(`Could not geocode address_a: ${geo.error}`);
    }

    const locationA: Prisma.InputJsonValue = {
      address: address_a,
      latitude: geo.lat,
      longitude: geo.lng,
      formatted_address: geo.formatted_address,
    };

    const created = await meetingRequestService.createMeetingRequest({
      userAId: userId,
      addressALat: geo.lat,
      addressALon: geo.lng,
      locationA,
      locationType: location_type,
      userBContactType: contactType,
      userBContact: user_b_contact,
    });

    // Email invite to User B (only for EMAIL contact type).
    if (contactType === ContactType.EMAIL) {
      try {
        await sendMeetingInviteEmail(user_b_contact, created.requestId, created.tokenB);
      } catch (e) {
        console.error('Failed to send meeting invite email:', e);
      }
    }

    res.status(201).json(meetingRequestService.toCreatedDto(created));
  } catch (e) {
    next(e);
  }
}

/** GET / — list the caller's meeting requests (auth, owner). */
export async function listMeetingRequests(
  req: Request,
  res: Response,
  next: NextFunction
): Promise<void> {
  try {
    const userId = req.user?.id;
    if (!userId) throw Unauthorized('Not authenticated');

    const requests = await meetingRequestService.listByUserA(userId);
    res.status(200).json(requests.map((r) => meetingRequestService.toOwnerDto(r)));
  } catch (e) {
    next(e);
  }
}

/** GET /:id — owner view of a single request (auth). */
export async function getMeetingRequest(
  req: Request,
  res: Response,
  next: NextFunction
): Promise<void> {
  try {
    const userId = req.user?.id;
    if (!userId) throw Unauthorized('Not authenticated');

    const request = await meetingRequestService.findById(req.params.id);
    if (!request) throw NotFound('Meeting request not found');
    if (request.userAId !== userId) throw Forbidden('Unauthorized');

    res.status(200).json(meetingRequestService.toOwnerDto(request));
  } catch (e) {
    next(e);
  }
}

/** PUT /:id — owner update (auth). address_b → CALCULATING; or set status. */
export async function updateMeetingRequest(
  req: Request,
  res: Response,
  next: NextFunction
): Promise<void> {
  try {
    const userId = req.user?.id;
    if (!userId) throw Unauthorized('Not authenticated');

    const request = await meetingRequestService.findById(req.params.id);
    if (!request) throw NotFound('Meeting request not found');
    if (request.userAId !== userId) throw Forbidden('Unauthorized');

    const data = req.body ?? {};
    const update: Prisma.MeetingRequestUpdateInput = { updatedAt: new Date() };

    if (data.address_b_lat !== undefined && data.address_b_lon !== undefined) {
      update.addressBLat = data.address_b_lat;
      update.addressBLon = data.address_b_lon;
      update.status = 'CALCULATING';
    } else if (data.status !== undefined) {
      const status = meetingRequestService.parseStatus(data.status);
      if (!status) throw BadRequest('Invalid status value');
      update.status = status;
    }

    if (data.meeting_location !== undefined) {
      // Agreeing on a place finalizes the request.
      update.selectedPlaceDetails = data.meeting_location;
      update.status = 'COMPLETED';
    }

    const updated = await meetingRequestService.updateRequest(request.requestId, update);
    res.status(200).json(meetingRequestService.toOwnerDto(updated));
  } catch (e) {
    next(e);
  }
}

/** DELETE /:id — owner delete (auth). 204. */
export async function deleteMeetingRequest(
  req: Request,
  res: Response,
  next: NextFunction
): Promise<void> {
  try {
    const userId = req.user?.id;
    if (!userId) throw Unauthorized('Not authenticated');

    const request = await meetingRequestService.findById(req.params.id);
    if (!request) throw NotFound('Meeting request not found');
    if (request.userAId !== userId) throw Forbidden('Unauthorized');

    await meetingRequestService.deleteRequest(request.requestId);
    res.status(204).send();
  } catch (e) {
    next(e);
  }
}

/**
 * GET /:id/status — accessible to the authenticated owner OR to User B via the
 * invite `?token=` (matches tokenB). The status DTO carries no sensitive data
 * (only request_id/status/timestamps), so token-gated read is safe.
 */
export async function getMeetingRequestStatus(
  req: Request,
  res: Response,
  next: NextFunction
): Promise<void> {
  try {
    const request = await meetingRequestService.findById(req.params.id);
    if (!request) throw NotFound('Meeting request not found');

    const userId = req.user?.id;
    const token = typeof req.query.token === 'string' ? req.query.token : undefined;
    const isOwner = Boolean(userId) && request.userAId === userId;
    const isInvitee = meetingRequestService.tokenMatches(request.tokenB, token);
    if (!isOwner && !isInvitee) throw Forbidden('Unauthorized');

    res.status(200).json(meetingRequestService.toStatusDto(request));
  } catch (e) {
    next(e);
  }
}

/**
 * POST /:id/respond — NO auth, token-gated. User B submits their coordinates.
 * Validates token + expiry, persists coords + CALCULATING, runs processing
 * synchronously, then returns EXACTLY {request_id, status}. On processing error,
 * marks FAILED and still returns only {request_id, status}.
 */
export async function respondToMeetingRequest(
  req: Request,
  res: Response,
  next: NextFunction
): Promise<void> {
  try {
    const data = req.body ?? {};
    const { token, address_b_lat, address_b_lon } = data;

    if (
      token === undefined ||
      address_b_lat === undefined ||
      address_b_lon === undefined
    ) {
      throw BadRequest('Missing required fields');
    }

    const request = await meetingRequestService.findById(req.params.id);
    if (!request) throw NotFound('Meeting request not found');

    // Timing-safe token check (mismatch and expiry both → 403, generic message).
    if (!meetingRequestService.tokenMatches(request.tokenB, token)) {
      throw Forbidden('Invalid token');
    }
    if (meetingRequestService.isExpired(request)) {
      throw Forbidden('Meeting request has expired');
    }

    // Single-use claim: atomically flip tokenBUsedAt NULL → now while persisting
    // B's coordinates + CALCULATING. If 0 rows affected the token was already
    // used (double-submit / replay) → generic 403 (no enumeration).
    const claimed = await meetingRequestService.claimTokenForResponse(
      request.requestId,
      address_b_lat,
      address_b_lon
    );
    if (claimed === 0) {
      throw Forbidden('Invalid token');
    }

    // Run the matching pipeline synchronously, then persist its outcome.
    try {
      const result = await processMeetingRequest({
        requestId: request.requestId,
        addressALat: request.addressALat,
        addressALon: request.addressALon,
        addressBLat: address_b_lat,
        addressBLon: address_b_lon,
        locationType: request.locationType,
      });

      await meetingRequestService.updateRequest(request.requestId, {
        // Suggestions generated → READY (awaiting the owner to agree on a place).
        // COMPLETED is reserved for when a place has actually been selected.
        status: result.status === 'completed' ? 'READY' : 'FAILED',
        suggestedOptions:
          result.suggestedOptions !== null
            ? (result.suggestedOptions as unknown as Prisma.InputJsonValue)
            : Prisma.JsonNull,
        updatedAt: new Date(),
      });
    } catch (e) {
      console.error('Error processing meeting request:', e);
      await meetingRequestService.updateRequest(request.requestId, {
        status: 'FAILED',
        updatedAt: new Date(),
      });
    }

    const fresh = await meetingRequestService.findById(request.requestId);
    // fresh cannot be null here (we just updated it), but guard for types.
    res
      .status(200)
      .json(
        fresh
          ? meetingRequestService.toRespondDto(fresh)
          : { request_id: request.requestId, status: 'failed' }
      );
  } catch (e) {
    next(e);
  }
}

/**
 * GET /:id/results — accessible to the authenticated owner OR to User B via the
 * invite `?token=` (matches tokenB). The results DTO exposes only status +
 * suggestions + selected place (no address_a, tokenB, or contact), which both
 * participants are meant to see.
 */
export async function getMeetingRequestResults(
  req: Request,
  res: Response,
  next: NextFunction
): Promise<void> {
  try {
    const request = await meetingRequestService.findById(req.params.id);
    if (!request) throw NotFound('Meeting request not found');

    const userId = req.user?.id;
    const token = typeof req.query.token === 'string' ? req.query.token : undefined;
    const isOwner = Boolean(userId) && request.userAId === userId;
    const isInvitee = meetingRequestService.tokenMatches(request.tokenB, token);
    if (!isOwner && !isInvitee) throw Forbidden('Unauthorized');

    const dto = meetingRequestService.toResultsDto(request);

    // OWNER ONLY: expose User B's email so the owner can save them as a contact.
    // This is not a new leak — the owner supplied this email when creating the
    // request. It is NEVER attached on the invitee/token path.
    if (isOwner && request.userBContactType === ContactType.EMAIL) {
      try {
        dto.meeting_contact_info = { email: decryptContact(request.userBContactEncrypted) };
      } catch {
        // If decryption fails, omit the field rather than failing the request.
      }
    }

    res.status(200).json(dto);
  } catch (e) {
    next(e);
  }
}

/**
 * POST /:id/resend-invitation — owner only (auth). Re-sends the invite to User B
 * using the stored (encrypted) contact and the existing tokenB. Returns a
 * generic success; never leaks the contact value or token.
 */
export async function resendInvitation(
  req: Request,
  res: Response,
  next: NextFunction
): Promise<void> {
  try {
    const userId = req.user?.id;
    if (!userId) throw Unauthorized('Not authenticated');

    const request = await meetingRequestService.findById(req.params.id);
    if (!request) throw NotFound('Meeting request not found');
    if (request.userAId !== userId) throw Forbidden('Unauthorized');

    if (meetingRequestService.isExpired(request)) {
      throw BadRequest('Meeting request has expired');
    }

    const contact = decryptContact(request.userBContactEncrypted);

    if (request.userBContactType === ContactType.EMAIL) {
      await sendMeetingInviteEmail(contact, request.requestId, request.tokenB);
    } else {
      const inviteUrl = `${env.frontendUrl}/request/${request.requestId}?token=${request.tokenB}`;
      await sendSms(
        contact,
        `You've been invited to find a meeting spot. Share your location: ${inviteUrl}`
      );
    }

    res.status(200).json({ message: 'Invitation resent successfully' });
  } catch (e) {
    next(e);
  }
}
