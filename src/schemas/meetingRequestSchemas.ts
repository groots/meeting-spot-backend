// Zod schemas for meeting-request request bodies.
import { z } from 'zod';
import { validateCoordinates } from '../utils/validators.js';

export const createMeetingRequestSchema = z
  .object({
    address_a: z.string().trim().min(1, 'address_a is required'),
    location_type: z.string().trim().min(1, 'location_type is required'),
    user_b_contact_type: z.string().trim().min(1, 'user_b_contact_type is required'),
    user_b_contact: z.string().trim().min(1, 'user_b_contact is required'),
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
