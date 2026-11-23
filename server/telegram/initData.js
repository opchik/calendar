import { createHmac, timingSafeEqual } from 'node:crypto';
import { config } from '../config.js';

/**
 * Проверка подписи initData из Telegram.WebApp.
 * https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app
 */
export function validateInitData(raw) {
  if (!raw) throw new Error('EMPTY');
  if (!config.botToken) throw new Error('NO_BOT_TOKEN');

  const params = new URLSearchParams(raw);
  const hash = params.get('hash');
  if (!hash) throw new Error('NO_HASH');

  const dataCheckString = [...params.entries()]
    .filter(([key]) => key !== 'hash' && key !== 'signature')
    .map(([key, value]) => `${key}=${value}`)
    .sort()
    .join('\n');

  const secretKey = createHmac('sha256', 'WebAppData').update(config.botToken).digest();
  const expected = createHmac('sha256', secretKey).update(dataCheckString).digest();

  const received = Buffer.from(hash, 'hex');
  if (received.length !== expected.length || !timingSafeEqual(received, expected)) {
    throw new Error('BAD_HASH');
  }

  const authDate = Number(params.get('auth_date'));
  if (!Number.isFinite(authDate)) throw new Error('NO_AUTH_DATE');
  if (Date.now() / 1000 - authDate > config.initDataMaxAgeSec) throw new Error('EXPIRED');

  const user = JSON.parse(params.get('user') || 'null');
  if (!user?.id) throw new Error('NO_USER');

  return { user, authDate };
}
