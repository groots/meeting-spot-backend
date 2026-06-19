// Geographic math + processing pipeline tests for locationService.
// Golden midpoint/distance values are computed from the identical Python
// formulas (location.py) and asserted to a 1e-9 tolerance.
jest.mock('../src/services/placesClient', () => ({
  __esModule: true,
  nearbySearch: jest.fn(),
  buildPhotoUrl: jest.fn((ref: string) => `https://photo/${ref}`),
}));

import {
  calculateMidpoint,
  calculateDistance,
  getPlaceTypesForCategory,
  getCategoryKeywords,
  findMeetingSpots,
  processMeetingRequest,
} from '../src/services/locationService';
import { nearbySearch } from '../src/services/placesClient';

const mockNearby = nearbySearch as jest.Mock;
const TOL = 1e-9;

describe('locationService geo math (golden parity vs Python)', () => {
  it('calculateMidpoint: SF ↔ NYC', () => {
    const [lat, lon] = calculateMidpoint(37.7749, -122.4194, 40.7128, -74.006);
    expect(lat).toBeCloseTo(41.84648277282369, 9);
    expect(lon).toBeCloseTo(-98.75223618246126, 9);
    expect(Math.abs(lat - 41.84648277282369)).toBeLessThan(TOL);
    expect(Math.abs(lon - -98.75223618246126)).toBeLessThan(TOL);
  });

  it('calculateMidpoint: simple equatorial (0,0)↔(0,90) = (0,45)', () => {
    const [lat, lon] = calculateMidpoint(0, 0, 0, 90);
    expect(Math.abs(lat - 0)).toBeLessThan(TOL);
    expect(Math.abs(lon - 45)).toBeLessThan(TOL);
  });

  it('calculateMidpoint: LA ↔ San Diego', () => {
    const [lat, lon] = calculateMidpoint(34.0522, -118.2437, 32.7157, -117.1611);
    expect(Math.abs(lat - 33.3851247708297)).toBeLessThan(TOL);
    expect(Math.abs(lon - -117.69823938996609)).toBeLessThan(TOL);
  });

  it('calculateDistance: SF ↔ NYC ≈ 4129.086 km', () => {
    const d = calculateDistance(37.7749, -122.4194, 40.7128, -74.006);
    expect(Math.abs(d - 4129.08616505731)).toBeLessThan(1e-6);
  });

  it('calculateDistance: identical points = 0', () => {
    expect(calculateDistance(10, 10, 10, 10)).toBe(0);
  });

  it('calculateDistance: LA ↔ San Diego ≈ 179.41 km', () => {
    const d = calculateDistance(34.0522, -118.2437, 32.7157, -117.1611);
    expect(Math.abs(d - 179.41042505730314)).toBeLessThan(1e-6);
  });
});

describe('locationService category parsing', () => {
  it('maps known categories to Google place types', () => {
    expect(getPlaceTypesForCategory('Food & Drink')).toContain('restaurant');
    expect(getPlaceTypesForCategory('Night Life')).toContain('night_club');
  });

  it('falls back to restaurant for unknown categories', () => {
    expect(getPlaceTypesForCategory('Nonsense')).toEqual(['restaurant']);
  });

  it('maps frontend LocationTypeSelector labels to the right place type', () => {
    expect(getPlaceTypesForCategory('Cafe')[0]).toBe('cafe');
    expect(getPlaceTypesForCategory('Bar')[0]).toBe('bar');
    expect(getPlaceTypesForCategory('Hotel')[0]).toBe('lodging');
    expect(getPlaceTypesForCategory('Park')[0]).toBe('park');
    expect(getPlaceTypesForCategory('Library')[0]).toBe('library');
    expect(getPlaceTypesForCategory('Meeting Space')[0]).toBe('cafe');
    expect(getPlaceTypesForCategory('Restaurant / Food')[0]).toBe('restaurant');
    expect(getPlaceTypesForCategory('Other')[0]).toBe('point_of_interest');
  });

  it('returns keywords for food subcategories', () => {
    expect(getCategoryKeywords('fine dining')).toContain('fine dining');
    expect(getCategoryKeywords('unknown')).toEqual([]);
  });

  it('returns keywords for frontend cuisine choices', () => {
    expect(getCategoryKeywords('Italian')).toEqual(['Italian']);
    expect(getCategoryKeywords('Vegetarian/Vegan')).toEqual(['vegetarian']);
    expect(getCategoryKeywords('Pizza')).toEqual(['pizza']);
    // "Any Food" / "Other" carry no keyword (plain restaurant search).
    expect(getCategoryKeywords('Any Food')).toEqual([]);
  });
});

