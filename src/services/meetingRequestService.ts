// Meeting request persistence (Prisma) + enum mapping + security-correct DTOs.
//
// SECURITY: the serializers below NEVER expose tokenB, user_b_contact_encrypted,
// address_a coordinates, location_a, user_a_id, or session_identifier_a to any
// response. The owner view exposes only non-sensitive fields; the public
// /respond view exposes exactly {request_id, status}.
import crypto from 'crypto';
import { ContactType, MeetingRequest, MeetingRequestStatus, Prisma } from '@prisma/client';
import { prisma } from '../config/prisma.js';
import { encryptContact, decryptContact } from '../utils/encryption.js';
import { TOKEN_EXPIRY_HOURS } from '../utils/constants.js';

// --- Enum <-> API string mapping (Prisma returns member names; the API and
// Python reference use the lowercase mapped values). ---

const STATUS_TO_VALUE: Record<MeetingRequestStatus, string> = {
  PENDING_B_ADDRESS: 'pending_b_address',
  CALCULATING: 'calculating',
  READY: 'ready',
  COMPLETED: 'completed',
  EXPIRED: 'expired',
  FAILED: 'failed',
};

const CONTACT_TYPE_TO_VALUE: Record<ContactType, string> = {
  EMAIL: 'email',
  PHONE: 'phone',
  SMS: 'sms',
};

const VALUE_TO_CONTACT_TYPE: Record<string, ContactType> = {
  email: ContactType.EMAIL,
  phone: ContactType.PHONE,
  sms: ContactType.SMS,
};

const VALUE_TO_STATUS: Record<string, MeetingRequestStatus> = {
  pending_b_address: MeetingRequestStatus.PENDING_B_ADDRESS,
  calculating: MeetingRequestStatus.CALCULATING,
  ready: MeetingRequestStatus.READY,
  completed: MeetingRequestStatus.COMPLETED,
  expired: MeetingRequestStatus.EXPIRED,
  failed: MeetingRequestStatus.FAILED,
};

export function statusValue(status: MeetingRequestStatus): string {
  return STATUS_TO_VALUE[status];
}

export function contactTypeValue(type: ContactType): string {
  return CONTACT_TYPE_TO_VALUE[type];
}

/** Parse an API contact-type string ("email"/"phone"/"sms") to the enum. */
export function parseContactType(value: string): ContactType | null {
  return VALUE_TO_CONTACT_TYPE[value?.toLowerCase()] ?? null;
}

/** Parse an API status string to the enum (null if invalid). */
export function parseStatus(value: string): MeetingRequestStatus | null {
  return VALUE_TO_STATUS[value?.toLowerCase()] ?? null;
}

// --- Persistence ---

export interface CreateMeetingRequestInput {
  userAId: string;
  addressALat: number;
  addressALon: number;
  locationA: Prisma.InputJsonValue | null;
  locationType: string;
  userBContactType: ContactType;
  userBContact: string;
}

export async function createMeetingRequest(
  input: CreateMeetingRequestInput
): Promise<MeetingRequest> {
  const now = new Date();
  const expiresAt = new Date(now.getTime() + TOKEN_EXPIRY_HOURS * 60 * 60 * 1000);
  const tokenB = crypto.randomBytes(32).toString('hex');

  return prisma.meetingRequest.create({
    data: {
      userAId: input.userAId,
      addressALat: input.addressALat,
      addressALon: input.addressALon,
      locationA: input.locationA ?? Prisma.JsonNull,
      locationType: input.locationType,
      userBContactType: input.userBContactType,
      userBContactEncrypted: encryptContact(input.userBContact),
      tokenB,
      status: MeetingRequestStatus.PENDING_B_ADDRESS,
      createdAt: now,
      updatedAt: now,
      expiresAt,
    },
  });
}

export function findById(requestId: string): Promise<MeetingRequest | null> {
  return prisma.meetingRequest.findUnique({ where: { requestId } });
}

export function listByUserA(userAId: string): Promise<MeetingRequest[]> {
  return prisma.meetingRequest.findMany({
    where: { userAId },
    orderBy: { createdAt: 'desc' },
  });
}

export function updateRequest(
  requestId: string,
  data: Prisma.MeetingRequestUpdateInput
): Promise<MeetingRequest> {
  return prisma.meetingRequest.update({ where: { requestId }, data });
}

export function deleteRequest(requestId: string): Promise<MeetingRequest> {
  return prisma.meetingRequest.delete({ where: { requestId } });
}

