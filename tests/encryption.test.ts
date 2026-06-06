// AES-256-GCM contact encryption round-trip + format/guard tests.
import { encryptContact, decryptContact } from '../src/utils/encryption';

describe('encryptContact / decryptContact', () => {
  it('round-trips a value', () => {
    const plain = 'bob@example.com';
    const enc = encryptContact(plain);
    expect(enc).not.toBe(plain);
    expect(decryptContact(enc)).toBe(plain);
  });

  it('produces the iv.tag.ciphertext base64 format', () => {
    const enc = encryptContact('+15551234567');
    expect(enc.split('.')).toHaveLength(3);
  });

  it('uses a fresh IV each time (ciphertext differs)', () => {
    const a = encryptContact('same-value');
    const b = encryptContact('same-value');
    expect(a).not.toBe(b);
    expect(decryptContact(a)).toBe(decryptContact(b));
  });

  it('passes empty strings through unchanged', () => {
    expect(encryptContact('')).toBe('');
    expect(decryptContact('')).toBe('');
  });

  it('throws on a malformed encrypted value', () => {
    expect(() => decryptContact('not-valid')).toThrow('Invalid encrypted value format');
  });

  it('keeps output within the 255-char DB column limit', () => {
    const enc = encryptContact('a'.repeat(120));
    expect(enc.length).toBeLessThanOrEqual(255);
  });
});