describe('findMeetingSpots', () => {
  const place = (over: Record<string, unknown> = {}) => ({
    name: 'Spot',
    place_id: 'pid',
    vicinity: '1 Main St',
    geometry: { location: { lat: 37.0, lng: -122.0 } },
    rating: 4.5,
    user_ratings_total: 100,
    price_level: 2,
    photos: [{ photo_reference: 'ref1' }, { photo_reference: 'ref2' }],
    types: ['restaurant'],
    ...over,
  });

  it('maps places, builds ≤2 photo URLs, and computes distance', async () => {
    mockNearby.mockResolvedValue([place()]);
    const spots = await findMeetingSpots(37.0, -122.0, 1000, 'Food & Drink');
    expect(spots).toHaveLength(1);
    expect(spots[0]).toMatchObject({
      name: 'Spot',
      place_id: 'pid',
      address: '1 Main St',
      rating: 4.5,
    });
    expect(spots[0].photos).toHaveLength(2);
    expect(spots[0].distance).toBeCloseTo(0, 6);
  });

  it('sorts by rating desc then distance asc', async () => {
    mockNearby.mockResolvedValue([
      place({ place_id: 'low', rating: 3.0 }),
      place({ place_id: 'high', rating: 4.9 }),
    ]);
    const spots = await findMeetingSpots(37, -122, 1000, 'Food & Drink');
    expect(spots[0].place_id).toBe('high');
    expect(spots[1].place_id).toBe('low');
  });

  it('passes a cuisine keyword (restaurant type) to Nearby Search', async () => {
    mockNearby.mockResolvedValue([place()]);
    await findMeetingSpots(37, -122, 1000, 'Restaurant / Food', 'Italian');
    expect(mockNearby).toHaveBeenCalledWith(
      expect.objectContaining({ type: 'restaurant', keyword: 'Italian' })
    );
  });

  it('applies subcategory price/rating filters', async () => {
    // "fine dining" requires price_level >= 3 and rating >= 4.0.
    mockNearby.mockResolvedValue([
      place({ place_id: 'cheap', price_level: 1, rating: 4.8 }),
      place({ place_id: 'fancy', price_level: 4, rating: 4.6 }),
    ]);
    const spots = await findMeetingSpots(37, -122, 1000, 'Food & Drink', 'fine dining');
    expect(spots.map((s) => s.place_id)).toEqual(['fancy']);
  });
});

describe('processMeetingRequest', () => {
  it('returns completed with suggestions on the first radius', async () => {
    mockNearby.mockResolvedValue([
      {
        name: 'A',
        place_id: 'a',
        vicinity: 'x',
        geometry: { location: { lat: 37, lng: -122 } },
        rating: 4.0,
        types: ['restaurant'],
      },
    ]);
    const result = await processMeetingRequest({
      requestId: 'r1',
      addressALat: 37.0,
      addressALon: -122.0,
      addressBLat: 37.1,
      addressBLon: -122.1,
      locationType: 'Food & Drink',
    });
    expect(result.status).toBe('completed');
    expect(result.success).toBe(true);
    expect(result.suggestedOptions).not.toBeNull();
  });

  it('fails when all radii return no spots', async () => {
    mockNearby.mockResolvedValue([]);
    const result = await processMeetingRequest({
      requestId: 'r1',
      addressALat: 37.0,
      addressALon: -122.0,
      addressBLat: 37.1,
      addressBLon: -122.1,
      locationType: 'Food & Drink',
    });
    expect(result.status).toBe('failed');
    expect(result.suggestedOptions).toBeNull();
  });

  it('fails when address coordinates are missing', async () => {
    const result = await processMeetingRequest({
      requestId: 'r1',
      addressALat: null,
      addressALon: null,
      addressBLat: 37.1,
      addressBLon: -122.1,
      locationType: 'Food & Drink',
    });
    expect(result.status).toBe('failed');
  });
});
