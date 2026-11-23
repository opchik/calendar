import { tg } from '#lib/telegram.js';

export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
  }
}

async function request(path, { method = 'GET', body } = {}) {
  const headers = { 'Content-Type': 'application/json' };
  if (tg?.initData) headers.Authorization = `tma ${tg.initData}`;

  let res;
  try {
    res = await fetch(path, {
      method,
      headers,
      credentials: 'same-origin',
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch {
    throw new ApiError('Нет связи с сервером', 0);
  }

  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new ApiError(data.error || `Ошибка ${res.status}`, res.status);
  return data;
}

export const api = {
  auth: (initData) => request('/api/auth', { method: 'POST', body: { initData } }),
  config: () => request('/api/config'),
  me: () => request('/api/me'),
  listTasks: () => request('/api/tasks'),
  createTask: (title) => request('/api/tasks', { method: 'POST', body: { title } }),
  updateTask: (id, patch) => request(`/api/tasks/${id}`, { method: 'PATCH', body: patch }),
  deleteTask: (id) => request(`/api/tasks/${id}`, { method: 'DELETE' }),
};
