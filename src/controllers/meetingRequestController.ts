// Meeting request controllers.
//
// SECURITY MODEL:
// - All endpoints except POST /:id/respond require authentication (router).
// - Owner endpoints verify request.userAId === req.user.id (403 otherwise).
// - POST /:id/respond is token-gated (no auth) and returns ONLY {request_id,
//   status} — it must never leak address_a, suggestions, tokenB, or contact.
// - GET /:id/results is owner-only and returns only status/suggestions/selected.
import { Request, Response, NextFunction } from 'express';
import { Prisma, SelectionMode } from '@prisma/client';
import * as meetingRequestService from '../services/meetingRequestService.js';
import * as userService from '../services/userService.js';
import { geocodeAddress } from '../services/geocodingService.js';
import { processMeetingRequest } from '../services/locationService.js';
import { parseTimeOfDay } from '../utils/openingHours.js';
import { isPremium } from '../services/subscriptionService.js';
import { sendMeetingInviteEmail, sendMeetingScheduledEmail } from '../services/emailService.js';
import { sendSms } from '../services/smsService.js';
import { decryptContact } from '../utils/encryption.js';
import { buildDirectionsUrl } from '../utils/directions.js';
import { buildCalendarUrl, buildIcs, endFromDuration, CalendarEvent } from '../utils/calendar.js';
import { computeMeetingAvailability } from '../services/availabilityService.js';
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
    const {
      address_a,
      location_type,
      user_b_contact_type,
      user_b_contact,
      selection_mode,
      time_of_day,
    } = body;

    if (!address_a || !location_type || !user_b_contact_type || !user_b_contact) {
      throw BadRequest('Missing required fields');
    }

    const contactType = meetingRequestService.parseContactType(user_b_contact_type);
    if (!contactType) {
      throw BadRequest('Invalid user_b_contact_type');
    }

    const selectionMode = meetingRequestService.parseSelectionMode(selection_mode);
    // Optional time-of-day preference; invalid values are ignored (no filter).
    const preferredTimeOfDay = parseTimeOfDay(time_of_day);

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
      selectionMode,
      preferredTimeOfDay,
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

    // Premium owners get the travel-time fairness re-rank on their initial
    // results. Resolve against the OWNER (userAId), not the token-bearing
    // invitee. Defensive: any lookup failure degrades to distance ranking.
    let ownerIsPremium = false;
    try {
      ownerIsPremium = request.userAId ? await isPremium(request.userAId) : false;
    } catch {
      ownerIsPremium = false;
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
        isPremium: ownerIsPremium,
        timeOfDay: parseTimeOfDay(request.preferredTimeOfDay),
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

/**
 * POST /:id/choose — record a participant's venue pick (optional auth).
 *
 * Role is resolved from the request itself: the authenticated owner (Bearer,
 * userAId === user) chooses as "A"; the invitee (matching tokenB in the body)
 * chooses as "B". We DO NOT consume the single-use tokenBUsedAt here — the
 * invitee may re-pick until agreement; that marker stays exclusive to /respond.
 *
 * OWNER mode: only the owner may choose (the invitee is read-only). MUTUAL mode:
 * either party may choose, and agreement finalizes the request (see
 * recordChoice). Incoming choices are validated against suggested_options so a
 * caller can't inject an arbitrary venue.
 */
export async function chooseMeetingPlace(
  req: Request,
  res: Response,
  next: NextFunction
): Promise<void> {
  try {
    const body = req.body ?? {};
    const { token, place } = body;

    const request = await meetingRequestService.findById(req.params.id);
    if (!request) throw NotFound('Meeting request not found');

    // Resolve role (owner via Bearer, invitee via tokenB) or reject.
    const userId = req.user?.id;
    const isOwner = Boolean(userId) && request.userAId === userId;
    const isInvitee = meetingRequestService.tokenMatches(request.tokenB, token);
    if (!isOwner && !isInvitee) throw Forbidden('Unauthorized');

    // Suggestions must exist (ready/completed) and the request must not already
    // be finalized — once a place is locked in, no further picks are accepted.
    const status = meetingRequestService.statusValue(request.status);
    if (status !== 'ready' && status !== 'completed') {
      throw BadRequest('Meeting is not ready for selection');
    }
    if (request.selectedPlaceDetails) {
      throw BadRequest('A meeting place has already been finalized');
    }

    // OWNER mode: invitee is read-only.
    if (request.selectionMode === SelectionMode.OWNER && !isOwner) {
      throw Forbidden('Only the organizer can choose the meeting place');
    }

    // The choice must be one of the server-generated suggestions.
    if (!meetingRequestService.placeMatchesSuggestion(request, place)) {
      throw BadRequest('Selected place is not one of the suggested options');
    }

    const role: 'A' | 'B' = isOwner ? 'A' : 'B';
    const updated = await meetingRequestService.recordChoice(request, role, place);

    res.status(200).json(meetingRequestService.toChooseDto(updated));
  } catch (e) {
    next(e);
  }
}

/**
 * POST /:id/refine — owner-only re-run of the suggestion engine with new params
 * (location_type / open_now / radius / max_results / objective) WITHOUT issuing
 * a new invite. Allowed only while the request is `ready` (suggestions exist but
 * nothing is finalized); blocked once a place or time is locked.
 *
 * Premium gates the travel-time fairness re-rank: softPremiumGate sets
 * req.isPremium, which we pass to processMeetingRequest. Non-premium refines
 * keep the distance-based ordering. Stale choices that fall out of the new
 * option set are cleared so MUTUAL agreement can't lock onto a vanished venue.
 */
export async function refineSuggestions(
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

    // Only refine while suggestions exist and nothing has been finalized.
    if (meetingRequestService.statusValue(request.status) !== 'ready') {
      throw BadRequest('Suggestions can only be refined while the request is ready');
    }
    if (request.selectedPlaceDetails || request.meetingTime) {
      throw BadRequest('Cannot refine after a place or time has been finalized');
    }

    const body = req.body ?? {};
    // Time-of-day: an explicit body value overrides; otherwise fall back to the
    // stored preference. A body value of null/'' (via parseTimeOfDay) clears it.
    const timeOfDay =
      body.time_of_day !== undefined
        ? parseTimeOfDay(body.time_of_day)
        : parseTimeOfDay(request.preferredTimeOfDay);
    const result = await processMeetingRequest({
      requestId: request.requestId,
      addressALat: request.addressALat,
      addressALon: request.addressALon,
      addressBLat: request.addressBLat,
      addressBLon: request.addressBLon,
      locationType: body.location_type ?? request.locationType,
      isPremium: Boolean(req.isPremium),
      openNow: body.open_now,
      radius: body.radius,
      maxResults: body.max_results,
      objective: body.objective,
      timeOfDay,
    });

    if (result.status !== 'completed' || !result.suggestedOptions) {
      throw BadRequest('No places found for the refined search');
    }

    const updated = await meetingRequestService.applyRefinedOptions(
      request,
      result.suggestedOptions as unknown as meetingRequestService.PlaceLike[]
    );

    res.status(200).json(meetingRequestService.toResultsDto(updated));
  } catch (e) {
    next(e);
  }
}

