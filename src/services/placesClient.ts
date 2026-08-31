// Thin client over the Google Places Nearby Search API. The result
// filtering/sorting lives in locationService (ported from location.py).
import axios from 'axios';
import {
  PLACES_NEARBY_URL,
  PLACE_DETAILS_URL,
  PLACE_PHOTO_URL,
  DISTANCE_MATRIX_URL,
} from '../utils/constants.js';
import { env } from '../config/env.js';

export interface GooglePlacePhoto {
  photo_reference?: string;
}
export interface GooglePlace {
  name: string;
  place_id: string;
  vicinity?: string;
  geometry?: { location?: { lat: number; lng: number } };
  rating?: number;
  user_ratings_total?: number;
  price_level?: number;
  photos?: GooglePlacePhoto[];
  types?: string[];
}

export interface NearbySearchParams {
  lat: number;
  lon: number;
  radius: number;
  type: string;
  keyword?: string;
  openNow?: boolean;
  apiKey?: string;
}

/**
 * Calls Google Places Nearby Search. Returns the raw `results` array.
 * Throws on transport error or non-OK/ZERO_RESULTS status handling is the
 * caller's responsibility — here we return [] for non-OK statuses to mirror
 * the Python behavior.
 */
export async function nearbySearch(params: NearbySearchParams): Promise<GooglePlace[]> {
  const key = params.apiKey ?? env.googleMapsApiKey;
  if (!key) {
    return [];
  }

  const query: Record<string, string | number> = {
    location: `${params.lat},${params.lon}`,
    radius: params.radius,
    type: params.type,
    key,
  };
  if (params.keyword) {
    query.keyword = params.keyword;
  }
  if (params.openNow) {
    query.opennow = 'true';
  }

  const response = await axios.get(PLACES_NEARBY_URL, { params: query });
  const data = response.data;
  if (data.status !== 'OK') {
    return [];
  }
  return (data.results ?? []) as GooglePlace[];
}

// A single opening period from Google Place Details. `open`/`close` carry a
// `day` (0=Sunday..6=Saturday) and a 4-digit `time` ("HHMM"). A 24h period has
// an `open` with no `close`.
export interface GoogleOpeningPeriod {
  open?: { day?: number; time?: string };
  close?: { day?: number; time?: string };
}

// Normalized opening-hours shape used across the pipeline. Mirrors the subset of
// Google's `opening_hours` we care about: the right-now boolean, the weekly
// human-readable schedule, and the machine-readable periods for time filtering.
export interface OpeningHours {
  open_now?: boolean;
  weekday_text?: string[];
  periods?: GoogleOpeningPeriod[];
}

/**
 * Calls Google Places Place Details for a single place, requesting only the
 * `opening_hours` field. Returns a normalized OpeningHours object, or null when
 * there's no key, the API errors, or no hours are available — mirroring the
 * graceful-degradation style of nearbySearch so callers treat "no data"
 * uniformly (they keep the venue, just without hours).
 */
export async function placeDetails(
  placeId: string,
  apiKey?: string
): Promise<OpeningHours | null> {
  const key = apiKey ?? env.googleMapsApiKey;
  if (!key || !placeId) {
    return null;
  }

  try {
    const response = await axios.get(PLACE_DETAILS_URL, {
      params: { place_id: placeId, fields: 'opening_hours', key },
    });
    const data = response.data;
    if (data.status !== 'OK') {
      return null;
    }
    const hours = data.result?.opening_hours;
    if (!hours) {
      return null;
    }
    return {
      open_now: typeof hours.open_now === 'boolean' ? hours.open_now : undefined,
      weekday_text: Array.isArray(hours.weekday_text) ? hours.weekday_text : undefined,
      periods: Array.isArray(hours.periods) ? (hours.periods as GoogleOpeningPeriod[]) : undefined,
    };
  } catch {
    return null;
  }
}

export interface LatLon {
  lat: number;
  lon: number;
}

export interface DistanceMatrixParams {
  origins: LatLon[];
  destinations: LatLon[];
  mode?: string;
  apiKey?: string;
}

/**
 * Calls Google Distance Matrix. Returns a 2-D grid of travel durations in
 * seconds: rows index `origins`, columns index `destinations`. A cell is null
 * when that origin→destination pair has no route (element status !== 'OK').
 *
 * Degrades to [] when the API key is absent or origins/destinations are empty,
 * mirroring nearbySearch so callers can treat "no data" uniformly.
 */
export async function distanceMatrix(
  params: DistanceMatrixParams
): Promise<(number | null)[][]> {
  const key = params.apiKey ?? env.googleMapsApiKey;
  if (!key || params.origins.length === 0 || params.destinations.length === 0) {
    return [];
  }

  const encode = (points: LatLon[]): string =>
    points.map((p) => `${p.lat},${p.lon}`).join('|');

  const query: Record<string, string> = {
    origins: encode(params.origins),
    destinations: encode(params.destinations),
    mode: params.mode ?? 'driving',
    key,
  };

  const response = await axios.get(DISTANCE_MATRIX_URL, { params: query });
  const data = response.data;
  if (data.status !== 'OK') {
    return [];
  }

  const rows = (data.rows ?? []) as Array<{
    elements?: Array<{ status?: string; duration?: { value?: number } }>;
  }>;

  return rows.map((row) =>
    (row.elements ?? []).map((el) =>
      el.status === 'OK' && typeof el.duration?.value === 'number'
        ? el.duration.value
        : null
    )
  );
}

export function buildPhotoUrl(photoReference: string, apiKey?: string): string {
  const key = apiKey ?? env.googleMapsApiKey;
  return `${PLACE_PHOTO_URL}?maxwidth=400&photoreference=${photoReference}&key=${key}`;
}
