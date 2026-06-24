// Email delivery via Mailgun. Ported from app/utils/notifications.py.
// Returns true on success; logs and returns false on misconfig/failure so
// callers can keep a generic response (e.g. password reset).
import axios from 'axios';
import { env } from '../config/env.js';

const BRAND = 'Find A Meeting Spot';

function escapeHtml(s: string): string {
  return s
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

/**
 * Minimal, well-structured HTML email. A clean layout with a real CTA button
 * (rather than a single bare link) reads as legitimate to spam filters, while
 * the plain-text part is always sent alongside it for multipart delivery.
 */
function renderHtml(opts: {
  heading: string;
  intro: string;
  ctaLabel: string;
  ctaUrl: string;
  note?: string;
}): string {
  const { heading, intro, ctaLabel, ctaUrl, note } = opts;
  return `<!doctype html>
<html lang="en">
  <body style="margin:0;padding:0;background:#f4f5f7;font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f4f5f7;padding:24px 0;">
      <tr>
        <td align="center">
          <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:480px;background:#ffffff;border-radius:12px;overflow:hidden;border:1px solid #e6e8eb;">
            <tr>
              <td style="padding:24px 32px 8px;font-size:18px;font-weight:600;color:#111827;">${escapeHtml(BRAND)}</td>
            </tr>
            <tr>
              <td style="padding:8px 32px 0;font-size:20px;font-weight:600;color:#111827;">${escapeHtml(heading)}</td>
            </tr>
            <tr>
              <td style="padding:12px 32px 0;font-size:15px;line-height:1.6;color:#374151;">${escapeHtml(intro)}</td>
            </tr>
            <tr>
              <td style="padding:24px 32px;">
                <a href="${ctaUrl}" style="display:inline-block;background:#2563eb;color:#ffffff;text-decoration:none;font-size:15px;font-weight:600;padding:12px 22px;border-radius:8px;">${escapeHtml(ctaLabel)}</a>
              </td>
            </tr>
            <tr>
              <td style="padding:0 32px 8px;font-size:13px;line-height:1.6;color:#6b7280;">If the button doesn't work, copy and paste this link into your browser:<br><span style="color:#2563eb;word-break:break-all;">${escapeHtml(ctaUrl)}</span></td>
            </tr>
            ${note ? `<tr><td style="padding:8px 32px 0;font-size:13px;line-height:1.6;color:#6b7280;">${escapeHtml(note)}</td></tr>` : ''}
            <tr>
              <td style="padding:24px 32px;border-top:1px solid #e6e8eb;margin-top:16px;font-size:12px;color:#9ca3af;">Thanks,<br>The ${escapeHtml(BRAND)} Team</td>
            </tr>
          </table>
        </td>
      </tr>
    </table>
  </body>
</html>`;
}

export async function sendEmail(
  toEmail: string,
  subject: string,
  text: string,
  html?: string
): Promise<boolean> {
  try {
    const apiKey = env.mailgunApiKey;
    const domain = env.mailgunDomain;

    if (!apiKey || !domain) {
      console.error('Missing Mailgun configuration (MAILGUN_API_KEY / MAILGUN_DOMAIN). Email not sent.');
      return false;
    }

    const from = env.mailFrom || `${BRAND} <noreply@${domain}>`;

    const url = `https://api.mailgun.net/v3/${domain}/messages`;
    const form = new URLSearchParams({
      from,
      to: toEmail,
      subject,
      text,
      html: html ?? text.replace(/\n/g, '<br>'),
      // Show the real destination URL instead of a Mailgun tracking redirect.
      // Without a configured tracking CNAME, rewritten links hurt deliverability
      // and look like phishing to recipients.
      'o:tracking-clicks': 'no',
    });
    if (env.mailReplyTo) {
      form.append('h:Reply-To', env.mailReplyTo);
    }

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
  const subject = 'Reset your Find A Meeting Spot password';
  const text = `Hello,

You've requested to reset your password for Find A Meeting Spot.

Reset your password using this link:
${resetUrl}

This link will expire in 1 hour.

If you didn't request this password reset, please ignore this email or contact support if you have concerns.

Thanks,
The Find A Meeting Spot Team
`;
  const html = renderHtml({
    heading: 'Reset your password',
    intro: "You've requested to reset your password for Find A Meeting Spot. Click the button below to choose a new one.",
    ctaLabel: 'Reset password',
    ctaUrl: resetUrl,
    note: "This link will expire in 1 hour. If you didn't request this, you can safely ignore this email.",
  });
  return sendEmail(email, subject, text, html);
}

export async function sendVerificationEmail(email: string, token: string): Promise<boolean> {
  const verifyUrl = `${env.frontendUrl}/auth/verify-email/${token}`;
  const subject = 'Verify your Find A Meeting Spot email';
  const text = `Hello,

Thanks for signing up for Find A Meeting Spot.

Confirm your email address using this link:
${verifyUrl}

This link will expire in 24 hours.

If you didn't create this account, you can safely ignore this email.

Thanks,
The Find A Meeting Spot Team
`;
  const html = renderHtml({
    heading: 'Confirm your email',
    intro: 'Thanks for signing up for Find A Meeting Spot. Please confirm your email address to finish setting up your account.',
    ctaLabel: 'Verify email',
    ctaUrl: verifyUrl,
    note: "This link will expire in 24 hours. If you didn't create this account, you can safely ignore this email.",
  });
  return sendEmail(email, subject, text, html);
}

export async function sendMeetingInviteEmail(email: string, requestId: string, token: string): Promise<boolean> {
  const inviteUrl = `${env.frontendUrl}/request/${requestId}?token=${token}`;
  const subject = "You've been invited to find a meeting spot";
  const text = `Hello,

Someone would like to find a convenient place to meet with you.

Enter your address using this link and we'll suggest meeting spots halfway between you. Your address stays private — it's only used to calculate the midpoint and is never shared with the other person:
${inviteUrl}

This invitation will expire in 24 hours.

Thanks,
The Find A Meeting Spot Team
`;
  const html = renderHtml({
    heading: 'Find a place to meet',
    intro: "Someone would like to find a convenient place to meet with you. Enter your address and we'll suggest spots halfway between you. Your address stays private — it's only used to calculate the midpoint and is never shared with the other person.",
    ctaLabel: 'Enter my address',
    ctaUrl: inviteUrl,
    note: 'This invitation will expire in 24 hours.',
  });
  return sendEmail(email, subject, text, html);
}

/**
 * Email a finalized meeting (venue + time) with an "add to calendar" link.
 *
 * PRIVACY: `venueName`/`location` are the public venue only; `whenText` is a
 * human-readable time. No home address or coordinates are ever included.
 */
export async function sendMeetingScheduledEmail(
  email: string,
  venueName: string,
  location: string,
  whenText: string,
  calendarUrl: string
): Promise<boolean> {
  const subject = `Your meeting at ${venueName} is scheduled`;
  const text = `Hello,

Your meeting is set.

Where: ${venueName}${location ? ` (${location})` : ''}
When: ${whenText}

Add it to your calendar:
${calendarUrl}

Thanks,
The Find A Meeting Spot Team
`;
  const html = renderHtml({
    heading: 'Your meeting is scheduled',
    intro: `Your meeting is set for ${whenText} at ${venueName}${location ? ` (${location})` : ''}. Add it to your calendar with one click.`,
    ctaLabel: 'Add to calendar',
    ctaUrl: calendarUrl,
    note: 'See you there!',
  });
  return sendEmail(email, subject, text, html);
}