/**
 * POST /:id/send-directions — text the chosen venue's directions link to the
 * caller (optional auth, rate-limited). Only available once the request is
 * COMPLETED.
 *
 * SECURITY: the destination number is read ONLY from stored data — owner →
 * user.phone; invitee → the decrypted user_b contact when it is a PHONE/SMS
 * contact. It is NEVER taken from the request body. The worst case with a
 * leaked token is re-triggering an SMS to the legitimate invitee's own number.
 * The response is generic and never echoes the number.
 */
export async function sendDirections(
  req: Request,
  res: Response,
  next: NextFunction
): Promise<void> {
  try {
    const body = req.body ?? {};
    const { token } = body;

    const request = await meetingRequestService.findById(req.params.id);
    if (!request) throw NotFound('Meeting request not found');

    const userId = req.user?.id;
    const isOwner = Boolean(userId) && request.userAId === userId;
    const isInvitee = meetingRequestService.tokenMatches(request.tokenB, token);
    if (!isOwner && !isInvitee) throw Forbidden('Unauthorized');

    if (meetingRequestService.statusValue(request.status) !== 'completed') {
      throw BadRequest('Meeting place has not been finalized yet');
    }

    const place = request.selectedPlaceDetails as
      | { name?: unknown; address?: unknown; place_id?: unknown }
      | null;
    if (!place) {
      throw BadRequest('No meeting place is available');
    }

    // Resolve the destination number strictly from stored data.
    let toNumber: string | null = null;
    if (isOwner) {
      const owner = userId ? await userService.findById(userId) : null;
      toNumber = owner?.phone ?? null;
    } else if (
      request.userBContactType === ContactType.PHONE ||
      request.userBContactType === ContactType.SMS
    ) {
      try {
        toNumber = decryptContact(request.userBContactEncrypted);
      } catch {
        toNumber = null;
      }
    }

    if (!toNumber) {
      // Frontend falls back to the on-screen directions link.
      throw BadRequest('No phone number is available for SMS delivery');
    }

    const url = buildDirectionsUrl(place);
    const name = typeof place.name === 'string' ? place.name : 'your meeting spot';
    await sendSms(toNumber, `Directions to ${name}: ${url}`);

    res.status(200).json({ message: 'Directions sent' });
  } catch (e) {
    next(e);
  }
}

