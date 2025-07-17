import express from 'express';
import cors from 'cors';
import helmet from 'helmet';
import dotenv from 'dotenv';
import { connectToDatabase } from './config/database.js';
import authRoutes from './routes/authRoutes.js';

// Load environment variables
dotenv.config();

// Initialize express
const app = express();
const port = process.env.PORT || 5000;

// Middleware
app.use(helmet());
app.use(
  cors({
    origin: process.env.FRONTEND_URL || '*',
    credentials: true,
  })
);
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// Health check endpoint
app.get('/api/v1/health', (req, res) => {
  res.status(200).json({
    status: 'OK',
    message: 'Meeting Spot Backend API is running',
    timestamp: new Date().toISOString(),
    environment: process.env.NODE_ENV || 'development',
  });
});

// Debug endpoint to check database and create table if needed
app.get('/api/v1/debug/db-setup', async (req, res) => {
  try {
    // Check if DATABASE_URL exists
    if (!process.env.DATABASE_URL) {
      return res.status(500).json({
        error: 'DATABASE_URL not configured',
        hasDatabase: false,
      });
    }

    // Test basic connection
    const { query } = await import('./config/database.js');
    
    // Check if users table exists
    const tableCheck = await query(`
      SELECT table_name 
      FROM information_schema.tables 
      WHERE table_schema = 'public' AND table_name = 'users'
    `);
    
    const tableExists = tableCheck.rows.length > 0;
    
    // If table doesn't exist, create it
    if (!tableExists) {
      await query(`
        CREATE TABLE IF NOT EXISTS users (
          id UUID PRIMARY KEY,
          email VARCHAR(255) NOT NULL UNIQUE,
          password_hash VARCHAR(255),
          username VARCHAR(100),
          first_name VARCHAR(100),
          last_name VARCHAR(100),
          phone VARCHAR(20),
          profile_picture_url TEXT,
          google_oauth_id VARCHAR(255),
          created_at TIMESTAMP WITH TIME ZONE NOT NULL,
          updated_at TIMESTAMP WITH TIME ZONE NOT NULL
        )
      `);
      
      // Create indexes
      await query('CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)');
      await query('CREATE INDEX IF NOT EXISTS idx_users_google_oauth_id ON users(google_oauth_id)');
    }
    
    // Check again after creation
    const finalCheck = await query(`
      SELECT table_name 
      FROM information_schema.tables 
      WHERE table_schema = 'public' AND table_name = 'users'
    `);
    
    // Test a simple query
    const userCount = await query('SELECT COUNT(*) as count FROM users');
    
    res.json({
      status: 'OK',
      hasDatabase: true,
      hasDatabaseUrl: !!process.env.DATABASE_URL,
      tableExisted: tableExists,
      tableExistsNow: finalCheck.rows.length > 0,
      userCount: userCount.rows[0].count,
      jwtSecret: !!process.env.JWT_SECRET,
      encryptionKey: !!process.env.ENCRYPTION_KEY,
    });
  } catch (error) {
    console.error('Database setup error:', error);
    res.status(500).json({
      error: 'Database setup failed',
      message: error instanceof Error ? error.message : 'Unknown error',
      hasDatabase: !!process.env.DATABASE_URL,
      jwtSecret: !!process.env.JWT_SECRET,
      encryptionKey: !!process.env.ENCRYPTION_KEY,
    });
  }
});

// Routes
app.use('/api/v1/auth', authRoutes);

// Default route
app.get('/', (req, res) => {
  res.status(200).json({
    message: 'Welcome to Meeting Spot Backend API',
    version: '1.0.0',
    endpoints: {
      health: '/api/v1/health',
      auth: '/api/v1/auth',
    },
  });
});

// Error handling middleware
app.use((err: any, req: express.Request, res: express.Response, next: express.NextFunction) => {
  console.error('Error:', err);
  res.status(500).json({
    error: 'Internal server error',
    message: process.env.NODE_ENV === 'development' ? err.message : 'Something went wrong',
  });
});

// 404 handler
app.use('*', (req, res) => {
  res.status(404).json({
    error: 'Route not found',
    message: `Cannot ${req.method} ${req.originalUrl}`,
  });
});

async function startServer() {
  try {
    // Connect to database
    await connectToDatabase();

    // Start server
    app.listen(port, () => {
      console.log(`🚀 Meeting Spot Backend running on port ${port}`);
      console.log(`📊 Health check: http://localhost:${port}/api/v1/health`);
      console.log(`🌍 Environment: ${process.env.NODE_ENV || 'development'}`);
    });
  } catch (error) {
    console.error('Failed to start server:', error);
    process.exit(1);
  }
}

startServer();

export default app;
