// Test environment configuration + global mocks.
//
// Env vars must be set BEFORE any module that reads `env` is imported. Jest
// evaluates setupFilesAfterEnv before the test files, so this is sufficient for
// the deterministic JWT/encryption keys used across suites.
process.env.NODE_ENV = 'test';
process.env.JWT_SECRET = 'test-secret';
process.env.JWT_EXPIRES_IN = '1h';
process.env.ENCRYPTION_KEY = 'test-encryption-key-deterministic-0123456789';
process.env.GOOGLE_MAPS_API_KEY = 'test-google-key';
process.env.STRIPE_SECRET_KEY = 'sk_test_dummy';
process.env.STRIPE_WEBHOOK_SECRET = 'whsec_test_dummy';
process.env.STRIPE_PRICE_PREMIUM_MONTHLY = 'price_monthly';
process.env.STRIPE_PRICE_PREMIUM_YEARLY = 'price_yearly';
process.env.MAILGUN_API_KEY = '';
process.env.MAILGUN_DOMAIN = '';
process.env.FRONTEND_URL = 'http://localhost:3000';
// Premium gating must be exercised explicitly in tests, so never bypass.
process.env.PREMIUM_BYPASS = 'false';

afterEach(() => {
  jest.clearAllMocks();
});
