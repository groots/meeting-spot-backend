import { Request, Response, NextFunction } from 'express';
import jwt from 'jsonwebtoken';
import * as userService from '../services/userService.js';
import { env } from '../config/env.js';

// Extended Express Request with user property
declare global {
  // eslint-disable-next-line @typescript-eslint/no-namespace
  namespace Express {
    interface Request {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      user?: any;
    }
  }
}

/**
 * Authentication middleware. Verifies the JWT and attaches the user (id/email)
 * to the request. Responds with 401 on any auth failure.
 */
export const authenticate = async (req: Request, res: Response, next: NextFunction): Promise<void> => {
  try {
    const authHeader = req.headers.authorization;

    if (!authHeader || !authHeader.startsWith('Bearer ')) {
      res.status(401).json({ error: 'Unauthorized', message: 'Missing or invalid token' });
      return;
    }

    const token = authHeader.replace('Bearer ', '');

    let decoded: jwt.JwtPayload;
    try {
      decoded = jwt.verify(token, env.jwtSecret) as jwt.JwtPayload;
    } catch (error) {
      const message =
        (error as Error).name === 'TokenExpiredError' ? 'Token has expired' : 'Invalid token';
      res.status(401).json({ error: 'Unauthorized', message });
      return;
    }

    const userId = decoded.sub as string | undefined;
    if (!userId) {
      res.status(401).json({ error: 'Unauthorized', message: 'Invalid token' });
      return;
    }

    const user = await userService.findById(userId);
    if (!user) {
      res.status(401).json({ error: 'Unauthorized', message: 'User not found' });
      return;
    }

    req.user = { id: user.id, email: user.email };
    next();
  } catch (error) {
    console.error('Auth middleware error:', error);
    res.status(500).json({ error: 'Server error', message: 'Authentication error' });
  }
};
