// Google Calendar OAuth (code flow) for free/busy scope.
// Separate from Sign-In with Google (ID token) used at login.
import { OAuth2Client } from 'google-auth-library';
import jwt from 'jsonwebtoken';
import axios from 'axios';
import { env } from '../config/env.js';
import * as calendarConnectionService from './calendarConnectionService.js';

export const CALENDAR_FREEBUSY_SCOPE = 'https://www.googleapis.com/auth/calendar.freebusy';
const OPENID_EMAIL_SCOPES = ['openid', 'email'];

function oauthClient(): OAuth2Client {
  return new OAuth2Client(
    env.googleClientId,
    env.googleClientSecret,
    env.googleCalendarRedirectUri
  );
}

/** Short-lived signed state so the callback knows which user connected. */
export function createConnectState(userId: string): string {
  return jwt.sign(
    { sub: userId, purpose: 'google_calendar_connect' },
    Buffer.from(env.jwtSecret),
    { expiresIn: '10m', algorithm: 'HS256' }
  );
}

export function parseConnectState(state: string): string {
  const payload = jwt.verify(state, Buffer.from(env.jwtSecret), {
    algorithms: ['HS256'],
  }) as { sub?: string; purpose?: string };
  if (payload.purpose !== 'google_calendar_connect' || !payload.sub) {
    throw new Error('Invalid calendar connect state');
  }
  return payload.sub;
}

export function buildAuthorizeUrl(userId: string): string {
  const client = oauthClient();
  return client.generateAuthUrl({
    access_type: 'offline',
    prompt: 'consent',
    scope: [...OPENID_EMAIL_SCOPES, CALENDAR_FREEBUSY_SCOPE],
    state: createConnectState(userId),
    include_granted_scopes: true,
  });
}

export async function handleOAuthCallback(code: string, state: string): Promise<string> {
  const userId = parseConnectState(state);
  const client = oauthClient();
  const { tokens } = await client.getToken(code);
  if (!tokens.refresh_token) {
    throw new Error(
      'Google did not return a refresh token. Disconnect the app in Google Account permissions and try again.'
    );
  }

  client.setCredentials(tokens);
  let accountEmail = '';
  if (tokens.id_token) {
    const ticket = await client.verifyIdToken({
      idToken: tokens.id_token,
      audience: env.googleClientId || undefined,
    });
    accountEmail = ticket.getPayload()?.email ?? '';
  }
  if (!accountEmail && tokens.access_token) {
    // Fallback: userinfo endpoint
    const info = await axios.get('https://www.googleapis.com/oauth2/v2/userinfo', {
      headers: { Authorization: `Bearer ${tokens.access_token}` },
      timeout: 8000,
    });
    accountEmail = typeof info.data?.email === 'string' ? info.data.email : '';
  }
  if (!accountEmail) {
    throw new Error('Could not determine Google account email');
  }

  const scopes =
    typeof tokens.scope === 'string' && tokens.scope
      ? tokens.scope
      : CALENDAR_FREEBUSY_SCOPE;

  await calendarConnectionService.upsertGoogleConnection({
    userId,
    accountEmail,
    refreshToken: tokens.refresh_token,
    scopes,
  });

  return userId;
}