// --- Scheduling (Phase 1): mirror the place-selection auth/mode pattern for
// *when* to meet, then expose "add to calendar" artifacts. ---

/**
 * Build the public CalendarEvent for a finalized meeting from stored data.
 *
 * PRIVACY: `location` is the venue name + formatted address ONLY — never
 * location_a/location_b or coordinates. Returns null if the request has no
 * locked place or time yet.
 */
function buildEventForRequest(request: {
  requestId: string;
  selectedPlaceDetails: unknown;
  meetingTime: Date | null;
  meetingDurationMin: number | null;
}): CalendarEvent | null {
  const place = request.selectedPlaceDetails as
    | { name?: unknown; address?: unknown }
    | null;
  if (!place || !request.meetingTime) return null;

  const name = typeof place.name === 'string' ? place.name : 'Meeting';
  const address = typeof place.address === 'string' ? place.address : '';
  const start = request.meetingTime;
  const end = endFromDuration(start, request.meetingDurationMin);

  return {
    requestId: request.requestId,
    title: `Meeting at ${name}`,
    location: address ? `${name}, ${address}` : name,
    description: 'Scheduled via Find A Meeting Spot.',
    start,
    end,
  };
}

function formatMeetingWhen(when: Date): string {
  return when.toLocaleString('en-US', {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
    timeZoneName: 'short',
  });
}

/**
 * Notify both parties that the meeting time is locked, with an add-to-calendar
 * link. Best-effort: failures are logged and never block the schedule response.
 *
 * PRIVACY: destinations come only from stored owner profile / invitee contact;
 * the message carries the public venue + time only.
 */
async function notifyMeetingScheduled(request: {
  userAId: string | null;
  userBContactType: ContactType;
  userBContactEncrypted: string;
  selectedPlaceDetails: unknown;
  meetingTime: Date | null;
  meetingDurationMin: number | null;
  requestId: string;
}): Promise<void> {
  const event = buildEventForRequest(request);
  if (!event || !request.meetingTime) return;

  const calendarUrl = buildCalendarUrl(event);
  const whenText = formatMeetingWhen(request.meetingTime);
  const place = request.selectedPlaceDetails as { name?: unknown; address?: unknown } | null;
  const venueName = typeof place?.name === 'string' ? place.name : 'your meeting spot';
  const location = typeof place?.address === 'string' ? place.address : '';
  const smsBody = `Meeting confirmed for ${whenText} at ${venueName}. Add to calendar: ${calendarUrl}`;

  if (request.userAId) {
    try {
      const owner = await userService.findById(request.userAId);
      if (owner?.email) {
        await sendMeetingScheduledEmail(owner.email, venueName, location, whenText, calendarUrl);
      } else if (owner?.phone) {
        await sendSms(owner.phone, smsBody);
      }
    } catch (e) {
      console.error('Failed to notify organizer of scheduled meeting:', e);
    }
  }

  try {
    if (request.userBContactType === ContactType.EMAIL) {
      let toEmail: string | null = null;
      try {
        toEmail = decryptContact(request.userBContactEncrypted);
      } catch {
        toEmail = null;
      }
      if (toEmail) {
        await sendMeetingScheduledEmail(toEmail, venueName, location, whenText, calendarUrl);
      }
    } else if (
      request.userBContactType === ContactType.PHONE ||
      request.userBContactType === ContactType.SMS
    ) {
      let toNumber: string | null = null;
      try {
        toNumber = decryptContact(request.userBContactEncrypted);
      } catch {
        toNumber = null;
      }
      if (toNumber) {
        await sendSms(toNumber, smsBody);
      }
    }
  } catch (e) {
    console.error('Failed to notify invitee of scheduled meeting:', e);
  }
}

