const API_BASE = '/api/v1';

export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
  }
}

function errorMessage(data, status) {
  const detail = data?.detail;
  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        const field = Array.isArray(item.loc) ? item.loc[item.loc.length - 1] : '';
        return field ? `${field}: ${item.msg}` : item.msg;
      })
      .join('; ');
  }
  if (typeof detail === 'string') return detail;
  return `Ошибка ${status}`;
}

async function request(path, { method = 'GET', body, form } = {}) {
  const headers = {};
  let payload;

  if (form) {
    payload = form;
  } else if (body !== undefined) {
    headers['Content-Type'] = 'application/json';
    payload = JSON.stringify(body);
  }

  let response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      method,
      headers,
      body: payload,
      credentials: 'same-origin',
    });
  } catch {
    throw new ApiError('Нет связи с сервером', 0);
  }

  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new ApiError(errorMessage(data, response.status), response.status);
  }
  return data;
}

const query = (params) => {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === null || value === '') continue;
    if (Array.isArray(value)) value.forEach((item) => search.append(key, item));
    else search.set(key, value);
  }
  const text = search.toString();
  return text ? `?${text}` : '';
};

export const api = {
  config: () => request('/config'),

  loginTelegram: (initData) =>
    request('/auth/telegram', { method: 'POST', body: { initData } }),
  logout: () => request('/auth/logout', { method: 'POST' }),
  me: () => request('/me'),

  circles: () => request('/circles'),
  createCircle: (payload) => request('/circles', { method: 'POST', body: payload }),
  updateCircle: (id, payload) =>
    request(`/circles/${id}`, { method: 'PATCH', body: payload }),
  deleteCircle: (id) => request(`/circles/${id}`, { method: 'DELETE' }),

  events: ({ from, to, circles } = {}) =>
    request(`/events${query({ from, to, circles })}`),
  event: (id) => request(`/events/${id}`),
  createEvent: (payload) => request('/events', { method: 'POST', body: payload }),
  updateEvent: (id, payload) =>
    request(`/events/${id}`, { method: 'PATCH', body: payload }),
  deleteEvent: (id) => request(`/events/${id}`, { method: 'DELETE' }),
  rsvp: (id, status) =>
    request(`/events/${id}/rsvp`, { method: 'POST', body: { status } }),

  comments: (id) => request(`/events/${id}/comments`),
  addComment: (id, text) =>
    request(`/events/${id}/comments`, { method: 'POST', body: { text } }),

  uploadCover: (file) => {
    const form = new FormData();
    form.append('file', file);
    return request('/uploads/cover', { method: 'POST', form });
  },
};
