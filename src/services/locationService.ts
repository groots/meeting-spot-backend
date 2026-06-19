// Exact port of the Python reference app/utils/location.py.
// Geographic midpoint/distance math, category parsing, Google Places lookup,
// and the meeting-request processing pipeline (radius ladder 1500→3000→5000).
import {
  PLACE_CATEGORIES,
  FOOD_SUBCATEGORIES,
  FOOD_CUISINE_KEYWORDS,
  CUISINE_MIN_RATING,
} from '../utils/constants.js';
import { nearbySearch, buildPhotoUrl } from './placesClient.js';

const toRadians = (deg: number): number => (deg * Math.PI) / 180;
const toDegrees = (rad: number): number => (rad * 180) / Math.PI;

export interface Coordinates {
  lat: number;
  lon: number;
}

export interface MeetingSpot {
  name: string;
  place_id: string;
  address: string;
  location: { lat: number; lng: number };
  rating: number | null;
  user_ratings_total: number | null;
  price_level: number | null;
  photos: string[];
  distance: number; // kilometers
  types: string[];
  category: string;
  subcategory: string | null;
}

/**
 * Calculate the geographic midpoint between two coordinates.
 * Mirrors calculate_midpoint in location.py (Bx/By/atan2).
 */
export function calculateMidpoint(
  lat1: number,
  lon1: number,
  lat2: number,
  lon2: number
): [number, number] {
  const lat1Rad = toRadians(lat1);
  const lon1Rad = toRadians(lon1);
  const lat2Rad = toRadians(lat2);
  const lon2Rad = toRadians(lon2);

  const dLon = lon2Rad - lon1Rad;

  const Bx = Math.cos(lat2Rad) * Math.cos(dLon);
  const By = Math.cos(lat2Rad) * Math.sin(dLon);

  const lat3Rad = Math.atan2(
    Math.sin(lat1Rad) + Math.sin(lat2Rad),
    Math.sqrt((Math.cos(lat1Rad) + Bx) ** 2 + By ** 2)
  );
  const lon3Rad = lon1Rad + Math.atan2(By, Math.cos(lat1Rad) + Bx);

  return [toDegrees(lat3Rad), toDegrees(lon3Rad)];
}

/**
 * Haversine distance in kilometers (R = 6371.0). Mirrors calculate_distance.
 */
export function calculateDistance(
  lat1: number,
  lon1: number,
  lat2: number,
  lon2: number
): number {
  const R = 6371.0;

  const lat1Rad = toRadians(lat1);
  const lon1Rad = toRadians(lon1);
  const lat2Rad = toRadians(lat2);
  const lon2Rad = toRadians(lon2);

  const dLat = lat2Rad - lat1Rad;
  const dLon = lon2Rad - lon1Rad;

  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(lat1Rad) * Math.cos(lat2Rad) * Math.sin(dLon / 2) ** 2;
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));

  return R * c;
}

/**
 * Map a user-friendly category/subcategory to Google Places type strings.
 */
export function getPlaceTypesForCategory(category: string): string[] {
  if (category in PLACE_CATEGORIES) {
    return PLACE_CATEGORIES[category];
  }
  const lower = category.toLowerCase();
  if (lower in FOOD_SUBCATEGORIES) {
    return FOOD_SUBCATEGORIES[lower].types;
  }
  return ['restaurant'];
}

/**
 * Keywords associated with a food subcategory (empty if none).
 */
export function getCategoryKeywords(category: string): string[] {
  const lower = category.toLowerCase();
  if (lower in FOOD_SUBCATEGORIES && FOOD_SUBCATEGORIES[lower].keywords) {
    return FOOD_SUBCATEGORIES[lower].keywords;
  }
  if (lower in FOOD_CUISINE_KEYWORDS) {
    return [FOOD_CUISINE_KEYWORDS[lower]];
  }
  return [];
}

/**
 * Find meeting spots near (lat, lon) via Google Places Nearby Search.
 * Ports find_meeting_spots: single-type query + keyword, post-filtering on
 * price/rating for subcategories, distance computed from the search center,
 * sort by (-rating, distance), sliced to max_results.
 */
