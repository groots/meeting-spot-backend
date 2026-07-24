// Auth controllers on Prisma. Response shapes match the Python backend:
// { message, access_token, user } for register/login, raw user dict for /me.
import { Request, Response, NextFunction } from 'express';
import path from 'path';
import axios from 'axios';
import { OAuth2Client, TokenPayload } from 'google-auth-library';
import jwt from 'jsonwebtoken';
import * as userService from '../services/userService.js';
import { createResetToken, consumeResetToken } from '../services/passwordResetService.js';
import {
  createVerificationToken,
  consumeVerificationToken,
} from '../services/emailVerificationService.js';
import {
  sendPasswordResetEmail,
  sendVerificationEmail,
} from '../services/emailService.js';
import { uploadProfilePicture, profilePicturesDir } from '../middleware/upload.js';
import { env } from '../config/env.js';
import { BadRequest, Conflict, NotFound, Unauthorized } from '../utils/errors.js';
import * as googleCalendarOAuthService from '../services/googleCalendarOAuthService.js';
import * as calendarConnectionService from '../services/calendarConnectionService.js';

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

    // Best-effort verification email (non-fatal: registration still succeeds).
    try {
      const verificationToken = await createVerificationToken(user.id);
      await sendVerificationEmail(user.email, verificationToken);
    } catch (e) {
      console.error('Failed to send verification email:', e);
    }

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
          emailVerified: true,
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

// Idle-refresh grace window: a token expired no more than this long ago can
// still be exchanged for a fresh one. Beyond this, the user must re-login.
const REFRESH_GRACE_SECONDS = 7 * 24 * 60 * 60; // 7 days

