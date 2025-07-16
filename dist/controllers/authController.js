"use strict";
var __awaiter = (this && this.__awaiter) || function (thisArg, _arguments, P, generator) {
    function adopt(value) { return value instanceof P ? value : new P(function (resolve) { resolve(value); }); }
    return new (P || (P = Promise))(function (resolve, reject) {
        function fulfilled(value) { try { step(generator.next(value)); } catch (e) { reject(e); } }
        function rejected(value) { try { step(generator["throw"](value)); } catch (e) { reject(e); } }
        function step(result) { result.done ? resolve(result.value) : adopt(result.value).then(fulfilled, rejected); }
        step((generator = generator.apply(thisArg, _arguments || [])).next());
    });
};
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.refreshToken = exports.googleCallback = exports.getCurrentUser = exports.login = exports.register = void 0;
const uuid_1 = require("uuid");
const jsonwebtoken_1 = __importDefault(require("jsonwebtoken"));
const User_1 = require("../models/User");
/**
 * Register a new user
 */
const register = (req, res) => __awaiter(void 0, void 0, void 0, function* () {
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
        const existingUser = yield User_1.UserModel.findByEmail(email);
        if (existingUser) {
            res.status(409).json({
                error: 'User already exists',
                message: 'User already exists',
            });
            return;
        }
        // Create new user
        const user = yield User_1.UserModel.create({
            email,
            password, // Will be hashed in the model
            first_name,
            last_name,
            username: username || email.split('@')[0],
            phone,
        });
        // Generate token
        const access_token = User_1.UserModel.generateToken(user);
        // Return successful response
        res.status(201).json({
            message: 'User created successfully',
            user: User_1.UserModel.toSafeObject(user),
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
});
exports.register = register;
/**
 * Login a user
 */
const login = (req, res) => __awaiter(void 0, void 0, void 0, function* () {
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
        const user = yield User_1.UserModel.findByEmail(email);
        if (!user) {
            res.status(401).json({
                error: 'Invalid credentials',
                message: 'Invalid email or password',
            });
            return;
        }
        // Verify password
        const isPasswordValid = user.password_hash
            ? yield User_1.UserModel.verifyPassword(password, user.password_hash)
            : false;
        if (!isPasswordValid) {
            res.status(401).json({
                error: 'Invalid credentials',
                message: 'Invalid email or password',
            });
            return;
        }
        // Generate token
        const access_token = User_1.UserModel.generateToken(user);
        // Return successful response
        res.status(200).json({
            message: 'Login successful',
            access_token,
            user: User_1.UserModel.toSafeObject(user),
        });
    }
    catch (error) {
        console.error('Error in login controller:', error);
        res.status(500).json({
            error: 'Server error',
            message: 'Error during login',
        });
    }
});
exports.login = login;
/**
 * Get current user
 */
const getCurrentUser = (req, res) => __awaiter(void 0, void 0, void 0, function* () {
    var _a;
    try {
        // Extract user ID from request (will be set by auth middleware)
        const userId = (_a = req.user) === null || _a === void 0 ? void 0 : _a.id;
        if (!userId) {
            res.status(401).json({
                error: 'Unauthorized',
                message: 'Not authenticated',
            });
            return;
        }
        // Find user by ID
        const user = yield User_1.UserModel.findById(userId);
        if (!user) {
            res.status(404).json({
                error: 'User not found',
                message: 'User not found',
            });
            return;
        }
        // Return user data
        res.status(200).json(User_1.UserModel.toSafeObject(user));
    }
    catch (error) {
        console.error('Error in getCurrentUser controller:', error);
        res.status(500).json({
            error: 'Server error',
            message: 'Error getting user data',
        });
    }
});
exports.getCurrentUser = getCurrentUser;
/**
 * Google OAuth callback
 */
const googleCallback = (req, res) => __awaiter(void 0, void 0, void 0, function* () {
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
        const decodedToken = jsonwebtoken_1.default.decode(credential);
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
        let user = yield User_1.UserModel.findByGoogleId(googleId);
        // If not found by Google ID, try to find by email
        if (!user) {
            user = yield User_1.UserModel.findByEmail(email);
            // If user exists but doesn't have Google ID, update it
            if (user) {
                yield User_1.UserModel.updateGoogleId(user.id, googleId);
                user.google_oauth_id = googleId;
            }
            else {
                // Create new user if not found
                user = yield User_1.UserModel.create({
                    email,
                    google_oauth_id: googleId,
                    first_name: firstName,
                    last_name: lastName,
                    username: email.split('@')[0],
                    profile_picture_url: picture,
                    // Generate a random password for Google users
                    password: (0, uuid_1.v4)(),
                });
            }
        }
        // Generate token
        const access_token = User_1.UserModel.generateToken(user);
        // Return successful response
        res.status(200).json({
            success: true,
            message: 'Google authentication successful',
            access_token,
            user: User_1.UserModel.toSafeObject(user),
        });
    }
    catch (error) {
        console.error('Error in Google callback controller:', error);
        res.status(500).json({
            error: 'Server error',
            message: 'Error authenticating with Google',
        });
    }
});
exports.googleCallback = googleCallback;
/**
 * Refresh an authentication token
 */
const refreshToken = (req, res) => __awaiter(void 0, void 0, void 0, function* () {
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
            decodedToken = jsonwebtoken_1.default.verify(token, process.env.JWT_SECRET || 'default_secret');
        }
        catch (error) {
            // If token is expired, try to extract info anyway
            if (error.name === 'TokenExpiredError') {
                decodedToken = jsonwebtoken_1.default.decode(token);
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
        const user = yield User_1.UserModel.findById(decodedToken.sub);
        if (!user) {
            res.status(401).json({
                error: 'Invalid token',
                message: 'User not found',
            });
            return;
        }
        // Generate a new token
        const access_token = User_1.UserModel.generateToken(user);
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
});
exports.refreshToken = refreshToken;
