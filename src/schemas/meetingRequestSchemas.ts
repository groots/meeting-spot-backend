// Zod schemas for meeting-request request bodies.
import { z } from 'zod';
import { validateCoordinates } from '../utils/validators.js';

export const createMeetingRequestSchema = z
  .object({
    address_a: z.string().trim().min(1, 'address_a is required'),
    location_type: z.string().trim().min(1, 'location_type is required'),
    user_b_contact_type: z.string().trim().min(1, 'user_b_contact_type is required'),
    user_b_contact: z.string().trim().min(1, 'user_b_contact is required'),
    selection_mode: z.enum(['owner', 'mutual']).optional(),
  })
  .passthrough();

// Coordinates accept number or numeric string (controllers/persistence coerce);
// range validity is delegated to the shared validateCoordinates helper.
const coordinate = z.union([z.number(), z.string()]);

export const respondSchema = z
  .object({
    token: z.string().min(1, 'token is required'),
    address_b_lat: coordinate,
    address_b_lon: coordinate,
  })
  .passthrough()
  .refine(
    (data) => validateCoordinates(data.address_b_lat, data.address_b_lon),
    { message: 'Invalid coordinates' }
  );

// POST /:id/choose — record a participant's venue pick. `token` is present only
// for the invitee path (owner uses the Bearer token). The place must at least
// carry name+address; `.passthrough()` preserves the rest of the venue object
// (place_id, location, etc.) so the server can match it against suggestions.
export const chooseSchema = z
  .object({
    token: z.string().min(1).optional(),
    place: z
      .object({
        name: z.string().min(1, 'place.name is required'),
        address: z.string().min(1, 'place.address is required'),
      })
      .passthrough(),
  })
  .passthrough();

// POST /:id/send-directions — only carries an optional invitee token. The SMS
// destination is read from stored data, never the request body.
export const sendDirectionsSchema = z
  .object({
    token: z.string().min(1).optional(),
  })
  .passthrough();

// POST /:id/schedule — propose the meeting time. `token` is present only for the
// invitee path (owner uses the Bearer token). `meeting_time` is an ISO datetime;
// the server additionally validates it's a bounded future time.
// `meeting_duration_min` is the optional event length (minutes) used for the
// ICS/Google end time.
export const scheduleSchema = z
  .object({
    token: z.string().min(1).optional(),
    meeting_time: z.string().datetime(),
    meeting_duration_min: z.number().int().min(1).max(1440).optional(),
  })
  .passthrough();

// POST /:id/send-calendar — only carries an optional invitee token. The delivery
// destination is read from stored data, never the request body.
export const sendCalendarSchema = z
  .object({
    token: z.string().min(1).optional(),
  })
  .passthrough();

// POST /:id/refine — owner-only re-run of the suggestion engine. All fields are
// optional (an empty body just re-runs with the stored location_type). `radius`
// is metres for the first discovery rung; `max_results` caps the returned set;
// `objective` selects the premium fairness ranking.
export const refineSchema = z
  .object({
    location_type: z.string().trim().min(1).optional(),
    open_now: z.boolean().optional(),
    radius: z.number().int().min(100).max(50000).optional(),
    max_results: z.number().int().min(1).max(20).optional(),
    objective: z.enum(['minimax', 'balance']).optional(),
  })
  .passthrough();
