import { db } from '../db.js';
import { config } from '../config.js';

/** Импорт задач из файла: каждая непустая строка — задача. */
export function importTasks(userId, text) {
  const lines = String(text)
    .split(/\r?\n/)
    .map((line) => line.replace(/^[-*•\d.)\s]+/, '').trim())
    .filter(Boolean)
    .slice(0, 500);

  const now = Math.floor(Date.now() / 1000);
  const insert = db.prepare(
    'INSERT INTO tasks (user_id, title, created_at, updated_at) VALUES (?, ?, ?, ?)'
  );

  db.exec('BEGIN');
  try {
    for (const line of lines) insert.run(userId, line.slice(0, 200), now, now);
    db.exec('COMMIT');
  } catch (error) {
    db.exec('ROLLBACK');
    throw error;
  }
  return lines.length;
}

const publicUrl = () => config.publicUrl || `http://localhost:${config.port}`;

/** Inline-кнопка мини-приложения: web_app требует HTTPS, иначе обычная ссылка. */
export const appButton = (text = 'Открыть календарь') =>
  publicUrl().startsWith('https://')
    ? { text, web_app: { url: publicUrl() } }
    : { text, url: publicUrl() };

/** Кнопка меню чата (слева от поля ввода) — только HTTPS. */
export const menuButton = () =>
  publicUrl().startsWith('https://')
    ? { type: 'web_app', text: 'Календарь', web_app: { url: publicUrl() } }
    : null;
