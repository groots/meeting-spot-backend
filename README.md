# Find A Meeting Spot - Node.js Backend

This is a new Node.js backend implementation designed to address authentication issues present in the original Python backend for the Find A Meeting Spot application.

## Why a New Backend?

The original Python backend had persistent authentication problems:

1. Login failures and random session expiration
2. Password reset functionality not working consistently
3. Google authentication errors
4. Token refresh issues causing repeated logouts

This Node.js implementation provides:

- Robust authentication flow with proper error handling
- Reliable token refresh mechanism
- Compatible API endpoints that match the original Python backend
- Better error reporting and logging

## Getting Started

### Prerequisites

- Node.js 16+
- PostgreSQL
- npm or yarn

### Installation

1. Clone the repository
2. Install dependencies:

```bash
cd new-backend
npm install
```

3. Create a `.env` file (use `.env.example` as a template)
4. Set up the database:

```bash
# Make sure PostgreSQL is running and the database exists
```

5. Start the development server:

```bash
npm run dev
```

## Project Structure

The backend follows a clean architecture:

```
new-backend/
├── src/
│   ├── config/           # Configuration files
│   ├── controllers/      # Request handlers
│   ├── middleware/       # Express middleware
│   ├── models/           # Data models
│   ├── routes/           # API routes
│   ├── utils/            # Utility functions
│   └── server.ts         # Server entry point
├── tests/                # Unit and integration tests
├── tsconfig.json         # TypeScript configuration
└── package.json          # Project dependencies
```

## Authentication Features

This backend implements:

1. **User Registration**

   - Secure password hashing with bcrypt
   - Email validation
   - Duplicate account checking

2. **User Login**

   - Secure password verification
   - JWT token generation with proper expiry
   - Protection against common attacks

3. **Google Authentication**

   - Secure OAuth 2.0 flow
   - Automatic account creation or linking

4. **Token Refresh**
   - Graceful handling of expired tokens
   - Transparent renewal of authentication

## API Endpoints

### Authentication

| Method | Endpoint                       | Description                  |
| ------ | ------------------------------ | ---------------------------- |
| POST   | `/api/v1/auth/register`        | Register a new user          |
| POST   | `/api/v1/auth/login`           | Login user                   |
| POST   | `/api/v1/auth/google/callback` | Google OAuth callback        |
| POST   | `/api/v1/auth/refresh`         | Refresh authentication token |
| GET    | `/api/v1/auth/me`              | Get current user profile     |

## Testing

Run tests with:

```bash
npm run test
```

## Deployment

This backend can be deployed to Google Cloud Run using:

```bash
# Build Docker image
docker build -t find-a-meeting-spot-backend .

# Deploy to Cloud Run
gcloud run deploy find-a-meeting-spot-backend \
  --image find-a-meeting-spot-backend \
  --platform managed \
  --allow-unauthenticated
```

## Contributing

1. Create feature branches from `main`
2. Make changes and write tests
3. Submit a pull request

## License

MIT
