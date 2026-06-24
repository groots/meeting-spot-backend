// SMS delivery via the Twilio REST API (using axios, already a dependency).
// When credentials are absent we log and succeed (stub) so local/dev flows work
// without provisioning Twilio. Returns true when the message was accepted (or
// stubbed), false on a delivery failure.
import axios from 'axios';
import { env } from '../config/env.js';

export async function sendSms(toNumber: string, message: string): Promise<boolean> {
  // Twilio credentials are optional; when absent we log and succeed (stub).
  if (!env.twilioAccountSid || !env.twilioAuthToken || !env.twilioFromNumber) {
    console.info(`[sms stub] would send to ${toNumber}: ${message}`);
    return true;
  }

  const url = `https://api.twilio.com/2010-04-01/Accounts/${env.twilioAccountSid}/Messages.json`;
  const body = new URLSearchParams({
    To: toNumber,
    From: env.twilioFromNumber,
    Body: message,
  });

  try {
    await axios.post(url, body.toString(), {
      auth: { username: env.twilioAccountSid, password: env.twilioAuthToken },
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      timeout: 10000,
    });
    return true;
  } catch (e) {
    // Never echo the destination number or message into error logs.
    const status = axios.isAxiosError(e) ? e.response?.status : undefined;
    console.error(`Failed to send SMS via Twilio${status ? ` (status ${status})` : ''}`);
    return false;
  }
}
