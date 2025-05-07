// Mock environment variables for tests
process.env.JWT_SECRET = 'test-secret';
process.env.JWT_EXPIRES_IN = '1h';
process.env.NODE_ENV = 'test';

// Clear all mocks after each test
afterEach(() => {
  jest.clearAllMocks();
}); 