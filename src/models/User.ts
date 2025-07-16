import { v4 as uuidv4 } from 'uuid';
import bcrypt from 'bcryptjs';
import jwt from 'jsonwebtoken';
import { query } from '../config/database.js';

export interface User {
  id: string;
  email: string;
  password_hash?: string;
  username?: string;
  first_name?: string;
  last_name?: string;
  phone?: string;
  profile_picture_url?: string;
  google_oauth_id?: string;
  created_at: Date;
  updated_at: Date;
}

// Additional interface for user creation that includes password
export interface UserCreateInput extends Partial<User> {
  password?: string;
}

export interface UserLoginResponse {
  message: string;
  access_token: string;
  user: Omit<User, 'password_hash'>;
}

export class UserModel {
  /**
   * Create a new user
   */
  static async create(userData: UserCreateInput): Promise<User> {
    const id = userData.id || uuidv4();
    const now = new Date();

    // Ensure email is lowercase
    const email = userData.email ? userData.email.toLowerCase() : '';

    // Hash password if provided
    let password_hash = userData.password_hash;
    if (!password_hash && 'password' in userData && userData.password) {
      const salt = await bcrypt.genSalt(10);
      password_hash = await bcrypt.hash(userData.password, salt);
    }

    // Create user columns and values
    const columns = ['id', 'email', 'created_at', 'updated_at'];
    const values = [id, email, now, now];
    const placeholders = ['$1', '$2', '$3', '$4'];
    let paramIndex = 5;

    // Add optional fields if provided
    const optionalFields: Array<keyof User> = [
      'password_hash',
      'username',
      'first_name',
      'last_name',
      'phone',
      'profile_picture_url',
      'google_oauth_id',
    ];

    for (const field of optionalFields) {
      if (field === 'password_hash' && password_hash) {
        columns.push(field);
        values.push(password_hash);
        placeholders.push(`$${paramIndex++}`);
      } else if (field in userData && userData[field as keyof typeof userData] !== undefined) {
        columns.push(field);
        values.push(userData[field as keyof typeof userData] as string | Date);
        placeholders.push(`$${paramIndex++}`);
      }
    }

    // Insert user
    const result = await query(
      `INSERT INTO users (${columns.join(', ')}) 
       VALUES (${placeholders.join(', ')}) 
       RETURNING *`,
      values
    );

    return result.rows[0];
  }

  /**
   * Find user by email
   */
  static async findByEmail(email: string): Promise<User | null> {
    const result = await query('SELECT * FROM users WHERE email = $1', [email.toLowerCase()]);

    return result.rows[0] || null;
  }

  /**
   * Find user by ID
   */
  static async findById(id: string): Promise<User | null> {
    const result = await query('SELECT * FROM users WHERE id = $1', [id]);

    return result.rows[0] || null;
  }

  /**
   * Find user by Google OAuth ID
   */
  static async findByGoogleId(googleId: string): Promise<User | null> {
    const result = await query('SELECT * FROM users WHERE google_oauth_id = $1', [googleId]);

    return result.rows[0] || null;
  }

  /**
   * Update a user's Google OAuth ID
   */
  static async updateGoogleId(userId: string, googleId: string): Promise<void> {
    await query(
      `UPDATE users 
       SET google_oauth_id = $1, updated_at = $2
       WHERE id = $3`,
      [googleId, new Date(), userId]
    );
  }

  /**
   * Verify password
   */
  static async verifyPassword(password: string, hashedPassword: string): Promise<boolean> {
    return await bcrypt.compare(password, hashedPassword);
  }

  /**
   * Generate JWT token
   */
  static generateToken(user: User): string {
    const secretEnv = process.env.JWT_SECRET;
    if (!secretEnv) {
      console.error('JWT_SECRET is not defined. Using a default, insecure secret.');
    }
    const secretString = secretEnv || 'default_very_insecure_secret_for_dev_only';
    const secretBuffer = Buffer.from(secretString);

    const payload = {
      sub: user.id,
      email: user.email,
    };

    const options: jwt.SignOptions = {
      expiresIn: '24h', // Temporarily hardcode to a simple string
      algorithm: 'HS256',
    };

    return jwt.sign(payload, secretBuffer, options);
  }

  /**
   * Convert user to safe object (remove password)
   */
  static toSafeObject(user: User): Omit<User, 'password_hash'> {
    const { password_hash, ...safeUser } = user;
    return safeUser;
  }
}
