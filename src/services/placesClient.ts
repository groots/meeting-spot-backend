// Thin client over the Google Places Nearby Search API. The result
// filtering/sorting lives in locationService (ported from location.py).
import axios from 'axios';
import { PLACES_NEARBY_URL, PLACE_PHOTO_URL } from '../utils/constants.js';
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

  const response = await axios.get(PLACES_NEARBY_URL, { params: query });
  const data = response.data;
  if (data.status !== 'OK') {
    return [];
  }
  return (data.results ?? []) as GooglePlace[];
}

export function buildPhotoUrl(photoReference: string, apiKey?: string): string {
  const key = apiKey ?? env.googleMapsApiKey;
  return `${PLACE_PHOTO_URL}?maxwidth=400&photoreference=${photoReference}&key=${key}`;
}
