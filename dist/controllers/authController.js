import { v4 as uuidv4 } from 'uuid';
import jwt from 'jsonwebtoken';
import { UserModel } from '../models/User.js';
/**
 * Register a new user
 */
export const register = async (req, res) => {
    try {
        const { email, password, first_name, last_name, username, phone } = req.body;
        // Validate required fields
        if (!email || !password) {
            res.status(400).json({
                error: 'Email and password are required',
                message: 'Email and password are required',
            });
            return;
        }
        // Check if user already exists
        const existingUser = await UserModel.findByEmail(email);
        if (existingUser) {
            res.status(409).json({
                error: 'User already exists',
                message: 'User already exists',
            });
            return;
        }
        // Create new user
        const user = await UserModel.create({
            email,
            password, // Will be hashed in the model
            first_name,
            last_name,
            username: username || email.split('@')[0],
            phone,
        });
        // Generate token
        const access_token = UserModel.generateToken(user);
        // Return successful response
        res.status(201).json({
            message: 'User created successfully',
            user: UserModel.toSafeObject(user),
            access_token,
        });
    }
    catch (error) {
        console.error('Error in register controller:', error);
        res.status(500).json({
            error: 'Server error',
            message: 'Error creating user',
        });
    }
};
/**
 * Login a user
 */
export const login = async (req, res) => {
    try {
        const { email, password } = req.body;
        // Validate required fields
        if (!email || !password) {
            res.status(400).json({
                error: 'Email and password are required',
                message: 'Email and password are required',
            });
            return;
        }
        // Find user by email
        const user = await UserModel.findByEmail(email);
        if (!user) {
            res.status(401).json({
                error: 'Invalid credentials',
                message: 'Invalid email or password',
            });
            return;
        }
        // Verify password
        const isPasswordValid = user.password_hash
            ? await UserModel.verifyPassword(password, user.password_hash)
            : false;
        if (!isPasswordValid) {
            res.status(401).json({
                error: 'Invalid credentials',
                message: 'Invalid email or password',
            });
            return;
        }
        // Generate token
        const access_token = UserModel.generateToken(user);
        // Return successful response
        res.status(200).json({
            message: 'Login successful',
            access_token,
            user: UserModel.toSafeObject(user),
        });
    }
    catch (error) {
        console.error('Error in login controller:', error);
        res.status(500).json({
            error: 'Server error',
            message: 'Error during login',
        });
    }
};
/**
 * Get current user
 */
export const getCurrentUser = async (req, res) => {
    try {
        // Extract user ID from request (will be set by auth middleware)
        const userId = req.user?.id;
        if (!userId) {
            res.status(401).json({
                error: 'Unauthorized',
                message: 'Not authenticated',
            });
            return;
        }
        // Find user by ID
        const user = await UserModel.findById(userId);
        if (!user) {
            res.status(404).json({
                error: 'User not found',
                message: 'User not found',
            });
            return;
        }
        // Return user data
        res.status(200).json(UserModel.toSafeObject(user));
    }
    catch (error) {
        console.error('Error in getCurrentUser controller:', error);
        res.status(500).json({
            error: 'Server error',
            message: 'Error getting user data',
        });
    }
};
/**
 * Google OAuth callback
 */
export const googleCallback = async (req, res) => {
    try {
        // Handle Google authentication
        const { credential } = req.body;
        if (!credential) {
            res.status(400).json({
                error: 'No Google credential found',
                message: 'No Google credential found',
            });
            return;
        }
        // Decode the token (which is a JWT) without verification
        // to extract information like the Google ID
        const decodedToken = jwt.decode(credential);
        if (!decodedToken || !decodedToken.sub || !decodedToken.email) {
            res.status(400).json({
                error: 'Invalid Google token',
                message: 'Invalid Google token format',
            });
            return;
        }
        const googleId = decodedToken.sub;
        const email = decodedToken.email.toLowerCase();
        const name = decodedToken.name || '';
        const firstName = decodedToken.given_name || '';
        const lastName = decodedToken.family_name || '';
        const picture = decodedToken.picture || '';
        // Check if user already exists by Google ID
        let user = await UserModel.findByGoogleId(googleId);
        // If not found by Google ID, try to find by email
        if (!user) {
            user = await UserModel.findByEmail(email);
            // If user exists but doesn't have Google ID, update it
            if (user) {
                await UserModel.updateGoogleId(user.id, googleId);
                user.google_oauth_id = googleId;
            }
            else {
                // Create new user if not found
                user = await UserModel.create({
                    email,
                    google_oauth_id: googleId,
                    first_name: firstName,
                    last_name: lastName,
                    username: email.split('@')[0],
                    profile_picture_url: picture,
                    // Generate a random password for Google users
                    password: uuidv4(),
                });
            }
        }
        // Generate token
        const access_token = UserModel.generateToken(user);
        // Return successful response
        res.status(200).json({
            success: true,
            message: 'Google authentication successful',
            access_token,
            user: UserModel.toSafeObject(user),
        });
    }
    catch (error) {
        console.error('Error in Google callback controller:', error);
        res.status(500).json({
            error: 'Server error',
            message: 'Error authenticating with Google',
        });
    }
};
/**
 * Refresh an authentication token
 */
export const refreshToken = async (req, res) => {
    try {
        const authHeader = req.headers.authorization;
        const token = req.body.token || (authHeader ? authHeader.replace('Bearer ', '') : null);
        if (!token) {
            res.status(400).json({
                error: 'Missing token',
                message: 'Token is required',
            });
            return;
        }
        let decodedToken;
        try {
            // Try to verify the token
            decodedToken = jwt.verify(token, process.env.JWT_SECRET || 'default_secret');
        }
        catch (error) {
            // If token is expired, try to extract info anyway
            if (error.name === 'TokenExpiredError') {
                decodedToken = jwt.decode(token);
            }
            else {
                throw error;
            }
        }
        if (!decodedToken || !decodedToken.sub) {
            res.status(401).json({
                error: 'Invalid token',
                message: 'Invalid token',
            });
            return;
        }
        // Find user by ID
        const user = await UserModel.findById(decodedToken.sub);
        if (!user) {
            res.status(401).json({
                error: 'Invalid token',
                message: 'User not found',
            });
            return;
        }
        // Generate a new token
        const access_token = UserModel.generateToken(user);
        // Return the new token
        res.status(200).json({
            message: 'Token refreshed',
            access_token,
        });
    }
    catch (error) {
        console.error('Error in refreshToken controller:', error);
        res.status(401).json({
            error: 'Invalid token',
            message: 'Cannot refresh token',
        });
    }
};