/**
 * GET /:id/availability — open slots from Google FreeBusy (optional auth).
 *
 * Owner via Bearer or invitee via ?token=. Place must already be locked.
 * Phase 1 returns organizer-only slots when the invitee has no calendar
 * connection; never returns busy event titles — only open slot starts/ends.
 */
export async function getAvailability(
  req: Request,
  res: Response,
  next: NextFunction
): Promise<void> {
  try {
    const request = await meetingRequestService.findById(req.params.id);
    if (!request) throw NotFound('Meeting request not found');

    const userId = req.user?.id;
    const isOwner = Boolean(userId) && request.userAId === userId;
    const isInvitee = meetingRequestService.tokenMatches(request.tokenB, req.query.token);
    if (!isOwner && !isInvitee) throw Forbidden('Unauthorized');

    if (
      meetingRequestService.statusValue(request.status) !== 'completed' ||
      !request.selectedPlaceDetails
    ) {
      throw BadRequest('A meeting place must be finalized before checking availability');
    }

    const availability = await computeMeetingAvailability({
      organizerUserId: request.userAId,
      inviteeUserId: null, // Phase 1: invitee calendar link comes later
      viewerIsOrganizer: isOwner,
      durationMin: request.meetingDurationMin,
    });

    res.status(200).json(availability);
  } catch (e) {
    next(e);
  }
}

/**
 * POST /:id/schedule — propose the meeting time (optional auth).
 *
 * Mirrors chooseMeetingPlace: owner via Bearer chooses as "A"; invitee via body
 * `token` chooses as "B". OWNER mode makes the invitee read-only. Time selection
 * only happens once the place is locked (status='completed' + selectedPlace
 * Details), and a finalized time can't be re-proposed.
 */
export async function proposeMeetingTime(
  req: Request,
  res: Response,
  next: NextFunction
): Promise<void> {
  try {
    const body = req.body ?? {};
    const { token, meeting_time, meeting_duration_min } = body;

    const request = await meetingRequestService.findById(req.params.id);
    if (!request) throw NotFound('Meeting request not found');

    const userId = req.user?.id;
    const isOwner = Boolean(userId) && request.userAId === userId;
    const isInvitee = meetingRequestService.tokenMatches(request.tokenB, token);
    if (!isOwner && !isInvitee) throw Forbidden('Unauthorized');

    // The place must already be locked in before a time can be chosen.
    if (
      meetingRequestService.statusValue(request.status) !== 'completed' ||
      !request.selectedPlaceDetails
    ) {
      throw BadRequest('A meeting place must be finalized before scheduling');
    }
    if (request.meetingTime) {
      throw BadRequest('A meeting time has already been finalized');
    }

    // OWNER mode: invitee is read-only.
    if (request.selectionMode === SelectionMode.OWNER && !isOwner) {
      throw Forbidden('Only the organizer can choose the meeting time');
    }

    const when = new Date(meeting_time);
    if (!meetingRequestService.isValidFutureTime(when)) {
      throw BadRequest('meeting_time must be a valid future time');
    }

    // Persist an optional duration (used for the ICS end time) before recording.
    if (typeof meeting_duration_min === 'number') {
      await meetingRequestService.updateRequest(request.requestId, {
        meetingDurationMin: meeting_duration_min,
      });
      request.meetingDurationMin = meeting_duration_min;
    }

    const role: 'A' | 'B' = isOwner ? 'A' : 'B';
    const updated = await meetingRequestService.recordTimeChoice(request, role, when);

    // When the time first locks in, confirm the completed plan for both parties.
    // Never fail the schedule response if delivery has trouble.
    if (!request.meetingTime && updated.meetingTime) {
      try {
        await notifyMeetingScheduled(updated);
      } catch (e) {
        console.error('Failed to send meeting confirmation notifications:', e);
      }
    }

    res.status(200).json(meetingRequestService.toScheduleDto(updated));
  } catch (e) {
    next(e);
  }
}

