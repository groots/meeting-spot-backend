// Input validation helpers. `validateAddress` is ported from the Python
// reference (app/utils/geocoding.py::validate_address).

export interface AddressValidation {
  valid: boolean;
  message: string;
}

const STREET_REGEX =
  /\b(street|st\.?|avenue|ave\.?|road|rd\.?|boulevard|blvd\.?|lane|ln\.?|drive|dr\.?|way|court|ct\.?|plaza|square|sq\.?|parkway|pkwy\.?|place|pl\.?)\b/i;

export function validateAddress(address: string): AddressValidation {
  if (!address || !address.trim()) {
    return { valid: false, message: 'Address cannot be empty' };
  }
  if (address.trim().length < 5) {
    return { valid: false, message: 'Address is too short' };
  }

  const hasNumber = /\d/.test(address);
  const hasStreet = STREET_REGEX.test(address);

  if (!hasNumber) {
    return { valid: false, message: 'Address should include a street number' };
  }
  if (!hasStreet) {
    return { valid: false, message: 'Address should include a street name' };
  }

  const hasCityState = /,\s*([A-Za-z\s]+)/.test(address);
  const hasZip = /\b\d{5}(?:-\d{4})?\b/.test(address);

  if (!hasCityState && !hasZip) {
    return { valid: false, message: 'Address should include city, state, or postal code' };
  }

  return { valid: true, message: 'Address appears valid' };
}

export function validateCoordinates(lat: unknown, lng: unknown): boolean {
  const latNum = typeof lat === 'string' ? parseFloat(lat) : (lat as number);
  const lngNum = typeof lng === 'string' ? parseFloat(lng) : (lng as number);
  if (!Number.isFinite(latNum) || !Number.isFinite(lngNum)) return false;
  return latNum >= -90 && latNum <= 90 && lngNum >= -180 && lngNum <= 180;
}

const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export function isValidEmail(email: string): boolean {
  return typeof email === 'string' && EMAIL_REGEX.test(email);
}
