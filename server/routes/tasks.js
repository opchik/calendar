import { json, requireUser } from '../http.js';
import { createTask, deleteTask, listTasks, updateTask } from '../tasks.js';

const parseId = (value) => {
  const id = Number(value);
  return Number.isInteger(id) && id > 0 ? id : null;
};

export function handleTasks(req, res, rawId, body) {
  const userId = requireUser(req).telegram_id;
  const id = rawId === undefined ? null : parseId(rawId);

  if (rawId !== undefined && id === null) return json(res, 400, { error: 'Некорректный id' });

  if (!id) {
    if (req.method === 'GET') return json(res, 200, { tasks: listTasks(userId) });
    if (req.method === 'POST') return json(res, 201, { task: createTask(userId, body.title) });
    return json(res, 405, { error: 'Method not allowed' });
  }

  if (req.method === 'PATCH') return json(res, 200, { task: updateTask(userId, id, body) });
  if (req.method === 'DELETE') {
    deleteTask(userId, id);
    return json(res, 200, { ok: true });
  }

  json(res, 405, { error: 'Method not allowed' });
}
