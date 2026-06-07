// User persistence + auth helpers on Prisma. Replaces the raw-pg UserModel.
// Public response shape (toSafeObject/serialize) matches the Python
// User.to_dict: snake_case fields + is_premium + full_name.
import bcrypt from 'bcryptjs';
import jwt from 'jsonwebtoken';
import { User } from '@prisma/client';
import { prisma } from '../config/prisma.js';
import { env } from '../config/env.js';
import { isPremium } from './subscriptionService.js';

export interface CreateUserInput {
  email: string;
  password?: string;
  passwordHash?: string;
  username?: string;
  firstName?: string;
  lastName?: string;
  phone?: string;
  googleOauthId?: string;
  facebookOauthId?: string;
  profilePictureUrl?: string;
  emailVerified?: boolean;
}

export interface SafeUser {
  id: string;
  email: string;
  created_at: string;
  updated_at: string;
  is_premium: boolean;
  email_verified: boolean;
  is_oauth_user: boolean;
  username?: string;
  first_name?: string;
  last_name?: string;
  phone?: string;
  profile_picture_url?: string;
  full_name?: string;
}

async function hashPassword(password: string): Promise<string> {
  const salt = await bcrypt.genSalt(10);
  return bcrypt.hash(password, salt);
}

export async function createUser(input: CreateUserInput): Promise<User> {
  const email = input.email.toLowerCase();

  let passwordHash = input.passwordHash;
  if (!passwordHash && input.password) {
    passwordHash = await hashPassword(input.password);
  }

  const now = new Date();
  return prisma.user.create({
    data: {
      email,
      passwordHash: passwordHash ?? null,
      username: input.username ?? email.split('@')[0],
      firstName: input.firstName ?? null,
      lastName: input.lastName ?? null,
      phone: input.phone ?? null,
      googleOauthId: input.googleOauthId ?? null,
      facebookOauthId: input.facebookOauthId ?? null,
      profilePictureUrl: input.profilePictureUrl ?? null,
      emailVerified: input.emailVerified ?? false,
      createdAt: now,
      updatedAt: now,
    },
  });
}

export function findByEmail(email: string): Promise<User | null> {
  return prisma.user.findUnique({ where: { email: email.toLowerCase() } });
}

export function findById(id: string): Promise<User | null> {
  return prisma.user.findUnique({ where: { id } });
}

export function findByGoogleId(googleId: string): Promise<User | null> {
  return prisma.user.findUnique({ where: { googleOauthId: googleId } });
}

export function updateGoogleId(userId: string, googleId: string): Promise<User> {
  return prisma.user.update({ where: { id: userId }, data: { googleOauthId: googleId } });
}

export function findByFacebookId(facebookId: string): Promise<User | null> {
  return prisma.user.findFirst({ where: { facebookOauthId: facebookId } });
}

export function updateFacebookId(userId: string, facebookId: string): Promise<User> {
  return prisma.user.update({ where: { id: userId }, data: { facebookOauthId: facebookId } });
}

export function updateProfilePicture(userId: string, url: string): Promise<User> {
  return prisma.user.update({ where: { id: userId }, data: { profilePictureUrl: url } });
}

export async function updatePassword(userId: string, newPassword: string): Promise<User> {
  const passwordHash = await hashPassword(newPassword);
  return prisma.user.update({ where: { id: userId }, data: { passwordHash } });
}

export function markEmailVerified(userId: string): Promise<User> {
  return prisma.user.update({ where: { id: userId }, data: { emailVerified: true } });
}

export function verifyPassword(password: string, hash: string): Promise<boolean> {
  return bcrypt.compare(password, hash);
}

export function generateToken(user: Pick<User, 'id' | 'email'>): string {
  const secret = Buffer.from(env.jwtSecret);
  return jwt.sign({ sub: user.id, email: user.email }, secret, {
    expiresIn: '24h',
    algorithm: 'HS256',
  });
}

/** Synchronous serializer given a precomputed premium flag. */
export function toSafeObject(user: User, premium = false): SafeUser {
  const safe: SafeUser = {
    id: user.id,
    email: user.email,
    created_at: user.createdAt.toISOString(),
    updated_at: user.updatedAt.toISOString(),
    is_premium: premium,
    email_verified: user.emailVerified,
    is_oauth_user: Boolean(user.googleOauthId || user.facebookOauthId),
  };
  if (user.username) safe.username = user.username;
  if (user.firstName) safe.first_name = user.firstName;
  if (user.lastName) safe.last_name = user.lastName;
  if (user.phone) safe.phone = user.phone;
  if (user.profilePictureUrl) safe.profile_picture_url = user.profilePictureUrl;

  if (user.firstName && user.lastName) {
    safe.full_name = `${user.firstName} ${user.lastName}`;
  } else if (user.firstName) {
    safe.full_name = user.firstName;
  } else if (user.lastName) {
    safe.full_name = user.lastName;
  }
  return safe;
}

/** Async serializer that computes is_premium from subscriptions. */
export async function serializeUser(user: User): Promise<SafeUser> {
  const premium = await isPremium(user.id);
  return toSafeObject(user, premium);
}
