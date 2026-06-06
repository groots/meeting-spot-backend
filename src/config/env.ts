// Centralized, typed environment loader. Import `env` everywhere instead of
// reading process.env directly so defaults and parsing live in one place.
import dotenv from 'dotenv';

dotenv.config();

const bool = (v: string | undefined, fallback = false): boolean => {
  if (v === undefined) return fallback;
  return ['1', 'true', 'yes', 'on'].includes(v.toLowerCase());
};

const list = (v: string | undefined): string[] =>
  (v ?? '')
    .split(',')
    .map((s) => s.trim())
    .filter(Boolean);

export const env = {
  nodeEnv: process.env.NODE_ENV || 'development',
  isProduction: process.env.NODE_ENV === 'production',
  isTest: process.env.NODE_ENV === 'test',
  port: parseInt(process.env.PORT || '8081', 10),

  databaseUrl: process.env.DATABASE_URL || '',

  frontendUrl: process.env.FRONTEND_URL || 'http://localhost:3000',
  corsOrigins: list(process.env.CORS_ORIGINS),

  jwtSecret: process.env.JWT_SECRET || 'default_very_insecure_secret_for_dev_only',
  encryptionKey: process.env.ENCRYPTION_KEY || 'dev_encryption_key_change_me_32b!',

  googleMapsApiKey: process.env.GOOGLE_MAPS_API_KEY || '',
  googleClientId: process.env.GOOGLE_CLIENT_ID || '',
  googleClientSecret: process.env.GOOGLE_CLIENT_SECRET || '',

  mailgunApiKey: process.env.MAILGUN_API_KEY || '',
  mailgunDomain: process.env.MAILGUN_DOMAIN || '',

  stripeSecretKey: process.env.STRIPE_SECRET_KEY || '',
  stripeWebhookSecret: process.env.STRIPE_WEBHOOK_SECRET || '',
  stripePriceMonthly: process.env.STRIPE_PRICE_PREMIUM_MONTHLY || '',
  stripePriceYearly: process.env.STRIPE_PRICE_PREMIUM_YEARLY || '',

  twilioAccountSid: process.env.TWILIO_ACCOUNT_SID || '',
  twilioAuthToken: process.env.TWILIO_AUTH_TOKEN || '',
  twilioFromNumber: process.env.TWILIO_FROM_NUMBER || '',

  premiumBypass: bool(process.env.PREMIUM_BYPASS, false),
  profilePicturesDir: process.env.PROFILE_PICTURES_DIR || 'uploads/profile-pictures',
};

export default env;
