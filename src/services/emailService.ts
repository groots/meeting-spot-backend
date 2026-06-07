// Email delivery via Mailgun. Ported from app/utils/notifications.py.
// Returns true on success; logs and returns false on misconfig/failure so
// callers can keep a generic response (e.g. password reset).
import axios from 'axios';
import { env } from '../config/env.js';

export async function sendEmail(toEmail: string, subject: string, body: string): Promise<boolean> {
  try {
    const apiKey = env.mailgunApiKey;
    const domain = env.mailgunDomain;

    if (!apiKey || !domain) {
      console.error('Missing Mailgun configuration (MAILGUN_API_KEY / MAILGUN_DOMAIN). Email not sent.');
      return false;
    }

    const url = `https://api.mailgun.net/v3/${domain}/messages`;
    const form = new URLSearchParams({
      from: `Find A Meeting Spot <noreply@${domain}>`,
      to: toEmail,
      subject,
      text: body,
      html: body.replace(/\n/g, '<br>'),
    });

    const response = await axios.post(url, form.toString(), {
      auth: { username: 'api', password: apiKey },
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      validateStatus: () => true,
    });

    if (response.status !== 200) {
      console.error(`Mailgun API error (${response.status}):`, response.data);
      return false;
    }
    return true;
  } catch (e) {
    console.error('Error sending email:', e);
    return false;
  }
}

export async function sendPasswordResetEmail(email: string, token: string): Promise<boolean> {
  const resetUrl = `${env.frontendUrl}/auth/reset-password/${token}`;
  const subject = 'Reset Your Find A Meeting Spot Password';
  const body = `Hello,

You've requested to reset your password for Find A Meeting Spot.

Please click the link below to reset your password:
${resetUrl}

This link will expire in 1 hour.

If you didn't request this password reset, please ignore this email or contact support if you have concerns.

Thanks,
The Find A Meeting Spot Team
`;
  return sendEmail(email, subject, body);
}

export async function sendVerificationEmail(email: string, token: string): Promise<boolean> {
  const verifyUrl = `${env.frontendUrl}/auth/verify-email/${token}`;
  const subject = 'Verify your Find A Meeting Spot email';
  const body = `Hello,

Thanks for signing up for Find A Meeting Spot.

Please confirm your email address by clicking the link below:
${verifyUrl}

This link will expire in 24 hours.

If you didn't create this account, you can safely ignore this email.

Thanks,
The Find A Meeting Spot Team
`;
  return sendEmail(email, subject, body);
}

export async function sendMeetingInviteEmail(email: string, requestId: string, token: string): Promise<boolean> {
  const inviteUrl = `${env.frontendUrl}/request/${requestId}?token=${token}`;
  const subject = "You've been invited to find a meeting spot";
  const body = `Hello,

Someone would like to find a convenient place to meet with you.

Please click the link below to share your location so we can suggest meeting spots halfway between you:
${inviteUrl}

This invitation will expire in 24 hours.

Thanks,
The Find A Meeting Spot Team
`;
  return sendEmail(email, subject, body);
}
