// placesClient.distanceMatrix tests — axios is mocked. Asserts the request
// shape (pipe-joined origins/destinations), the seconds grid parsing, per-cell
// null on non-OK elements, and empty-input/no-key degradation.
jest.mock('axios', () => ({
  __esModule: true,
  default: { get: jest.fn() },
}));

import axios from 'axios';
import { distanceMatrix } from '../src/services/placesClient';

const mockGet = (axios as unknown as { get: jest.Mock }).get;

const ORIGINS = [
  { lat: 37.0, lon: -122.0 },
  { lat: 37.2, lon: -122.2 },
];
const DESTS = [
  { lat: 37.1, lon: -122.1 },
  { lat: 37.3, lon: -122.3 },
];

describe('distanceMatrix', () => {
  it('returns a seconds grid (origins × destinations)', async () => {
    mockGet.mockResolvedValue({
      data: {
        status: 'OK',
        rows: [
          { elements: [{ status: 'OK', duration: { value: 100 } }, { status: 'OK', duration: { value: 200 } }] },
          { elements: [{ status: 'OK', duration: { value: 300 } }, { status: 'OK', duration: { value: 400 } }] },
        ],
      },
    });

    const grid = await distanceMatrix({ origins: ORIGINS, destinations: DESTS, apiKey: 'k' });
    expect(grid).toEqual([
      [100, 200],
      [300, 400],
    ]);

    // Request shape: pipe-joined "lat,lon".
    const params = mockGet.mock.calls[0][1].params;
    expect(params.origins).toBe('37,-122|37.2,-122.2');
    expect(params.destinations).toBe('37.1,-122.1|37.3,-122.3');
    expect(params.mode).toBe('driving');
  });

  it('maps non-OK elements to null', async () => {
    mockGet.mockResolvedValue({
      data: {
        status: 'OK',
        rows: [{ elements: [{ status: 'ZERO_RESULTS' }, { status: 'OK', duration: { value: 50 } }] }],
      },
    });
    const grid = await distanceMatrix({ origins: [ORIGINS[0]], destinations: DESTS, apiKey: 'k' });
    expect(grid).toEqual([[null, 50]]);
  });

  it('returns [] on a non-OK top-level status', async () => {
    mockGet.mockResolvedValue({ data: { status: 'REQUEST_DENIED' } });
    const grid = await distanceMatrix({ origins: ORIGINS, destinations: DESTS, apiKey: 'k' });
    expect(grid).toEqual([]);
  });

  it('degrades to [] without a key (no network call)', async () => {
    const grid = await distanceMatrix({ origins: ORIGINS, destinations: DESTS, apiKey: '' });
    expect(grid).toEqual([]);
    expect(mockGet).not.toHaveBeenCalled();
  });

  it('degrades to [] for empty origins/destinations (no network call)', async () => {
    expect(await distanceMatrix({ origins: [], destinations: DESTS, apiKey: 'k' })).toEqual([]);
    expect(await distanceMatrix({ origins: ORIGINS, destinations: [], apiKey: 'k' })).toEqual([]);
    expect(mockGet).not.toHaveBeenCalled();
  });
});
