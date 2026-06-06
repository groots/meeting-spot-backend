// Geocoding service tests — axios is mocked; we assert the response shapes the
// frontend/tests depend on, plus quality classification and error handling.
jest.mock('axios', () => ({
  __esModule: true,
  default: { get: jest.fn() },
}));

import axios from 'axios';
import {
  geocodeAddress,
  reverseGeocodeCoordinates,
} from '../src/services/geocodingService';

const mockGet = (axios as unknown as { get: jest.Mock }).get;

describe('geocodeAddress', () => {
  it('returns success with coordinates + high quality for a street address', async () => {
    mockGet.mockResolvedValue({
      data: {
        status: 'OK',
        results: [
          {
            formatted_address: '1600 Amphitheatre Pkwy, Mountain View, CA',
            geometry: { location: { lat: 37.4224, lng: -122.0841 } },
            types: ['street_address'],
          },
        ],
      },
    });

    const res = await geocodeAddress('1600 Amphitheatre Pkwy');
    expect(res).toEqual({
      success: true,
      lat: 37.4224,
      lng: -122.0841,
      formatted_address: '1600 Amphitheatre Pkwy, Mountain View, CA',
      quality: 'high',
      coordinates: { lat: 37.4224, lng: -122.0841 },
    });
  });

  it('classifies locality results as medium quality', async () => {
    mockGet.mockResolvedValue({
      data: {
        status: 'OK',
        results: [
          {
            formatted_address: 'San Francisco, CA',
            geometry: { location: { lat: 37.77, lng: -122.41 } },
            types: ['locality'],
          },
        ],
      },
    });
    const res = await geocodeAddress('San Francisco');
    expect(res.success && res.quality).toBe('medium');
  });

  it('returns a failure for an empty address (no network call)', async () => {
    const res = await geocodeAddress('');
    expect(res).toEqual({ success: false, error: 'Address cannot be empty' });
    expect(mockGet).not.toHaveBeenCalled();
  });

  it('maps ZERO_RESULTS to a not-found failure', async () => {
    mockGet.mockResolvedValue({ data: { status: 'ZERO_RESULTS', results: [] } });
    const res = await geocodeAddress('nowhere');
    expect(res).toEqual({
      success: false,
      error: 'No results found for the given address',
    });
  });

  it('wraps transport errors', async () => {
    mockGet.mockRejectedValue(new Error('network down'));
    const res = await geocodeAddress('x');
    expect(res.success).toBe(false);
    if (!res.success) expect(res.error).toContain('network down');
  });
});

describe('reverseGeocodeCoordinates', () => {
  it('rejects invalid coordinates without a network call', async () => {
    const res = await reverseGeocodeCoordinates(999, 999);
    expect(res).toEqual({
      success: false,
      error: 'Invalid latitude/longitude values',
    });
    expect(mockGet).not.toHaveBeenCalled();
  });

  it('returns formatted_address + quality on success', async () => {
    mockGet.mockResolvedValue({
      data: {
        status: 'OK',
        results: [
          { formatted_address: 'Somewhere', types: ['premise'] },
        ],
      },
    });
    const res = await reverseGeocodeCoordinates(37.0, -122.0);
    expect(res).toEqual({
      success: true,
      formatted_address: 'Somewhere',
      quality: 'high',
    });
  });
});
