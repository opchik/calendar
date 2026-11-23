import { db } from './db.js';

const MAX_TITLE = 200;

const row = (task) => ({
  id: task.id,
  title: task.title,
  done: Boolean(task.done),
  createdAt: task.created_at * 1000,
});

export const listTasks = (userId) =>
  db.prepare('SELECT * FROM tasks WHERE user_id = ? ORDER BY done, id DESC').all(userId).map(row);

export function createTask(userId, title) {
  const clean = typeof title === 'string' ? title.trim() : '';
  if (!clean) throw new HttpError(400, 'Название не может быть пустым');
  if (clean.length > MAX_TITLE) throw new HttpError(400, `Максимум ${MAX_TITLE} символов`);

  const now = Math.floor(Date.now() / 1000);
  const { lastInsertRowid } = db
    .prepare('INSERT INTO tasks (user_id, title, created_at, updated_at) VALUES (?, ?, ?, ?)')
    .run(userId, clean, now, now);

  return row(db.prepare('SELECT * FROM tasks WHERE id = ?').get(lastInsertRowid));
}

export function updateTask(userId, id, { done, title }) {
  const task = db.prepare('SELECT * FROM tasks WHERE id = ? AND user_id = ?').get(id, userId);
  if (!task) throw new HttpError(404, 'Задача не найдена');

  const nextTitle =
    typeof title === 'string' && title.trim() ? title.trim().slice(0, MAX_TITLE) : task.title;
  const nextDone = typeof done === 'boolean' ? done : Boolean(task.done);

  db.prepare('UPDATE tasks SET title = ?, done = ?, updated_at = ? WHERE id = ?').run(
    nextTitle,
    Number(nextDone),
    Math.floor(Date.now() / 1000),
    id
  );

  return row(db.prepare('SELECT * FROM tasks WHERE id = ?').get(id));
}

export function deleteTask(userId, id) {
  const { changes } = db.prepare('DELETE FROM tasks WHERE id = ? AND user_id = ?').run(id, userId);
  if (!changes) throw new HttpError(404, 'Задача не найдена');
}

export class HttpError extends Error {
  constructor(status, message) {
    super(message);
    this.status = status;
  }
}
