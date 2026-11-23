import { createHmac, timingSafeEqual } from 'node:crypto';
import { config } from './config.js';

const b64url = (input) =>
  Buffer.from(input).toString('base64').replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');

const sign = (payload) => createHmac('sha256', config.sessionSecret).update(payload).digest('base64url');

/** Cookie вида "<payload>.<sig>" — состояние сессии в cookie, без таблицы сессий. */
export function createSession(telegramId) {
  const payload = b64url(
    JSON.stringify({ uid: telegramId, exp: Math.floor(Date.now() / 1000) + config.sessionTtlSec })
  );
  return `${payload}.${sign(payload)}`;
}

export function readSession(cookieHeader = '') {
  const match = (cookieHeader || '').match(/(?:^|;\s*)sid=([^;]+)/);
  if (!match) return null;

  const [payload, signature] = match[1].split('.');
  if (!payload || !signature) return null;

  const expected = Buffer.from(sign(payload));
  const received = Buffer.from(signature);
  if (expected.length !== received.length || !timingSafeEqual(expected, received)) return null;

  try {
    const data = JSON.parse(Buffer.from(payload, 'base64url').toString());
    return data.exp > Date.now() / 1000 ? data : null;
  } catch {
    return null;
  }
}

export function sessionCookie(session) {
  const maxAge = config.sessionTtlSec;
  const secure = config.publicUrl.startsWith('https') ? '; Secure' : '';
  return `sid=${session}; HttpOnly; Path=/; SameSite=Lax; Max-Age=${maxAge}${secure}`;
}
