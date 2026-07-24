// AES-256-GCM encryption helpers.
// Storage format: base64(iv).base64(authTag).base64(ciphertext)
//
// Fresh start: no Fernet/legacy compatibility needed. The 32-byte key is
// derived deterministically from ENCRYPTION_KEY via SHA-256.
import crypto from 'crypto';
import { env } from '../config/env.js';

const IV_LENGTH = 12; // 96-bit nonce, recommended for GCM
const MAX_CONTACT_ENCRYPTED_LENGTH = 255;

function getKey(): Buffer {
  const secret = env.encryptionKey;
  if (!secret) {
    throw new Error('Encryption key is required');
  }
  // Deterministic 32-byte key from the secret.
  return crypto.createHash('sha256').update(secret, 'utf8').digest();
}

/** Encrypt an arbitrary secret (e.g. OAuth refresh tokens). No length cap. */
export function encryptSecret(plaintext: string): string {
  if (!plaintext) return plaintext;

  const key = getKey();
  const iv = crypto.randomBytes(IV_LENGTH);
  const cipher = crypto.createCipheriv('aes-256-gcm', key, iv);

  const ciphertext = Buffer.concat([cipher.update(plaintext, 'utf8'), cipher.final()]);
  const authTag = cipher.getAuthTag();

  return `${iv.toString('base64')}.${authTag.toString('base64')}.${ciphertext.toString('base64')}`;
}

/** Decrypt a value produced by encryptSecret / encryptContact. */
export function decryptSecret(encoded: string): string {
  if (!encoded) return encoded;

  const parts = encoded.split('.');
  if (parts.length !== 3) {
    throw new Error('Invalid encrypted value format');
  }
  const [ivB64, tagB64, ctB64] = parts;

  const key = getKey();
  const iv = Buffer.from(ivB64, 'base64');
  const authTag = Buffer.from(tagB64, 'base64');
  const ciphertext = Buffer.from(ctB64, 'base64');

  const decipher = crypto.createDecipheriv('aes-256-gcm', key, iv);
  decipher.setAuthTag(authTag);

  const plaintext = Buffer.concat([decipher.update(ciphertext), decipher.final()]);
  return plaintext.toString('utf8');
}

/** Encrypt user_b contact; enforces the VarChar(255) column budget. */
export function encryptContact(plaintext: string): string {
  const encoded = encryptSecret(plaintext);
  if (encoded.length > MAX_CONTACT_ENCRYPTED_LENGTH) {
    throw new Error(`Encrypted value exceeds ${MAX_CONTACT_ENCRYPTED_LENGTH} characters`);
  }
  return encoded;
}

export function decryptContact(encoded: string): string {
  return decryptSecret(encoded);
}
