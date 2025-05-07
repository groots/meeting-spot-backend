import tseslint from 'typescript-eslint';

export default tseslint.config({
  extends: ['eslint:recommended', 'plugin:@typescript-eslint/recommended'],
  ignores: ['dist/**', 'node_modules/**'],
  languageOptions: {
    parser: tseslint.parser,
    parserOptions: {
      project: './tsconfig.json',
    },
  },
  plugins: {
    '@typescript-eslint': tseslint.plugin,
  },
  rules: {
    '@typescript-eslint/no-explicit-any': 'warn',
    '@typescript-eslint/explicit-function-return-type': 'off',
    'no-console': 'warn',
  },
});
