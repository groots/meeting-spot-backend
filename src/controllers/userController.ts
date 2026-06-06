// User controllers (port of app/api/users.py). Minimal create/get by id.
import { Request, Response, NextFunction } from 'express';
import * as userService from '../services/userService.js';
import { BadRequest } from '../utils/errors.js';

/** POST / — create a user. */
export async function createUser(
  req: Request,
  res: Response,
  next: NextFunction
): Promise<void> {
  try {
    const data = req.body ?? {};
    if (!data.email || !data.password) {
      throw BadRequest('Missing required fields');
    }

    const existing = await userService.findByEmail(data.email);
    if (existing) {
      throw BadRequest('Email already registered');
    }

    const user = await userService.createUser({
      email: data.email,
      password: data.password,
      googleOauthId: data.google_oauth_id,
    });
    res.status(201).json(await userService.serializeUser(user));
  } catch (e) {
    next(e);
  }
}

/** GET /:id — fetch a user by id. */
export async function getUser(
  req: Request,
  res: Response,
  next: NextFunction
): Promise<void> {
  try {
    const user = await userService.findById(req.params.id);
    if (!user) {
      res.status(404).json({ error: 'User not found' });
      return;
    }
    res.status(200).json(await userService.serializeUser(user));
  } catch (e) {
    next(e);
  }
}
