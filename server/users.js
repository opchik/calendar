import { db } from './db.js';

export function upsertUser(user) {
  const now = Math.floor(Date.now() / 1000);
  db.prepare(
    `INSERT INTO users (telegram_id, first_name, last_name, username, language, created_at, seen_at)
     VALUES (?, ?, ?, ?, ?, ?, ?)
     ON CONFLICT (telegram_id) DO UPDATE SET
       first_name = excluded.first_name,
       last_name  = excluded.last_name,
       username   = excluded.username,
       language   = excluded.language,
       seen_at    = excluded.seen_at`
  ).run(
    user.id,
    user.first_name ?? null,
    user.last_name ?? null,
    user.username ?? null,
    user.language_code ?? null,
    now,
    now
  );
  return getUser(user.id);
}

export const getUser = (id) => db.prepare('SELECT * FROM users WHERE telegram_id = ?').get(id);

export const publicUser = (user) => ({
  id: user.telegram_id,
  firstName: user.first_name,
  lastName: user.last_name,
  username: user.username,
});