export function isExpired(request: MeetingRequest): boolean {
  if (!request.expiresAt) return false;
  return new Date() > request.expiresAt;
}

/**
 * Timing-safe comparison of the stored tokenB against a provided token. Guards
 * length first (timingSafeEqual throws on length mismatch) so a length probe
 * can't leak via an exception, and returns false for any non-string/empty
 * input without short-circuiting on content.
 */
export function tokenMatches(stored: string, provided: unknown): boolean {
  if (typeof provided !== 'string' || provided.length === 0) return false;
  const a = Buffer.from(stored, 'utf8');
  const b = Buffer.from(provided, 'utf8');
  if (a.length !== b.length) return false;
  return crypto.timingSafeEqual(a, b);
}

/**
 * Atomically "claim" a request for User B's response: flips tokenBUsedAt from
 * NULL → now and persists B's coordinates + CALCULATING in a single updateMany
 * guarded on `tokenBUsedAt: null`. Returns the number of rows affected — 0 means
 * the token was already used (double-submit / replay), 1 means this caller won
 * the claim. Prevents the double-respond race.
 */
export async function claimTokenForResponse(
  requestId: string,
  addressBLat: number,
  addressBLon: number
): Promise<number> {
  const result = await prisma.meetingRequest.updateMany({
    where: { requestId, tokenBUsedAt: null },
    data: {
      addressBLat,
      addressBLon,
      status: MeetingRequestStatus.CALCULATING,
      tokenBUsedAt: new Date(),
      updatedAt: new Date(),
    },
  });
  return result.count;
}

// --- Security-correct serializers ---

/**
 * Owner-facing DTO. Exposes the fields the owner legitimately needs WITHOUT any
 * sensitive material: no tokenB, no user_b_contact_encrypted, no address_a
 * coordinates, no location_a, no session_identifier_a, no user_a_id.
 *
 * PRIVACY: User B's coordinates (address_b_lat/lon) are intentionally NOT
 * exposed. The owner only ever sees suggested venues near the midpoint, never
 * User B's exact location.
 */
export function toOwnerDto(request: MeetingRequest): Record<string, unknown> {
  // OWNER ONLY: decrypt User B's contact so the owner can see who they're
  // meeting. Every caller of this DTO authenticates the owner (userAId === user),
  // so this value is never exposed to User B or the public.
  let userBContact: string | null = null;
  try {
    userBContact = decryptContact(request.userBContactEncrypted);
  } catch {
    userBContact = null;
  }

  return {
    request_id: request.requestId,
    user_b_contact: userBContact,
    user_b_contact_type: contactTypeValue(request.userBContactType),
    location_type: request.locationType,
    status: statusValue(request.status),
    selected_place_google_id: request.selectedPlaceGoogleId,
    selected_place_details: request.selectedPlaceDetails,
    suggested_options: request.suggestedOptions,
    created_at: request.createdAt.toISOString(),
    updated_at: request.updatedAt.toISOString(),
    expires_at: request.expiresAt.toISOString(),
    is_expired: isExpired(request),
  };
}

/** Minimal creation summary returned by POST / (no sensitive fields). */
export function toCreatedDto(request: MeetingRequest): Record<string, unknown> {
  return {
    request_id: request.requestId,
    status: statusValue(request.status),
    user_b_contact_type: contactTypeValue(request.userBContactType),
    location_type: request.locationType,
    created_at: request.createdAt.toISOString(),
  };
}

/** Status-only DTO for GET /:id/status. */
export function toStatusDto(request: MeetingRequest): Record<string, unknown> {
  return {
    request_id: request.requestId,
    status: statusValue(request.status),
    created_at: request.createdAt.toISOString(),
    expires_at: request.expiresAt.toISOString(),
  };
}

/** Results DTO for GET /:id/results (owner only). No sensitive fields. */
export function toResultsDto(request: MeetingRequest): Record<string, unknown> {
  return {
    request_id: request.requestId,
    status: statusValue(request.status),
    suggested_options: request.suggestedOptions,
    selected_place: request.selectedPlaceDetails,
  };
}

/**
 * The ONLY shape returned by POST /:id/respond. Exactly two keys: this is the
 * coordinate-leak fix — User B never receives address_a, suggestions, or any
 * other request internals.
 */
export function toRespondDto(request: MeetingRequest): { request_id: string; status: string } {
  return {
    request_id: request.requestId,
    status: statusValue(request.status),
  };
}
