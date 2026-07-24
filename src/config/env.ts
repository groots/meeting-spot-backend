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
  // OAuth redirect for Google Calendar free/busy connect. Must match the
  // authorized redirect URI in the Google Cloud console.
  googleCalendarRedirectUri:
    process.env.GOOGLE_CALENDAR_REDIRECT_URI ||
    `http://localhost:${parseInt(process.env.PORT || '8081', 10)}/api/v1/auth/google/calendar/callback`,

  facebookAppId: process.env.FACEBOOK_APP_ID || '',
  facebookAppSecret: process.env.FACEBOOK_APP_SECRET || '',

  mailgunApiKey: process.env.MAILGUN_API_KEY || '',
  mailgunDomain: process.env.MAILGUN_DOMAIN || '',
  // Optional sender overrides. MAIL_FROM may be a bare address or
  // "Name <addr@domain>"; defaults to a noreply on the Mailgun domain.
  // MAIL_REPLY_TO should be a monitored mailbox so replies go somewhere real.
  mailFrom: process.env.MAIL_FROM || '',
  mailReplyTo: process.env.MAIL_REPLY_TO || '',

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

// Known insecure dev-only defaults. In production these must be overridden by
// real env vars, or we fail closed (crash-loop loudly) rather than run insecure.
const INSECURE_JWT_DEFAULT = 'default_very_insecure_secret_for_dev_only';
const INSECURE_ENCRYPTION_DEFAULT = 'dev_encryption_key_change_me_32b!';

// Fail-closed production guard. Throwing here happens at import time, before the
// server binds a port, so a misconfigured prod deploy crash-loops instead of
// serving traffic with insecure secrets.
if (env.isProduction) {
  const problems: string[] = [];
  if (!process.env.JWT_SECRET || process.env.JWT_SECRET === INSECURE_JWT_DEFAULT) {
    problems.push('JWT_SECRET is unset or using the insecure dev default');
  }
  if (
    !process.env.ENCRYPTION_KEY ||
    process.env.ENCRYPTION_KEY === INSECURE_ENCRYPTION_DEFAULT
  ) {
    problems.push('ENCRYPTION_KEY is unset or using the insecure dev default');
  }
  if (!process.env.DATABASE_URL) {
    problems.push('DATABASE_URL is unset');
  }
  if (problems.length > 0) {
    throw new Error(
      `Refusing to start in production with insecure configuration:\n- ${problems.join('\n- ')}`
    );
  }
}

export default env;
