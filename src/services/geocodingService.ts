// Google Maps Geocoding API client. Ported from app/utils/geocoding.py.
// Response shapes are preserved so the frontend/tests see identical fields.
import axios from 'axios';
import { GEOCODING_API_URL } from '../utils/constants.js';
import { env } from '../config/env.js';
import { validateCoordinates } from '../utils/validators.js';

export interface GeocodeSuccess {
  success: true;
  lat: number;
  lng: number;
  formatted_address: string;
  quality: 'high' | 'medium' | 'low';
  coordinates: { lat: number; lng: number };
}
export interface GeocodeFailure {
  success: false;
  error: string;
}
export type GeocodeResult = GeocodeSuccess | GeocodeFailure;

export interface ReverseGeocodeSuccess {
  success: true;
  formatted_address: string;
  quality: 'high' | 'medium' | 'low';
}
export type ReverseGeocodeResult = ReverseGeocodeSuccess | GeocodeFailure;

const HIGH_PRECISION_TYPES = ['street_address', 'premise', 'subpremise', 'point_of_interest'];
const MEDIUM_PRECISION_TYPES = ['neighborhood', 'locality', 'sublocality', 'postal_code', 'route'];

function determineAddressQuality(result: { types?: string[] }): 'high' | 'medium' | 'low' {
  const types = result.types ?? [];
  if (types.some((t) => HIGH_PRECISION_TYPES.includes(t))) return 'high';
  if (types.some((t) => MEDIUM_PRECISION_TYPES.includes(t))) return 'medium';
  return 'low';
}

export async function geocodeAddress(address: string, apiKey?: string): Promise<GeocodeResult> {
  if (!address) {
    return { success: false, error: 'Address cannot be empty' };
  }

  const key = apiKey ?? env.googleMapsApiKey;
  if (!key) {
    return { success: false, error: 'Geocoding service not configured' };
  }

  try {
    const response = await axios.get(GEOCODING_API_URL, { params: { address, key } });
    const data = response.data;

    if (data.status !== 'OK') {
      if (data.status === 'ZERO_RESULTS') {
        return { success: false, error: 'No results found for the given address' };
      }
      return { success: false, error: data.error_message ?? `Geocoding failed: ${data.status}` };
    }
    if (!data.results || data.results.length === 0) {
      return { success: false, error: 'No results found for the given address' };
    }

    const result = data.results[0];
    const location = result.geometry.location;
    const quality = determineAddressQuality(result);

    return {
      success: true,
      lat: location.lat,
      lng: location.lng,
      formatted_address: result.formatted_address,
      quality,
      coordinates: { lat: location.lat, lng: location.lng },
    };
  } catch (e) {
    return { success: false, error: `Error during geocoding: ${(e as Error).message}` };
  }
}

export async function reverseGeocodeCoordinates(
  lat: number,
  lng: number,
  apiKey?: string
): Promise<ReverseGeocodeResult> {
  if (!validateCoordinates(lat, lng)) {
    return { success: false, error: 'Invalid latitude/longitude values' };
  }

  const key = apiKey ?? env.googleMapsApiKey;
  if (!key) {
    return { success: false, error: 'Geocoding service not configured' };
  }

  try {
    const response = await axios.get(GEOCODING_API_URL, { params: { latlng: `${lat},${lng}`, key } });
    const data = response.data;

    if (data.status !== 'OK') {
      if (data.status === 'ZERO_RESULTS') {
        return { success: false, error: 'No results found for the given coordinates' };
      }
      return { success: false, error: data.error_message ?? `Geocoding failed: ${data.status}` };
    }
    if (!data.results || data.results.length === 0) {
      return { success: false, error: 'No address found for the provided coordinates' };
    }

    const result = data.results[0];
    const quality = determineAddressQuality(result);
    return { success: true, formatted_address: result.formatted_address, quality };
  } catch (e) {
    return { success: false, error: `Reverse geocoding service error: ${(e as Error).message}` };
  }
}
