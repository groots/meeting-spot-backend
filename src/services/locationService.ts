// Exact port of the Python reference app/utils/location.py.
// Geographic midpoint/distance math, category parsing, Google Places lookup,
// and the meeting-request processing pipeline (radius ladder 1500→3000→5000).
import {
  PLACE_CATEGORIES,
  FOOD_SUBCATEGORIES,
  FOOD_CUISINE_KEYWORDS,
  CUISINE_MIN_RATING,
} from '../utils/constants.js';
import { nearbySearch, buildPhotoUrl, distanceMatrix, placeDetails } from './placesClient.js';
import { isOpenDuringTimeOfDay, type TimeOfDay } from '../utils/openingHours.js';

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
  // Travel-time fairness (Phase 2, premium only). Driving seconds from each
  // origin to this venue; null when Distance Matrix had no route/data. Written
  // with origins[0]=A, origins[1]=B today; generalizes to N participants later.
  travel_time_a_sec?: number | null;
  travel_time_b_sec?: number | null;
  // Weekly opening hours from Google Place Details, enriched after ranking for
  // the spots we actually return. null when Details had no data / no key.
  opening_hours?: {
    open_now?: boolean;
    weekday_text?: string[];
    periods?: unknown[];
  } | null;
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
  maxResults = 5,
  openNow = false
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
    openNow: openNow || undefined,
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

export type FairnessObjective = 'minimax' | 'balance';

export interface RankByFairnessOptions {
  objective?: FairnessObjective;
  mode?: string;
  apiKey?: string;
}

/**
 * Re-rank candidate spots by travel-time fairness across `origins`.
 *
 * Written over an origins collection from day one ([A, B] today, N participants
 * later). Calls Distance Matrix once (origins × spots), annotates each spot with
 * per-origin durations (travel_time_a_sec / travel_time_b_sec for origins[0]/[1]),
 * then sorts:
 *   1. Spots with full travel data before those missing any (null) leg.
 *   2. objective 'minimax' (default): minimize the worst origin's time
 *      (helps the worse-off person); 'balance': minimize the spread max−min.
 *   3. Tie-break on the spread |max−min| (fairness).
 *   4. Then the existing (-rating, distance) ordering.
 *
 * Degrades gracefully: if Distance Matrix returns [] (no key / no data) the
 * spots are returned unchanged so callers keep the distance-based ranking.
 */
export async function rankByFairness(
  spots: MeetingSpot[],
  origins: Coordinates[],
  opts: RankByFairnessOptions = {}
): Promise<MeetingSpot[]> {
  if (spots.length === 0 || origins.length === 0) {
    return spots;
  }

  const destinations = spots.map((s) => ({ lat: s.location.lat, lon: s.location.lng }));
  const matrix = await distanceMatrix({
    origins,
    destinations,
    mode: opts.mode,
    apiKey: opts.apiKey,
  });

  // No data → leave the input ordering (and travel_time_* unset) untouched.
  if (matrix.length === 0) {
    return spots;
  }

  // matrix[originIdx][spotIdx] = seconds | null. Pivot to per-spot times.
  const timesForSpot = (spotIdx: number): (number | null)[] =>
    origins.map((_, originIdx) => matrix[originIdx]?.[spotIdx] ?? null);

  const annotated = spots.map((spot, spotIdx) => {
    const times = timesForSpot(spotIdx);
    const next: MeetingSpot = { ...spot };
    next.travel_time_a_sec = times[0] ?? null;
    next.travel_time_b_sec = times.length > 1 ? (times[1] ?? null) : null;
    const complete = times.every((t): t is number => typeof t === 'number');
    const valid = complete ? (times as number[]) : null;
    return {
      spot: next,
      worst: valid ? Math.max(...valid) : Number.POSITIVE_INFINITY,
      spread: valid ? Math.max(...valid) - Math.min(...valid) : Number.POSITIVE_INFINITY,
      complete,
    };
  });

  const objective = opts.objective ?? 'minimax';

  annotated.sort((a, b) => {
    // Complete travel data ranks ahead of incomplete.
    if (a.complete !== b.complete) {
      return a.complete ? -1 : 1;
    }

    if (a.complete && b.complete) {
      const primaryA = objective === 'balance' ? a.spread : a.worst;
      const primaryB = objective === 'balance' ? b.spread : b.worst;
      if (primaryA !== primaryB) {
        return primaryA - primaryB;
      }
      // Tie-break on fairness spread (skip when it's already the primary key).
      if (objective !== 'balance' && a.spread !== b.spread) {
        return a.spread - b.spread;
      }
    }

    // Fall back to the existing (-rating, distance) ordering.
    const ratingDelta = (b.spot.rating ?? 0) - (a.spot.rating ?? 0);
    if (ratingDelta !== 0) {
      return ratingDelta;
    }
    return a.spot.distance - b.spot.distance;
  });

  return annotated.map((a) => a.spot);
}

export interface ProcessableRequest {
  requestId: string;
  addressALat: number | null;
  addressALon: number | null;
  addressBLat: number | null;
  addressBLon: number | null;
  locationType: string | null;
  // Phase 2 (all optional; defaults preserve the original behavior).
  // When true, re-rank the discovered options by travel-time fairness.
  isPremium?: boolean;
  // Filter to currently-open venues (opennow=true on Nearby Search).
  openNow?: boolean;
  // Override the first discovery rung's radius (metres). The 3000/5000 fallback
  // rungs still apply when a smaller radius finds nothing.
  radius?: number;
  // How many options to return after ranking (default 5).
  maxResults?: number;
  // Fairness objective when isPremium (default 'minimax').
  objective?: FairnessObjective;
  // Exclude venues not open during this time-of-day window (morning/afternoon/
  // evening). When set, spots are enriched with Place Details hours and filtered
  // by weekly opening periods before slicing to maxResults.
  timeOfDay?: TimeOfDay | null;
}

