import { config } from './config.js';
import { readSession } from './session.js';
import { HttpError } from './tasks.js';
import { getUser, upsertUser } from './users.js';

const DEV_USER = { id: 1, first_name: 'Разработчик', username: 'dev' };

/** Разработка без Telegram: только вне HTTPS, чтобы не сломать прод. */
export const isDevMode = () => config.devBypass && !config.publicUrl.startsWith('https://');

export function touchDevUser() {
  return isDevMode() ? upsertUser(DEV_USER) : null;
}

/** Сессия по cookie; в dev-режиме — автоматически пользователь-разработчик. */
export function userFromRequest(req) {
  const session = readSession(req.headers.cookie);
  const user = session ? getUser(session.uid) : null;
  return user || touchDevUser();
}

export function requireUser(req) {
  const user = userFromRequest(req);
  if (!user) throw new HttpError(401, 'Не авторизован');
  return user;
}

export function json(res, status, body) {
  res.writeHead(status, { 'Content-Type': 'application/json; charset=utf-8' });
  res.end(JSON.stringify(body));
}
