import typescriptEslint from 'typescript-eslint';

export default [
  ...typescriptEslint.configs.recommended,
  {
    ignores: [
      'dist/**',
      'node_modules/**',
      '**/*.js',
      '**/*.mjs',
      '**/*.cjs',
      '.eslintrc.js',
      'jest.config.js'
    ],
  languageOptions: {
    parserOptions: {
      project: './tsconfig.json',
    },
  },
  rules: {
    '@typescript-eslint/no-explicit-any': 'warn',
    '@typescript-eslint/explicit-function-return-type': 'off',
    'no-console': 'warn',
      '@typescript-eslint/no-unused-vars': ['warn', {
        'argsIgnorePattern': '^_',
        'varsIgnorePattern': '^_'
      }],
      '@typescript-eslint/no-namespace': 'off',
  },
  }
];
