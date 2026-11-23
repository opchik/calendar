import { json } from '../http.js';
import { createSession, sessionCookie } from '../session.js';
import { validateInitData } from '../telegram/initData.js';
import { upsertUser } from '../users.js';

const AUTH_ERRORS = {
  NO_BOT_TOKEN: 'Сервер не настроен: не задан BOT_TOKEN',
  EXPIRED: 'Данные входа устарели, переоткройте приложение',
};

/** POST /api/auth — обменивает Telegram initData на HttpOnly cookie-сессию. */
export function handleAuth(req, res, body) {
  let data;
  try {
    data = validateInitData(body.initData);
  } catch (error) {
    return json(res, 401, { error: AUTH_ERRORS[error.message] || 'Подпись Telegram неверна' });
  }

  const user = upsertUser(data.user);
  res.setHeader('Set-Cookie', sessionCookie(createSession(user.telegram_id)));
  json(res, 200, { ok: true });
}

/** POST /api/logout — удаляет cookie-сессию. */
export function handleLogout(req, res) {
  res.setHeader('Set-Cookie', 'sid=; HttpOnly; Path=/; SameSite=Lax; Max-Age=0');
  json(res, 200, { ok: true });
}
