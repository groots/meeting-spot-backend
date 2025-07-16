import { Request, Response, NextFunction } from 'express';
import jwt from 'jsonwebtoken';
import { UserModel } from '../models/User.js';

// Extended Express Request with user property
declare global {
  namespace Express {
    interface Request {
      user?: any;
    }
  }
}

/**
 * Authentication middleware
 * Verifies JWT token and attaches user to request
 */
export const authenticate = async (
  req: Request,
  res: Response,
  next: NextFunction
): Promise<void> => {
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
      const decoded = jwt.verify(
        token,
        process.env.JWT_SECRET || 'default_secret'
      ) as jwt.JwtPayload;

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
      const user = await UserModel.findById(userId as string);

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
    } catch (error) {
      if ((error as Error).name === 'TokenExpiredError') {
        res.status(401).json({
          error: 'Unauthorized',
          message: 'Token has expired',
        });
      } else {
        res.status(401).json({
          error: 'Unauthorized',
          message: 'Invalid token',
        });
      }
    }
  } catch (error) {
    console.error('Auth middleware error:', error);
    res.status(500).json({
      error: 'Server error',
      message: 'Authentication error',
    });
  }
};
