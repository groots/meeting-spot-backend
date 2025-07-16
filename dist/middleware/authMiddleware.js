import jwt from 'jsonwebtoken';
import { UserModel } from '../models/User.js';
/**
 * Authentication middleware
 * Verifies JWT token and attaches user to request
 */
export const authenticate = async (req, res, next) => {
    try {
        // Get token from headers
        const authHeader = req.headers.authorization;
        if (!authHeader || !authHeader.startsWith('Bearer ')) {
            res.status(401).json({
                error: 'Unauthorized',
                message: 'Missing or invalid token',
            });
            return;
        }
        // Extract token
        const token = authHeader.replace('Bearer ', '');
        try {
            // Verify token
            const decoded = jwt.verify(token, process.env.JWT_SECRET || 'default_secret');
            // Get user ID
            const userId = decoded.sub;
            if (!userId) {
                res.status(401).json({
                    error: 'Unauthorized',
                    message: 'Invalid token',
                });
                return;
            }
            // Get user from database
            const user = await UserModel.findById(userId);
            if (!user) {
                res.status(401).json({
                    error: 'Unauthorized',
                    message: 'User not found',
                });
                return;
            }
            // Attach user to request
            req.user = UserModel.toSafeObject(user);
            // Proceed to the next middleware/route handler
            next();
        }
        catch (error) {
            if (error.name === 'TokenExpiredError') {
                res.status(401).json({
                    error: 'Unauthorized',
                    message: 'Token has expired',
                });
            }
            else {
                res.status(401).json({
                    error: 'Unauthorized',
                    message: 'Invalid token',
                });
            }
        }
    }
    catch (error) {
        console.error('Auth middleware error:', error);
        res.status(500).json({
            error: 'Server error',
            message: 'Authentication error',
        });
    }
};
