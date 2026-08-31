// Meeting request persistence (Prisma) + enum mapping + security-correct DTOs.
//
// SECURITY: the serializers below NEVER expose tokenB, user_b_contact_encrypted,
// address_a coordinates, location_a, user_a_id, or session_identifier_a to any
// response. The owner view exposes only non-sensitive fields; the public
// /respond view exposes exactly {request_id, status}.
import crypto from 'crypto';
import { ContactType, MeetingRequest, MeetingRequestStatus, SelectionMode, Prisma } from '@prisma/client';
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

const SELECTION_MODE_TO_VALUE: Record<SelectionMode, string> = {
  OWNER: 'owner',
  MUTUAL: 'mutual',
};

const VALUE_TO_SELECTION_MODE: Record<string, SelectionMode> = {
  owner: SelectionMode.OWNER,
  mutual: SelectionMode.MUTUAL,
};

export function selectionModeValue(mode: SelectionMode): string {
  return SELECTION_MODE_TO_VALUE[mode];
}

/** Parse an API selection-mode string ("owner"/"mutual"); defaults to OWNER. */
export function parseSelectionMode(value: unknown): SelectionMode {
  if (typeof value !== 'string') return SelectionMode.OWNER;
  return VALUE_TO_SELECTION_MODE[value.toLowerCase()] ?? SelectionMode.OWNER;
}

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
  selectionMode?: SelectionMode;
  // Preferred time-of-day window ('morning'/'afternoon'/'evening') used to
  // filter suggestions by opening hours. null = no preference.
  preferredTimeOfDay?: string | null;
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
      selectionMode: input.selectionMode ?? SelectionMode.OWNER,
      preferredTimeOfDay: input.preferredTimeOfDay ?? null,
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
    preferred_time_of_day: request.preferredTimeOfDay,
    status: statusValue(request.status),
    selection_mode: selectionModeValue(request.selectionMode),
    selected_place_google_id: request.selectedPlaceGoogleId,
    selected_place_details: request.selectedPlaceDetails,
    suggested_options: request.suggestedOptions,
    user_a_choice: request.userAChoice,
    user_b_choice: request.userBChoice,
    ...timeFields(request),
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

/** Results DTO for GET /:id/results (owner or invitee via token). No sensitive
 * fields — the choices are venues drawn from the already-shared
 * suggested_options, so they carry no coordinates beyond the public venue. */