/** POST /refresh — re-issue a token from a valid OR recently-expired token. */
export async function refreshToken(req: Request, res: Response, next: NextFunction): Promise<void> {
  try {
    const authHeader = req.headers.authorization;
    const token = req.body?.token || (authHeader ? authHeader.replace('Bearer ', '') : null);
    if (!token) {
      throw BadRequest('Token is required');
    }

    // Always verify the HS256 signature. `ignoreExpiration` lets an expired (but
    // otherwise authentic) token through so we can apply our own grace window;
    // a forged/tampered token fails signature verification and is rejected.
    let decoded: jwt.JwtPayload;
    try {
      decoded = jwt.verify(token, env.jwtSecret, {
        ignoreExpiration: true,
      }) as jwt.JwtPayload;
    } catch {
      throw Unauthorized('Invalid token');
    }

    if (!decoded?.sub) {
      throw Unauthorized('Invalid token');
    }

    // Bound how long after expiry a token can still refresh. Tokens carry `exp`
    // (seconds since epoch); reject anything expired beyond the grace window.
    if (typeof decoded.exp === 'number') {
      const nowSeconds = Math.floor(Date.now() / 1000);
      if (nowSeconds - decoded.exp > REFRESH_GRACE_SECONDS) {
        throw Unauthorized('Invalid token');
      }
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

/** POST /reset-password/confirm — consume token, set new password. */
export async function resetPasswordConfirm(
  req: Request,
  res: Response,
  next: NextFunction
): Promise<void> {
  try {
    const { token, password } = req.body ?? {};
    if (!token || !password) {
      throw BadRequest('Token and password are required');
    }
    await consumeResetToken(token, password);
    res.status(200).json({ message: 'Password has been reset successfully' });
  } catch (e) {
    next(e);
  }
}

/** POST /verify-email — consume an email verification token. */
export async function verifyEmail(
  req: Request,
  res: Response,
  next: NextFunction
): Promise<void> {
  try {
    const token = req.body?.token;
    if (!token) {
      throw BadRequest('Token is required');
    }
    await consumeVerificationToken(token);
    res.status(200).json({ message: 'Email verified successfully' });
  } catch (e) {
    next(e);
  }
}

/** POST /resend-verification — generic 200 (no user enumeration). */
export async function resendVerification(
  req: Request,
  res: Response,
  next: NextFunction
): Promise<void> {
  try {
    const email = (req.body?.email ?? '').toLowerCase().trim();
    if (!email) {
      throw BadRequest('Email is required');
    }

    const successMessage =
      'If your email exists and is unverified, a new verification link has been sent.';

    const user = await userService.findByEmail(email);
    if (user && !user.emailVerified) {
      const token = await createVerificationToken(user.id);
      await sendVerificationEmail(user.email, token);
    }

    res.status(200).json({ message: successMessage });
  } catch (e) {
    next(e);
  }
}

interface FacebookDebugData {
  data?: { is_valid?: boolean; app_id?: string };
}

interface FacebookProfile {
  id: string;
  email?: string;
  first_name?: string;
  last_name?: string;
}

/** POST /facebook/callback (and /direct) — verify FB access token via Graph API. */
export async function facebookCallback(
  req: Request,
  res: Response,
  next: NextFunction
): Promise<void> {
  try {
    const accessToken = req.body?.access_token ?? req.body?.token;
    if (!accessToken) {
      throw BadRequest('No Facebook access token found');
    }

    if (!env.facebookAppId || !env.facebookAppSecret) {
      throw BadRequest('Facebook login is not configured');
    }

    // 1) Verify the user token is valid and issued for our app.
    const appToken = `${env.facebookAppId}|${env.facebookAppSecret}`;
    let debug: FacebookDebugData;
    try {
      const debugRes = await axios.get<FacebookDebugData>(
        'https://graph.facebook.com/debug_token',
        { params: { input_token: accessToken, access_token: appToken } }
      );
      debug = debugRes.data;
    } catch {
      throw BadRequest('Could not verify Facebook token');
    }

    if (!debug.data?.is_valid || debug.data.app_id !== env.facebookAppId) {
      throw BadRequest('Invalid Facebook token');
    }

    // 2) Fetch the profile.
    let profile: FacebookProfile;
    try {
      const profileRes = await axios.get<FacebookProfile>('https://graph.facebook.com/me', {
        params: {
          fields: 'id,email,first_name,last_name',
          access_token: accessToken,
        },
      });
      profile = profileRes.data;
    } catch {
      throw BadRequest('Could not fetch Facebook profile');
    }

    if (!profile.id) {
      throw BadRequest('Invalid Facebook profile');
    }

    const facebookId = profile.id;
    const email = profile.email?.toLowerCase();

    let user = await userService.findByFacebookId(facebookId);
    let created = false;

    if (!user) {
      if (email) {
        user = await userService.findByEmail(email);
      }
      if (user) {
        user = await userService.updateFacebookId(user.id, facebookId);
      } else {
        if (!email) {
          throw BadRequest('Facebook account has no email; cannot create account');
        }
        user = await userService.createUser({
          email,
          facebookOauthId: facebookId,
          firstName: profile.first_name,
          lastName: profile.last_name,
          emailVerified: true,
        });
        created = true;
      }
    }

    const access_token = userService.generateToken(user);
    res.status(created ? 201 : 200).json({
      message: 'Facebook authentication successful',
      access_token,
      user: await userService.serializeUser(user),
    });
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

/**
 * GET /google/calendar/connect — return the Google OAuth URL for free/busy.
 * Frontend navigates the browser to authorize_url.
 */
export async function googleCalendarConnect(
  req: Request,
  res: Response,
  next: NextFunction
): Promise<void> {
  try {
    const userId = req.user?.id;
    if (!userId) throw Unauthorized('Not authenticated');
    if (!env.googleClientId || !env.googleClientSecret) {
      throw BadRequest('Google Calendar connect is not configured');
    }

    res.status(200).json({
      authorize_url: googleCalendarOAuthService.buildAuthorizeUrl(userId),
    });
  } catch (e) {
    next(e);
  }
}

/**
 * GET /google/calendar/callback — Google redirects here with ?code=&state=.
 * Exchanges the code, stores the refresh token, then redirects to the profile.
 */
export async function googleCalendarCallback(
  req: Request,
  res: Response,
  next: NextFunction
): Promise<void> {
  try {
    const code = typeof req.query.code === 'string' ? req.query.code : '';
    const state = typeof req.query.state === 'string' ? req.query.state : '';
    const oauthError = typeof req.query.error === 'string' ? req.query.error : '';

    if (oauthError) {
      res.redirect(`${env.frontendUrl}/profile?calendar=denied`);
      return;
    }
    if (!code || !state) {
      res.redirect(`${env.frontendUrl}/profile?calendar=error`);
      return;
    }

    await googleCalendarOAuthService.handleOAuthCallback(code, state);
    res.redirect(`${env.frontendUrl}/profile?calendar=connected`);
  } catch (e) {
    console.error('Google Calendar OAuth callback failed:', e);
    res.redirect(`${env.frontendUrl}/profile?calendar=error`);
  }
}

/** GET /google/calendar — connection status for the current user. */
export async function googleCalendarStatus(
  req: Request,
  res: Response,
  next: NextFunction
): Promise<void> {
  try {
    const userId = req.user?.id;
    if (!userId) throw Unauthorized('Not authenticated');
    const connection = await calendarConnectionService.findActive(userId);
    res.status(200).json(calendarConnectionService.toPublicStatus(connection));
  } catch (e) {
    next(e);
  }
}

/** DELETE /google/calendar — disconnect and invalidate stored refresh token. */
export async function googleCalendarDisconnect(
  req: Request,
  res: Response,
  next: NextFunction
): Promise<void> {
  try {
    const userId = req.user?.id;
    if (!userId) throw Unauthorized('Not authenticated');
    const removed = await calendarConnectionService.revoke(userId);
    res.status(200).json({ disconnected: removed });
  } catch (e) {
    next(e);
  }
}
