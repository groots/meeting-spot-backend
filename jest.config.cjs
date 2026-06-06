/** @type {import('ts-jest').JestConfigWithTsJest} */
module.exports = {
  preset: 'ts-jest',
  testEnvironment: 'node',
  roots: ['<rootDir>/src/', '<rootDir>/tests/'],
  testMatch: ['**/*.test.ts'],
  coverageDirectory: 'coverage',
  collectCoverageFrom: ['src/**/*.ts', '!src/**/*.d.ts', '!src/server.ts'],
  moduleFileExtensions: ['ts', 'js', 'json', 'node'],
  // Source files use ESM-style ".js" extensions in relative imports (required by
  // the Node16 build). Under ts-jest/CommonJS we strip the extension so Jest
  // resolves the corresponding ".ts" file.
  moduleNameMapper: {
    '^(\\.{1,2}/.*)\\.js$': '$1',
  },
  transform: {
    '^.+\\.tsx?$': [
      'ts-jest',
      {
        tsconfig: 'tsconfig.test.json',
        diagnostics: { ignoreCodes: [151001] },
      },
    ],
  },
  setupFilesAfterEnv: ['<rootDir>/tests/setup.ts'],
};
