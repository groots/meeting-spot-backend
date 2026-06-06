// Auth controllers on Prisma. Response shapes match the Python backend:
// { message, access_token, user } for register/login, raw user dict for /me.
import { Request, Response, NextFunction } from 'express';
import path from 'path';
import { OAuth2Client, TokenPayload } from 'google-auth-library';
import jwt from 'jsonwebtoken';
import * as userService from '../services/userService.js';
import { createResetToken } from '../services/passwordResetService.js';
import { sendPasswordResetEmail } from '../services/emailService.js';
import { uploadProfilePicture, profilePicturesDir } from '../middleware/upload.js';
import { env } from '../config/env.js';
import { BadRequest, Conflict, NotFound, Unauthorized } from '../utils/errors.js';

const googleClient = new OAuth2Client(env.googleClientId);

/** POST /register */
export async function register(req: Request, res: Response, next: NextFunction): Promise<void> {
  try {
    const { email, password, first_name, last_name, username, phone } = req.body ?? {};

    if (!email || !password) {
      throw BadRequest('Email and password are required');
    }

    const existing = await userService.findByEmail(email);
    if (existing) {
      throw Conflict('User already exists');
    }

    const user = await userService.createUser({
      email,
      password,
      firstName: first_name,
      lastName: last_name,
      username,
      phone,
    });

    const access_token = userService.generateToken(user);
    res.status(201).json({
      message: 'User created successfully',
      user: await userService.serializeUser(user),
      access_token,
    });
  } catch (e) {
    next(e);
  }
}

/** POST /login */
export async function login(req: Request, res: Response, next: NextFunction): Promise<void> {
  try {
    const { email, password } = req.body ?? {};

    if (!email || !password) {
      throw BadRequest('Email and password are required');
    }

    const user = await userService.findByEmail(email);
    if (!user || !user.passwordHash) {
      throw Unauthorized('Invalid email or password');
    }

    const valid = await userService.verifyPassword(password, user.passwordHash);
    if (!valid) {
      throw Unauthorized('Invalid email or password');
    }

    const access_token = userService.generateToken(user);
    res.status(200).json({
      message: 'Login successful',
      access_token,
      user: await userService.serializeUser(user),
    });
  } catch (e) {
    next(e);
  }
}

/** GET /me */
export async function getCurrentUser(req: Request, res: Response, next: NextFunction): Promise<void> {
  try {
    const userId = req.user?.id;
    if (!userId) throw Unauthorized('Not authenticated');

    const user = await userService.findById(userId);
    if (!user) throw NotFound('User not found');

    res.status(200).json(await userService.serializeUser(user));
  } catch (e) {
    next(e);
  }
}

/** POST /google/callback (and /google/callback/direct) */
export async function googleCallback(req: Request, res: Response, next: NextFunction): Promise<void> {
  try {
    const credential = req.body?.credential ?? req.body?.token;
    if (!credential) {
      throw BadRequest('No Google credential found');
    }

    // Verify the Google ID token (improvement over the Python non-verifying decode).
    let payload: TokenPayload | undefined;
    try {
      const ticket = await googleClient.verifyIdToken({
        idToken: credential,
        audience: env.googleClientId || undefined,
      });
      payload = ticket.getPayload();
    } catch {
      throw BadRequest('Invalid Google token');
    }

    if (!payload || !payload.sub || !payload.email) {
      throw BadRequest('Invalid Google token');
    }

    const googleId = payload.sub;
    const email = payload.email.toLowerCase();

    let user = await userService.findByGoogleId(googleId);
    let created = false;

    if (!user) {
      user = await userService.findByEmail(email);
      if (user) {
        user = await userService.updateGoogleId(user.id, googleId);
      } else {
        user = await userService.createUser({
          email,
          googleOauthId: googleId,
          firstName: payload.given_name,
          lastName: payload.family_name,
          profilePictureUrl: payload.picture,
        });
        created = true;
      }
    }

    const access_token = userService.generateToken(user);
    res.status(created ? 201 : 200).json({
      message: 'Google authentication successful',
      access_token,
      user: await userService.serializeUser(user),
    });
  } catch (e) {
    next(e);
  }
}

/** POST /refresh — re-issue a token from a valid/expired-but-decodable token. */
export async function refreshToken(req: Request, res: Response, next: NextFunction): Promise<void> {
  try {
    const authHeader = req.headers.authorization;
    const token = req.body?.token || (authHeader ? authHeader.replace('Bearer ', '') : null);
    if (!token) {
      throw BadRequest('Token is required');
    }

    let decoded: jwt.JwtPayload | null = null;
    try {
      decoded = jwt.verify(token, env.jwtSecret) as jwt.JwtPayload;
    } catch (err) {
      if ((err as Error).name === 'TokenExpiredError') {
        decoded = jwt.decode(token) as jwt.JwtPayload | null;
      } else {
        throw Unauthorized('Invalid token');
      }
    }

    if (!decoded?.sub) {
      throw Unauthorized('Invalid token');
    }

    const user = await userService.findById(decoded.sub as string);
    if (!user) {
      throw Unauthorized('User not found');
    }

    const access_token = userService.generateToken(user);
    res.status(200).json({ message: 'Token refreshed', access_token });
  } catch (e) {
    next(e);
  }
}

/** POST /reset-password — always generic 200 (no user enumeration). */
export async function resetPassword(req: Request, res: Response, next: NextFunction): Promise<void> {
  try {
    const email = (req.body?.email ?? '').toLowerCase().trim();
    if (!email) {
      throw BadRequest('Email is required');
    }

    const successMessage =
      'If your email exists in our system, you will receive password reset instructions.';

    const user = await userService.findByEmail(email);
    if (user) {
      const token = await createResetToken(user.id);
      await sendPasswordResetEmail(email, token);
    }

    res.status(200).json({ message: successMessage });
  } catch (e) {
    next(e);
  }
}

/** POST /me/picture — multer single 'file', persists profile_picture_url. */
export function uploadPicture(req: Request, res: Response, next: NextFunction): void {
  uploadProfilePicture(req, res, async (err: unknown) => {
    try {
      if (err) {
        throw BadRequest((err as Error).message || 'File upload failed');
      }
      const userId = req.user?.id;
      if (!userId) throw Unauthorized('Not authenticated');

      const file = req.file;
      if (!file) {
        throw BadRequest('No file part');
      }

      const url = `${req.protocol}://${req.get('host')}/api/v1/auth/profile/picture/${file.filename}`;
      await userService.updateProfilePicture(userId, url);

      res.status(201).json({
        message: 'Profile picture uploaded successfully',
        filename: file.filename,
        profile_picture_url: url,
      });
    } catch (e) {
      next(e);
    }
  });
}

/** GET /profile/picture/:filename — reject traversal, send file. */
export function getProfilePicture(req: Request, res: Response, next: NextFunction): void {
  try {
    const { filename } = req.params;
    if (!filename || filename.includes('..') || filename.includes('/')) {
      throw BadRequest('Invalid filename');
    }
    res.sendFile(path.join(profilePicturesDir, filename));
  } catch (e) {
    next(e);
  }
}
