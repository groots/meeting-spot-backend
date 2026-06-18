import express from 'express';
import cors from 'cors';
import helmet from 'helmet';
import { env } from './config/env.js';
import { prisma } from './config/prisma.js';
import authRoutes from './routes/authRoutes.js';
import meetingRequestRoutes from './routes/meetingRequestRoutes.js';
import contactRoutes from './routes/contactRoutes.js';
import paymentRoutes from './routes/paymentRoutes.js';
import userRoutes from './routes/userRoutes.js';
import geocodingRoutes from './routes/geocodingRoutes.js';
import { errorHandler, notFoundHandler } from './middleware/errorHandler.js';

const app = express();

// Behind Render's proxy: trust exactly one hop so req.ip / X-Forwarded-For is
// the real client IP (needed for per-IP rate limiting). Use 1, not `true`,
// which would trust any spoofed XFF header.
app.set('trust proxy', 1);

// Security + CORS. Fail closed: never fall back to '*'. In prod we use the
// explicit CORS_ORIGINS list (or FRONTEND_URL); in dev FRONTEND_URL defaults
// to http://localhost:3000.
app.use(helmet());
app.use(
  cors({
    origin: env.corsOrigins.length > 0 ? env.corsOrigins : env.frontendUrl,
    credentials: true,
  })
);

// Stripe webhook needs the RAW body for signature verification. Mount express.raw
// on its exact path BEFORE the JSON parser. body-parser sets req._body=true after
// reading, so the subsequent express.json() skips this request.
app.use('/api/v1/payments/webhook', express.raw({ type: '*/*' }));

app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// Health check — verifies DB connectivity so a misconfigured DATABASE_URL
// surfaces as a 503 (failing Render's health check) instead of silently
// returning OK while every real request fails.
app.get('/api/v1/health', async (_req, res) => {
  let database = 'up';
  try {
    await prisma.$queryRaw`SELECT 1`;
  } catch {
    database = 'down';
  }
  const healthy = database === 'up';
  res.status(healthy ? 200 : 503).json({
    status: healthy ? 'OK' : 'DEGRADED',
    message: 'Meeting Spot Backend API is running',
    database,
    timestamp: new Date().toISOString(),
    environment: env.nodeEnv,
  });
});

// Routes
app.use('/api/v1/auth', authRoutes);
app.use('/api/v1/meeting-requests', meetingRequestRoutes);
app.use('/api/v1/contacts', contactRoutes);
app.use('/api/v1/payments', paymentRoutes);
app.use('/api/v1/users', userRoutes);
app.use('/api/v1/geocoding', geocodingRoutes);

// Root
app.get('/', (_req, res) => {
  res.status(200).json({
    message: 'Welcome to Meeting Spot Backend API',
    version: '1.0.0',
    endpoints: {
      health: '/api/v1/health',
      auth: '/api/v1/auth',
      meetingRequests: '/api/v1/meeting-requests',
      contacts: '/api/v1/contacts',
      payments: '/api/v1/payments',
      users: '/api/v1/users',
      geocoding: '/api/v1/geocoding',
    },
  });
});

// 404 + central error handler (must be last)
app.use(notFoundHandler);
app.use(errorHandler);

async function startServer(): Promise<void> {
  // Bind the port regardless of DB state so the health check can report a 503
  // (database: "down") instead of the process crash-looping on boot with
  // "no open ports detected" when DATABASE_URL is wrong/unreachable.
  app.listen(env.port, () => {
    console.log(`Meeting Spot Backend running on port ${env.port}`);
    console.log(`Health check: http://localhost:${env.port}/api/v1/health`);
    console.log(`Environment: ${env.nodeEnv}`);
  });
  try {
    await prisma.$connect();
    console.log('Database connected');
  } catch (error) {
    console.error(
      'Database connection failed at startup; /api/v1/health will report 503 until it recovers:',
      error
    );
  }
}

// Only auto-start outside of tests (tests import the app via supertest).
if (!env.isTest) {
  void startServer();
}

export default app;
