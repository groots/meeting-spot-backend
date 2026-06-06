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
import { errorHandler, notFoundHandler } from './middleware/errorHandler.js';

const app = express();

// Security + CORS
app.use(helmet());
app.use(
  cors({
    origin: env.corsOrigins.length > 0 ? env.corsOrigins : env.frontendUrl || '*',
    credentials: true,
  })
);

// Stripe webhook needs the RAW body for signature verification. Mount express.raw
// on its exact path BEFORE the JSON parser. body-parser sets req._body=true after
// reading, so the subsequent express.json() skips this request.
app.use('/api/v1/payments/webhook', express.raw({ type: '*/*' }));

app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// Health check
app.get('/api/v1/health', (_req, res) => {
  res.status(200).json({
    status: 'OK',
    message: 'Meeting Spot Backend API is running',
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
    },
  });
});

// 404 + central error handler (must be last)
app.use(notFoundHandler);
app.use(errorHandler);

async function startServer(): Promise<void> {
  try {
    await prisma.$connect();
    app.listen(env.port, () => {
      console.log(`Meeting Spot Backend running on port ${env.port}`);
      console.log(`Health check: http://localhost:${env.port}/api/v1/health`);
      console.log(`Environment: ${env.nodeEnv}`);
    });
  } catch (error) {
    console.error('Failed to start server:', error);
    process.exit(1);
  }
}

// Only auto-start outside of tests (tests import the app via supertest).
if (!env.isTest) {
  void startServer();
}

export default app;