export interface ProcessResult {
  success: boolean;
  suggestedOptions: MeetingSpot[] | null;
  status: 'completed' | 'failed';
}

// Fetch opening hours for a single spot (best-effort) and attach them. Returns a
// new spot with `opening_hours` set (null when Details had no data).
async function enrichWithHours(spot: MeetingSpot): Promise<MeetingSpot> {
  const hours = await placeDetails(spot.place_id);
  return { ...spot, opening_hours: hours };
}

/**
 * Enrich ranked spots with opening hours (via Place Details) for display, and
 * optionally filter to those open during `timeOfDay`.
 *
 * Place Details is billed per call, so we enrich lazily in ranked-order batches
 * and — when filtering — stop once `maxResults` matches are collected (capped at
 * the pool size). When not filtering, we still enrich only the top `maxResults`
 * (the ones that will be shown). Degrades to the unfiltered/ranked input if
 * Details returns nothing for the whole pool.
 */
async function enrichAndFilterByHours(
  spots: MeetingSpot[],
  maxResults: number,
  timeOfDay: TimeOfDay | null
): Promise<MeetingSpot[]> {
  const BATCH = 5;

  if (!timeOfDay) {
    // No time filter: only enrich the spots we'll actually show.
    const head = spots.slice(0, maxResults);
    const enrichedHead: MeetingSpot[] = [];
    for (let i = 0; i < head.length; i += BATCH) {
      const batch = head.slice(i, i + BATCH);
      enrichedHead.push(...(await Promise.all(batch.map(enrichWithHours))));
    }
    return [...enrichedHead, ...spots.slice(maxResults)];
  }

  // Time filter active: walk the ranked pool in batches, keep only spots that
  // pass the window, and stop once we have enough matches.
  const matches: MeetingSpot[] = [];
  let anyHours = false;
  for (let i = 0; i < spots.length && matches.length < maxResults; i += BATCH) {
    const batch = spots.slice(i, i + BATCH);
    const enriched = await Promise.all(batch.map(enrichWithHours));
    for (const spot of enriched) {
      if (spot.opening_hours) anyHours = true;
      if (matches.length >= maxResults) break;
      if (isOpenDuringTimeOfDay(spot.opening_hours?.periods as never, timeOfDay)) {
        matches.push(spot);
      }
    }
  }

  // If Place Details yielded no hours at all (no key / API down), we can't
  // filter meaningfully — degrade to the ranked pool so the user still gets
  // results rather than an empty list.
  if (!anyHours && matches.length === 0) {
    const head = spots.slice(0, maxResults);
    const enrichedHead: MeetingSpot[] = [];
    for (let i = 0; i < head.length; i += BATCH) {
      const batch = head.slice(i, i + BATCH);
      enrichedHead.push(...(await Promise.all(batch.map(enrichWithHours))));
    }
    return enrichedHead;
  }

  return matches;
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

    const openNow = request.openNow ?? false;
    const finalCount = request.maxResults ?? 5;
    const timeOfDay = request.timeOfDay ?? null;

    // Discovery ladder: progressively widen and relax the query until something
    // is found. The first rung honors an optional radius override (default 1500)
    // and the chosen subcategory; later rungs broaden the radius and category.
    const firstRadius = request.radius ?? 1500;
    const rungs: Array<{ radius: number; category: string; subcategory: string | null }> = [
      { radius: firstRadius, category, subcategory },
      { radius: 3000, category, subcategory: null },
      { radius: 5000, category: 'Food & Drink', subcategory: null },
    ];

    // Discover a wide pool (20 — one Nearby Search page) so the fairness re-rank
    // AND time-of-day filtering have candidates to choose from before we slice
    // down to finalCount.
    let meetingSpots: MeetingSpot[] = [];
    for (const rung of rungs) {
      meetingSpots = await findMeetingSpots(
        midpointLat,
        midpointLon,
        rung.radius,
        rung.category,
        rung.subcategory,
        20,
        openNow
      );
      if (meetingSpots.length > 0) {
        break;
      }
    }

    if (meetingSpots.length === 0) {
      return { success: false, suggestedOptions: null, status: 'failed' };
    }

    // Premium: re-rank by travel-time fairness across both origins, then slice.
    // Non-premium keeps the (-rating, distance) ordering from findMeetingSpots.
    if (request.isPremium) {
      const origins: Coordinates[] = [
        { lat: request.addressALat, lon: request.addressALon },
        { lat: request.addressBLat, lon: request.addressBLon },
      ];
      meetingSpots = await rankByFairness(meetingSpots, origins, {
        objective: request.objective,
      });
    }

    // Enrich the ranked pool with opening hours (for display) and, when a
    // time-of-day window is set, keep only spots open during it — collecting up
    // to finalCount matches before stopping to limit Place Details calls.
    const enriched = await enrichAndFilterByHours(meetingSpots, finalCount, timeOfDay);

    return {
      success: true,
      suggestedOptions: enriched.slice(0, finalCount),
      status: 'completed',
    };
  } catch {
    return { success: false, suggestedOptions: null, status: 'failed' };
  }
}
