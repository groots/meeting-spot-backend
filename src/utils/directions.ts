// Shared helper to build a Google Maps directions URL to a chosen venue.
//
// PRIVACY: the origin is intentionally omitted. Google Maps then uses each
// user's own current location as the start point, so no party's address is
// ever embedded in (or shared via) the link.

export interface DirectionsPlace {
  name?: unknown;
  address?: unknown;
  place_id?: unknown;
}

/**
 * Build a Google Maps directions URL to `place`. Prefers the formatted address
 * as the destination label, falling back to the venue name; includes
 * destination_place_id when available for an exact match. No origin is set.
 */
export function buildDirectionsUrl(place: DirectionsPlace): string {
  const address = typeof place.address === 'string' ? place.address : '';
  const name = typeof place.name === 'string' ? place.name : '';
  const destination = address || name;
  const placeId = typeof place.place_id === 'string' ? place.place_id : '';

  const params = new URLSearchParams({ api: '1', destination });
  if (placeId) {
    params.set('destination_place_id', placeId);
  }
  return `https://www.google.com/maps/dir/?${params.toString()}`;
}
