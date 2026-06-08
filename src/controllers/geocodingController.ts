// Geocoding controller — server-side proxy so the Google Maps API key stays on
// the backend (never shipped to the browser). Mirrors the request/response shape
// the frontend expects (src/utils/geocoding.ts):
//   - Forward:  POST { address, skip_reverse? }  -> { success, coordinates, formatted_address }
//   - Reverse:  POST { lat, lng }                -> { success, formatted_address }
import { Request, Response, NextFunction } from 'express';
import { geocodeAddress, reverseGeocodeCoordinates } from '../services/geocodingService.js';

// Matches the client's "Location (lat, lng)" placeholder produced when reverse
// geocoding is unavailable, so we can short-circuit without calling Google.
const LOCATION_PATTERN = /Location \((-?\d+(?:\.\d+)?),\s*(-?\d+(?:\.\d+)?)\)/;

export async function geocode(req: Request, res: Response, next: NextFunction): Promise<void> {
  try {
    const body = req.body ?? {};
    const { address, lat, lng } = body;

    // Reverse geocode when coordinates are provided.
    if (typeof lat === 'number' && typeof lng === 'number') {
      const result = await reverseGeocodeCoordinates(lat, lng);
      res.json(result);
      return;
    }

    if (typeof address === 'string' && address.trim()) {
      // If the address is already a "Location (lat, lng)" placeholder, parse the
      // coordinates directly instead of asking Google to geocode the literal text.
      const match = address.match(LOCATION_PATTERN);
      if (match) {
        const parsedLat = parseFloat(match[1]);
        const parsedLng = parseFloat(match[2]);
        res.json({
          success: true,
          lat: parsedLat,
          lng: parsedLng,
          coordinates: { lat: parsedLat, lng: parsedLng },
          formatted_address: address,
          quality: 'low',
        });
        return;
      }

      const result = await geocodeAddress(address);
      res.json(result);
      return;
    }

    res.status(400).json({
      success: false,
      error: 'Provide either { address } for forward geocoding or { lat, lng } for reverse geocoding',
    });
  } catch (e) {
    next(e);
  }
}