export async function findMeetingSpots(
  lat: number,
  lon: number,
  radius = 1000,
  category = 'restaurant',
  subcategory: string | null = null,
  maxResults = 5
): Promise<MeetingSpot[]> {
  let placeTypes: string[];
  let keywords: string[];

  if (subcategory) {
    placeTypes = getPlaceTypesForCategory(subcategory);
    keywords = getCategoryKeywords(subcategory);
  } else {
    placeTypes = getPlaceTypesForCategory(category);
    keywords = [];
  }

  const placeType = placeTypes.length > 0 ? placeTypes[0] : 'restaurant';

  const places = await nearbySearch({
    lat,
    lon,
    radius,
    type: placeType,
    keyword: keywords.length > 0 ? keywords[0] : undefined,
  });

  const subFilters =
    subcategory && subcategory.toLowerCase() in FOOD_SUBCATEGORIES
      ? FOOD_SUBCATEGORIES[subcategory.toLowerCase()]
      : null;

  // Cuisine keyword searches get a rating floor (see CUISINE_MIN_RATING).
  const isCuisine =
    !!subcategory && subcategory.toLowerCase() in FOOD_CUISINE_KEYWORDS;

  const meetingSpots: MeetingSpot[] = [];

  for (const place of places) {
    const location = place.geometry?.location;
    if (!location) {
      continue;
    }

    const photos: string[] = [];
    if (place.photos && place.photos.length > 0) {
      for (const photo of place.photos.slice(0, 2)) {
        if (photo.photo_reference) {
          photos.push(buildPhotoUrl(photo.photo_reference));
        }
      }
    }

    const placeLat = location.lat;
    const placeLon = location.lng;
    const distance = calculateDistance(lat, lon, placeLat, placeLon);

    // Subcategory price/rating constraints (only applied when present on place).
    if (subFilters) {
      if (
        subFilters.min_price_level !== undefined &&
        place.price_level !== undefined &&
        place.price_level < subFilters.min_price_level
      ) {
        continue;
      }
      if (
        subFilters.max_price_level !== undefined &&
        place.price_level !== undefined &&
        place.price_level > subFilters.max_price_level
      ) {
        continue;
      }
      if (
        subFilters.min_rating !== undefined &&
        place.rating !== undefined &&
        place.rating < subFilters.min_rating
      ) {
        continue;
      }
      if (
        subFilters.max_rating !== undefined &&
        place.rating !== undefined &&
        place.rating > subFilters.max_rating
      ) {
        continue;
      }
    }

    // Drop low-rated cuisine matches (unrated places pass through).
    if (isCuisine && place.rating !== undefined && place.rating < CUISINE_MIN_RATING) {
      continue;
    }

    meetingSpots.push({
      name: place.name,
      place_id: place.place_id,
      address: place.vicinity ?? '',
      location: { lat: placeLat, lng: placeLon },
      rating: place.rating ?? null,
      user_ratings_total: place.user_ratings_total ?? null,
      price_level: place.price_level ?? null,
      photos,
      distance,
      types: place.types ?? [],
      category,
      subcategory,
    });
  }

  // Sort by rating desc, then distance asc (matches Python's (-rating, distance)).
  meetingSpots.sort((a, b) => {
    const ratingDelta = (b.rating ?? 0) - (a.rating ?? 0);
    if (ratingDelta !== 0) {
      return ratingDelta;
    }
    return a.distance - b.distance;
  });

  return meetingSpots.slice(0, maxResults);
}

export interface ProcessableRequest {
  requestId: string;
  addressALat: number | null;
  addressALon: number | null;
  addressBLat: number | null;
  addressBLon: number | null;
  locationType: string | null;
}

export interface ProcessResult {
  success: boolean;
  suggestedOptions: MeetingSpot[] | null;
  status: 'completed' | 'failed';
}

/**
 * Process a meeting request: midpoint → category parse → Places lookup with the
 * 1500 → 3000 → 5000m fallback ladder. Returns the computed suggestions and the
 * resulting status (the caller persists them). Ports process_meeting_request.
 */
export async function processMeetingRequest(
  request: ProcessableRequest
): Promise<ProcessResult> {
  try {
    if (
      request.addressALat === null ||
      request.addressALon === null ||
      request.addressBLat === null ||
      request.addressBLon === null
    ) {
      return { success: false, suggestedOptions: null, status: 'failed' };
    }

    const [midpointLat, midpointLon] = calculateMidpoint(
      request.addressALat,
      request.addressALon,
      request.addressBLat,
      request.addressBLon
    );

    let category = 'Food & Drink';
    let subcategory: string | null = null;

    const locationType = request.locationType;
    if (locationType) {
      if (locationType.includes(':')) {
        const idx = locationType.indexOf(':');
        category = locationType.slice(0, idx).trim();
        const rest = locationType.slice(idx + 1).trim();
        subcategory = rest.length > 0 ? rest : null;
      } else if (locationType.toLowerCase() in FOOD_SUBCATEGORIES) {
        category = 'Food & Drink';
        subcategory = locationType.toLowerCase();
      } else if (locationType in PLACE_CATEGORIES) {
        category = locationType;
      }
    }

    let meetingSpots = await findMeetingSpots(
      midpointLat,
      midpointLon,
      1500,
      category,
      subcategory,
      10
    );

    if (meetingSpots.length === 0) {
      meetingSpots = await findMeetingSpots(
        midpointLat,
        midpointLon,
        3000,
        category,
        null,
        10
      );

      if (meetingSpots.length === 0) {
        meetingSpots = await findMeetingSpots(
          midpointLat,
          midpointLon,
          5000,
          'Food & Drink',
          null,
          10
        );

        if (meetingSpots.length === 0) {
          return { success: false, suggestedOptions: null, status: 'failed' };
        }
      }
    }

    return { success: true, suggestedOptions: meetingSpots, status: 'completed' };
  } catch {
    return { success: false, suggestedOptions: null, status: 'failed' };
  }
}
