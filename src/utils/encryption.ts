// AES-256-GCM encryption for the user_b contact value.
// Storage format: base64(iv).base64(authTag).base64(ciphertext)
// The DB column is VarChar(255), so we guard the output length.
//
// Fresh start: no Fernet/legacy compatibility needed. The 32-byte key is
// derived deterministically from ENCRYPTION_KEY via SHA-256.
import crypto from 'crypto';
import { env } from '../config/env.js';

const IV_LENGTH = 12; // 96-bit nonce, recommended for GCM
const MAX_ENCRYPTED_LENGTH = 255;

function getKey(): Buffer {
  const secret = env.encryptionKey;
  if (!secret) {
    throw new Error('Encryption key is required');
  }
  // Deterministic 32-byte key from the secret.
  return crypto.createHash('sha256').update(secret, 'utf8').digest();
}

export function encryptContact(plaintext: string): string {
  if (!plaintext) return plaintext;

  const key = getKey();
  const iv = crypto.randomBytes(IV_LENGTH);
  const cipher = crypto.createCipheriv('aes-256-gcm', key, iv);

  const ciphertext = Buffer.concat([cipher.update(plaintext, 'utf8'), cipher.final()]);
  const authTag = cipher.getAuthTag();

  const encoded = `${iv.toString('base64')}.${authTag.toString('base64')}.${ciphertext.toString('base64')}`;

  if (encoded.length > MAX_ENCRYPTED_LENGTH) {
    throw new Error(`Encrypted value exceeds ${MAX_ENCRYPTED_LENGTH} characters`);
  }
  return encoded;
}

export function decryptContact(encoded: string): string {
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