/**
 * GET /:id/calendar — return the "add to calendar" artifacts (owner or invitee
 * via ?token=). Requires a finalized meeting_time. The .ics string is the source
 * of truth; the client builds the download from it.
 */
export async function getCalendarLinks(
  req: Request,
  res: Response,
  next: NextFunction
): Promise<void> {
  try {
    const request = await meetingRequestService.findById(req.params.id);
    if (!request) throw NotFound('Meeting request not found');

    const userId = req.user?.id;
    const isOwner = Boolean(userId) && request.userAId === userId;
    const isInvitee = meetingRequestService.tokenMatches(
      request.tokenB,
      req.query.token
    );
    if (!isOwner && !isInvitee) throw Forbidden('Unauthorized');

    if (!request.meetingTime) {
      throw BadRequest('Meeting time has not been finalized yet');
    }

    const event = buildEventForRequest(request);
    if (!event) throw BadRequest('No meeting is available');

    res.status(200).json({
      google_url: buildCalendarUrl(event),
      ics: buildIcs(event),
    });
  } catch (e) {
    next(e);
  }
}

/**
 * POST /:id/send-calendar — deliver the calendar link to the caller (optional
 * auth, rate-limited). Mirrors sendDirections: the destination is read ONLY from
 * stored data (owner → user.phone/email; invitee → decrypted user_b contact),
 * never the request body.
 */
export async function sendCalendar(
  req: Request,
  res: Response,
  next: NextFunction
): Promise<void> {
  try {
    const body = req.body ?? {};
    const { token } = body;

    const request = await meetingRequestService.findById(req.params.id);
    if (!request) throw NotFound('Meeting request not found');

    const userId = req.user?.id;
    const isOwner = Boolean(userId) && request.userAId === userId;
    const isInvitee = meetingRequestService.tokenMatches(request.tokenB, token);
    if (!isOwner && !isInvitee) throw Forbidden('Unauthorized');

    if (!request.meetingTime) {
      throw BadRequest('Meeting time has not been finalized yet');
    }

    const event = buildEventForRequest(request);
    if (!event) throw BadRequest('No meeting is available');

    const calendarUrl = buildCalendarUrl(event);
    const whenText = formatMeetingWhen(request.meetingTime);
    const place = request.selectedPlaceDetails as { name?: unknown; address?: unknown } | null;
    const venueName = typeof place?.name === 'string' ? place.name : 'your meeting spot';
    const location = typeof place?.address === 'string' ? place.address : '';

    // Resolve the destination strictly from stored data.
    if (isOwner) {
      const owner = userId ? await userService.findById(userId) : null;
      if (owner?.email) {
        await sendMeetingScheduledEmail(
          owner.email,
          venueName,
          location,
          whenText,
          calendarUrl
        );
      } else if (owner?.phone) {
        await sendSms(owner.phone, `Add your meeting to your calendar: ${calendarUrl}`);
      } else {
        throw BadRequest('No contact is available for delivery');
      }
    } else if (request.userBContactType === ContactType.EMAIL) {
      let toEmail: string | null = null;
      try {
        toEmail = decryptContact(request.userBContactEncrypted);
      } catch {
        toEmail = null;
      }
      if (!toEmail) throw BadRequest('No contact is available for delivery');
      await sendMeetingScheduledEmail(
        toEmail,
        venueName,
        location,
        whenText,
        calendarUrl
      );
    } else if (
      request.userBContactType === ContactType.PHONE ||
      request.userBContactType === ContactType.SMS
    ) {
      let toNumber: string | null = null;
      try {
        toNumber = decryptContact(request.userBContactEncrypted);
      } catch {
        toNumber = null;
      }
      if (!toNumber) throw BadRequest('No contact is available for delivery');
      await sendSms(toNumber, `Add your meeting to your calendar: ${calendarUrl}`);
    } else {
      throw BadRequest('No contact is available for delivery');
    }

    res.status(200).json({ message: 'Calendar link sent' });
  } catch (e) {
    next(e);
  }
}
