// Phase 2a tests: travel-time fairness ranking, the open_now plumbing, and the
// premium gating in processMeetingRequest. placesClient is mocked so no real
// Google calls are made; distanceMatrix is stubbed per-test.
jest.mock('../src/services/placesClient', () => ({
  __esModule: true,
  nearbySearch: jest.fn(),
  distanceMatrix: jest.fn(),
  buildPhotoUrl: jest.fn((ref: string) => `https://photo/${ref}`),
}));

import {
  rankByFairness,
  processMeetingRequest,
  findMeetingSpots,
  type Coordinates,
  type MeetingSpot,
} from '../src/services/locationService';
import { nearbySearch, distanceMatrix } from '../src/services/placesClient';

const mockNearby = nearbySearch as jest.Mock;
const mockMatrix = distanceMatrix as jest.Mock;

beforeEach(() => {
  jest.clearAllMocks();
});

// Minimal MeetingSpot factory (only the fields ranking touches matter).
function spot(over: Partial<MeetingSpot> = {}): MeetingSpot {
  return {
    name: 'S',
    place_id: 'p',
    address: 'addr',
    location: { lat: 0, lng: 0 },
    rating: 4.0,
    user_ratings_total: 10,
    price_level: 2,
    photos: [],
    distance: 1,
    types: ['restaurant'],
    category: 'Food & Drink',
    subcategory: null,
    ...over,
  };
}

const ORIGINS: Coordinates[] = [
  { lat: 37.0, lon: -122.0 },
  { lat: 37.2, lon: -122.2 },
];

describe('rankByFairness', () => {
  it('minimax: orders by the smallest worst-case travel time', async () => {
    const s0 = spot({ place_id: 's0', location: { lat: 1, lng: 1 } });
    const s1 = spot({ place_id: 's1', location: { lat: 2, lng: 2 } });
    // matrix[originIdx][spotIdx]; columns follow the input order [s1, s0].
    // s1 worst=1000, s0 worst=600 → minimax orders s0 first.
    mockMatrix.mockResolvedValue([
      [100, 600], // origin A → [s1, s0]
      [1000, 600], // origin B → [s1, s0]
    ]);

    const ranked = await rankByFairness([s1, s0], ORIGINS, { objective: 'minimax' });
    expect(ranked.map((s) => s.place_id)).toEqual(['s0', 's1']);
  });

  it('balance: orders by the smallest spread between origins', async () => {
    const s0 = spot({ place_id: 's0' });
    const s1 = spot({ place_id: 's1' });
    // Columns follow the input order [s0, s1]:
    // s0 spread=0 (600/600, worst=600), s1 spread=100 (100/200, worst=200).
    mockMatrix.mockResolvedValue([
      [600, 100],
      [600, 200],
    ]);

    const balance = await rankByFairness([s0, s1], ORIGINS, { objective: 'balance' });
    expect(balance.map((s) => s.place_id)).toEqual(['s0', 's1']);
    // minimax would prefer s1 (worst 200 < 600) — proving the objective matters.
    const minimax = await rankByFairness([s0, s1], ORIGINS, { objective: 'minimax' });
    expect(minimax.map((s) => s.place_id)).toEqual(['s1', 's0']);
  });

  it('annotates per-origin travel times (a/b)', async () => {
    mockMatrix.mockResolvedValue([
      [300, 0],
      [450, 0],
    ]);
    const ranked = await rankByFairness([spot({ place_id: 'x' }), spot({ place_id: 'y' })], ORIGINS);
    const x = ranked.find((s) => s.place_id === 'x')!;
    expect(x.travel_time_a_sec).toBe(300);
    expect(x.travel_time_b_sec).toBe(450);
  });

  it('ranks spots with a missing (null) leg after complete ones', async () => {
    const s0 = spot({ place_id: 's0' });
    const s1 = spot({ place_id: 's1' });
    // s0 has a null leg → incomplete; s1 complete (even with a larger worst).
    mockMatrix.mockResolvedValue([
      [null, 9999],
      [500, 9999],
    ]);
    const ranked = await rankByFairness([s0, s1], ORIGINS);
    expect(ranked.map((s) => s.place_id)).toEqual(['s1', 's0']);
    const s0After = ranked.find((s) => s.place_id === 's0')!;
    expect(s0After.travel_time_a_sec).toBeNull();
  });

  it('degrades to the input ordering when the matrix is empty (no key/data)', async () => {
    mockMatrix.mockResolvedValue([]);
    const input = [spot({ place_id: 'a' }), spot({ place_id: 'b' })];
    const ranked = await rankByFairness(input, ORIGINS);
    expect(ranked.map((s) => s.place_id)).toEqual(['a', 'b']);
    expect(ranked[0].travel_time_a_sec).toBeUndefined();
  });

  it('is a no-op for empty spots/origins', async () => {
    expect(await rankByFairness([], ORIGINS)).toEqual([]);
    expect(mockMatrix).not.toHaveBeenCalled();
  });
});

describe('open_now plumbing', () => {
  it('findMeetingSpots passes openNow=true through to Nearby Search', async () => {
    mockNearby.mockResolvedValue([]);
    await findMeetingSpots(37, -122, 1000, 'Food & Drink', null, 5, true);
    expect(mockNearby).toHaveBeenCalledWith(expect.objectContaining({ openNow: true }));
  });

  it('omits openNow when false', async () => {
    mockNearby.mockResolvedValue([]);
    await findMeetingSpots(37, -122, 1000, 'Food & Drink', null, 5, false);
    expect(mockNearby).toHaveBeenCalledWith(expect.objectContaining({ openNow: undefined }));
  });
});

describe('processMeetingRequest premium gating', () => {
  const base = {
    requestId: 'r1',
    addressALat: 37.0,
    addressALon: -122.0,
    addressBLat: 37.1,
    addressBLon: -122.1,
    locationType: 'Food & Drink',
  };

  function manySpots(n: number) {
    return Array.from({ length: n }, (_, i) => ({
      name: `A${i}`,
      place_id: `a${i}`,
      vicinity: 'x',
      geometry: { location: { lat: 37 + i * 0.01, lng: -122 } },
      rating: 4.0,
      types: ['restaurant'],
    }));
  }

  it('premium: re-ranks via distanceMatrix and slices to 5', async () => {
    mockNearby.mockResolvedValue(manySpots(8));
    // Give every spot full travel data so all are "complete".
    mockMatrix.mockImplementation(async ({ destinations }: { destinations: unknown[] }) => [
      destinations.map((_, i) => 100 + i),
      destinations.map((_, i) => 200 + i),
    ]);

    const result = await processMeetingRequest({ ...base, isPremium: true });
    expect(result.status).toBe('completed');
    expect(mockMatrix).toHaveBeenCalledTimes(1);
    expect(result.suggestedOptions).toHaveLength(5);
  });

  it('non-premium: keeps distance ranking and never calls distanceMatrix', async () => {
    mockNearby.mockResolvedValue(manySpots(8));
    const result = await processMeetingRequest({ ...base, isPremium: false });
    expect(result.status).toBe('completed');
    expect(mockMatrix).not.toHaveBeenCalled();
    expect(result.suggestedOptions).toHaveLength(5);
  });

  it('honors max_results', async () => {
    mockNearby.mockResolvedValue(manySpots(8));
    const result = await processMeetingRequest({ ...base, maxResults: 3 });
    expect(result.suggestedOptions).toHaveLength(3);
  });
});
