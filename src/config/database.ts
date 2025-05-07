import { Pool } from 'pg';
import dotenv from 'dotenv';

dotenv.config();

// Create a pool of connections
const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
  ssl: process.env.NODE_ENV === 'production' ? { rejectUnauthorized: false } : false,
});

// Function to connect to the database
export const connectToDatabase = async (): Promise<void> => {
  try {
    // Test database connection
    const client = await pool.connect();
    console.log('Connected to PostgreSQL database');
    client.release();
  } catch (error) {
    console.error('Database connection error:', error);
    throw error;
  }
};

// Function to execute a query
export const query = async (text: string, params: any[] = []): Promise<any> => {
  try {
    const start = Date.now();
    const result = await pool.query(text, params);
    const duration = Date.now() - start;

    console.log('Executed query', { text, duration: `${duration}ms`, rows: result.rowCount });

    return result;
  } catch (error) {
    console.error('Query error:', error);
    throw error;
  }
};
