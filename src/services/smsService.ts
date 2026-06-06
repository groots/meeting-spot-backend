// SMS delivery. Twilio is not wired up yet (parity with the Python reference,
// which logs in development and stubs production). Returns true to indicate the
// caller should proceed as if delivery succeeded.
import { env } from '../config/env.js';

export async function sendSms(toNumber: string, message: string): Promise<boolean> {
  // Twilio credentials are optional; when absent we log and succeed (stub).
  if (!env.twilioAccountSid || !env.twilioAuthToken) {
    console.info(`[sms stub] would send to ${toNumber}: ${message}`);
    return true;
  }
  // TODO: integrate Twilio REST API when credentials are provisioned.
  console.info(`[sms stub] (credentials present) would send to ${toNumber}: ${message}`);
  return true;
}