export function toResultsDto(request: MeetingRequest): Record<string, unknown> {
  return {
    request_id: request.requestId,
    status: statusValue(request.status),
    selection_mode: selectionModeValue(request.selectionMode),
    suggested_options: request.suggestedOptions,
    selected_place: request.selectedPlaceDetails,
    user_a_choice: request.userAChoice,
    user_b_choice: request.userBChoice,
    ...timeFields(request),
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

// --- Collaborative selection helpers ---

/** A venue choice as it arrives from the client / lives in suggestedOptions. */
export type PlaceLike = { name?: unknown; address?: unknown; place_id?: unknown } & Record<
  string,
  unknown
>;

/**
 * Stable identity for a venue across suggestions/choices. Prefer place_id; fall
 * back to "name|address" when the upstream didn't return a place_id. Used to
 * compare User A's and User B's picks for agreement.
 */
export function venueKey(place: PlaceLike | null | undefined): string {
  if (!place) return '';
  const placeId = typeof place.place_id === 'string' ? place.place_id : '';
  if (placeId) return placeId;
  const name = typeof place.name === 'string' ? place.name : '';
  const address = typeof place.address === 'string' ? place.address : '';
  return `${name}|${address}`;
}

/**
 * True when `place` is present (by venueKey) in an option collection. Written
 * over an explicit options array so the same test serves both choice-validation
 * and refine's stale-choice clearing; Phase 3 can reuse it per participant.
 */
export function venueInOptions(
  place: PlaceLike | null | undefined,
  options: PlaceLike[]
): boolean {
  const key = venueKey(place);
  if (!key) return false;
  return options.some((opt) => venueKey(opt) === key);
}

/**
 * Validate that an incoming choice is one of the request's suggested options
 * (by venueKey). Rejects arbitrary venue injection — a choice must match a
 * server-generated suggestion.
 */
export function placeMatchesSuggestion(
  request: MeetingRequest,
  place: PlaceLike
): boolean {
  const options = Array.isArray(request.suggestedOptions)
    ? (request.suggestedOptions as unknown as PlaceLike[])
    : [];
  return venueInOptions(place, options);
}

/**
 * Persist a refined option set (from POST /:id/refine), clearing any recorded
 * venue choices that are no longer among the new options so MUTUAL agreement
 * can't lock onto a venue that just vanished. Keeps the request READY.
 *
 * The stale-choice sweep is written over a choice collection ([A, B] today) so
 * Phase 3 just iterates the participant rows instead.
 */
export async function applyRefinedOptions(
  request: MeetingRequest,
  newOptions: PlaceLike[]
): Promise<MeetingRequest> {
  const data: Prisma.MeetingRequestUpdateInput = {
    suggestedOptions: newOptions as unknown as Prisma.InputJsonValue,
    status: MeetingRequestStatus.READY,
    updatedAt: new Date(),
  };

  const choices: Array<['A' | 'B', PlaceLike | null]> = [
    ['A', request.userAChoice as PlaceLike | null],
    ['B', request.userBChoice as PlaceLike | null],
  ];
  for (const [role, choice] of choices) {
    if (choice && !venueInOptions(choice, newOptions)) {
      if (role === 'A') data.userAChoice = Prisma.JsonNull;
      else data.userBChoice = Prisma.JsonNull;
    }
  }

  return prisma.meetingRequest.update({
    where: { requestId: request.requestId },
    data,
  });
}

/**
 * Record a participant's venue choice and (depending on mode) finalize.
 *
 *   OWNER mode  → only the owner chooses; sets selected_place_details +
 *                 selected_place_google_id and flips to COMPLETED immediately.
 *   MUTUAL mode → records user_a_choice / user_b_choice; when BOTH are set and
 *                 their venueKeys match, finalizes (selected_place_details +
 *                 COMPLETED). Otherwise the request stays READY.
 *
 * Returns the updated request.
 */
export async function recordChoice(
  request: MeetingRequest,
  role: 'A' | 'B',
  place: PlaceLike
): Promise<MeetingRequest> {
  const placeJson = place as unknown as Prisma.InputJsonValue;

  if (request.selectionMode === SelectionMode.OWNER) {
    const googleId = typeof place.place_id === 'string' ? place.place_id : null;
    return prisma.meetingRequest.update({
      where: { requestId: request.requestId },
      data: {
        selectedPlaceDetails: placeJson,
        selectedPlaceGoogleId: googleId,
        status: MeetingRequestStatus.COMPLETED,
        updatedAt: new Date(),
      },
    });
  }

  // MUTUAL mode.
  const data: Prisma.MeetingRequestUpdateInput = { updatedAt: new Date() };
  if (role === 'A') {
    data.userAChoice = placeJson;
  } else {
    data.userBChoice = placeJson;
  }

  // Determine the *other* party's existing choice to test for agreement.
  const otherChoice = (role === 'A' ? request.userBChoice : request.userAChoice) as
    | PlaceLike
    | null;
  const thisKey = venueKey(place);
  const otherKey = venueKey(otherChoice);

  if (otherKey && thisKey && otherKey === thisKey) {
    // Both parties agree → finalize on this venue.
    const googleId = typeof place.place_id === 'string' ? place.place_id : null;
    data.selectedPlaceDetails = placeJson;
    data.selectedPlaceGoogleId = googleId;
    data.status = MeetingRequestStatus.COMPLETED;
  } else {
    // No agreement yet — keep the request awaiting selection.
    data.status = MeetingRequestStatus.READY;
  }

  return prisma.meetingRequest.update({
    where: { requestId: request.requestId },
    data,
  });
}

/** Safe DTO returned by POST /:id/choose — only the collaborative-selection
 * fields both parties may see (no address_a, tokenB, or contact). */
export function toChooseDto(request: MeetingRequest): Record<string, unknown> {
  return {
    request_id: request.requestId,
    status: statusValue(request.status),
    selection_mode: selectionModeValue(request.selectionMode),
    user_a_choice: request.userAChoice,
    user_b_choice: request.userBChoice,
    selected_place: request.selectedPlaceDetails,
    ...timeFields(request),
  };
}

// --- Scheduling helpers (mirror collaborative selection, for *when* to meet) ---

/** Default meeting length (minutes) used for the ICS end time when the owner
 * didn't specify a duration. */
export const DEFAULT_MEETING_DURATION_MIN = 60;

/**
 * Canonical ISO-minute identity for a proposed time (analog of venueKey). Two
 * proposals "agree" when their timeKeys match. Truncated to the minute so a
 * difference in seconds/millis between the two clients' inputs doesn't block a
 * match. Returns '' for a null/invalid date.
 */
export function timeKey(when: Date | null | undefined): string {
  if (!when) return '';
  const d = when instanceof Date ? when : new Date(when);
  const ms = d.getTime();
  if (Number.isNaN(ms)) return '';
  // Floor to the minute (UTC) and emit a stable ISO string.
  return new Date(Math.floor(ms / 60000) * 60000).toISOString();
}

/**
 * Pure agreement test over a collection of time keys: true when there is at
 * least one key and every key is non-empty and identical. Written over an array
 * so Phase 3 can pass N participants' keys; today it's called with [A, B].
 */
export function choicesAgree(keys: string[]): boolean {
  if (keys.length === 0) return false;
  const first = keys[0];
  if (!first) return false;
  return keys.every((k) => k === first);
}

/**
 * Validate a proposed meeting time: a real date, in the future, and bounded to
 * ~1 year out (guards absurd/overflow values). Mirrors the server-side checks
 * we apply to user input at the boundary.
 */
export function isValidFutureTime(when: Date | null | undefined): boolean {
  if (!when) return false;
  const d = when instanceof Date ? when : new Date(when);
  const ms = d.getTime();
  if (Number.isNaN(ms)) return false;
  const now = Date.now();
  const oneYearMs = 366 * 24 * 60 * 60 * 1000;
  return ms > now && ms <= now + oneYearMs;
}

/**
 * Record a participant's proposed meeting time and (depending on mode) finalize.
 *
 *   OWNER mode  → only the owner proposes; sets meeting_time immediately.
 *   MUTUAL mode → records user_a_time_choice / user_b_time_choice; when the
 *                 other party's timeKey already matches, sets meeting_time.
 *                 Otherwise the proposal is just stored (status unchanged —
 *                 the place is already locked at COMPLETED).
 *
 * Returns the updated request.
 */
export async function recordTimeChoice(
  request: MeetingRequest,
  role: 'A' | 'B',
  when: Date
): Promise<MeetingRequest> {
  if (request.selectionMode === SelectionMode.OWNER) {
    return prisma.meetingRequest.update({
      where: { requestId: request.requestId },
      data: { meetingTime: when, updatedAt: new Date() },
    });
  }

  // MUTUAL mode.
  const data: Prisma.MeetingRequestUpdateInput = { updatedAt: new Date() };
  if (role === 'A') {
    data.userATimeChoice = when;
  } else {
    data.userBTimeChoice = when;
  }

  const otherChoice = role === 'A' ? request.userBTimeChoice : request.userATimeChoice;
  if (choicesAgree([timeKey(when), timeKey(otherChoice)])) {
    // Both parties proposed the same minute → lock the time in.
    data.meetingTime = when;
  }

  return prisma.meetingRequest.update({
    where: { requestId: request.requestId },
    data,
  });
}

/** The scheduling fields shared by the time-aware DTOs. Privacy-safe: times
 * carry no address or contact. */
function timeFields(request: MeetingRequest): Record<string, unknown> {
  return {
    meeting_time: request.meetingTime ? request.meetingTime.toISOString() : null,
    user_a_time_choice: request.userATimeChoice ? request.userATimeChoice.toISOString() : null,
    user_b_time_choice: request.userBTimeChoice ? request.userBTimeChoice.toISOString() : null,
    meeting_duration_min: request.meetingDurationMin,
  };
}

/** DTO returned by POST /:id/schedule — the collaborative time-selection state
 * (no address_a, tokenB, or contact). */
export function toScheduleDto(request: MeetingRequest): Record<string, unknown> {
  return {
    request_id: request.requestId,
    status: statusValue(request.status),
    selection_mode: selectionModeValue(request.selectionMode),
    ...timeFields(request),
  };
}
