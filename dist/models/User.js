import { v4 as uuidv4 } from 'uuid';
import bcrypt from 'bcryptjs';
import jwt from 'jsonwebtoken';
import { query } from '../config/database.js';
export class UserModel {
    /**
     * Create a new user
     */
    static async create(userData) {
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
        const optionalFields = [
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
            }
            else if (field in userData && userData[field] !== undefined) {
                columns.push(field);
                values.push(userData[field]);
                placeholders.push(`$${paramIndex++}`);
            }
        }
        // Insert user
        const result = await query(`INSERT INTO users (${columns.join(', ')}) 
       VALUES (${placeholders.join(', ')}) 
       RETURNING *`, values);
        return result.rows[0];
    }
    /**
     * Find user by email
     */
    static async findByEmail(email) {
        const result = await query('SELECT * FROM users WHERE email = $1', [email.toLowerCase()]);
        return result.rows[0] || null;
    }
    /**
     * Find user by ID
     */
    static async findById(id) {
        const result = await query('SELECT * FROM users WHERE id = $1', [id]);
        return result.rows[0] || null;
    }
    /**
     * Find user by Google OAuth ID
     */
    static async findByGoogleId(googleId) {
        const result = await query('SELECT * FROM users WHERE google_oauth_id = $1', [googleId]);
        return result.rows[0] || null;
    }
    /**
     * Update a user's Google OAuth ID
     */
    static async updateGoogleId(userId, googleId) {
        await query(`UPDATE users 
       SET google_oauth_id = $1, updated_at = $2
       WHERE id = $3`, [googleId, new Date(), userId]);
    }
    /**
     * Verify password
     */
    static async verifyPassword(password, hashedPassword) {
        return await bcrypt.compare(password, hashedPassword);
    }
    /**
     * Generate JWT token
     */
    static generateToken(user) {
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
        const options = {
            expiresIn: '24h', // Temporarily hardcode to a simple string
            algorithm: 'HS256',
        };
        return jwt.sign(payload, secretBuffer, options);
    }
    /**
     * Convert user to safe object (remove password)
     */
    static toSafeObject(user) {
        const { password_hash, ...safeUser } = user;
        return safeUser;
    }
}
