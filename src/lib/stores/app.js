import { get, writable } from 'svelte/store';
import { api } from '#lib/api.js';
import { getStartParam } from '#lib/telegram.js';

const DAY_MS = 24 * 60 * 60 * 1000;

export const user = writable(null);
export const appConfig = writable({
  dev: false,
  botUsername: null,
  appShortName: null,
  publicUrl: '',
  keycloakEnabled: false,
});
export const circles = writable([]);
export const events = writable([]);
export const selectedCircleIds = writable([]);
export const view = writable('feed');
export const activeEvent = writable(null);
export const loading = writable(true);
export const errorMessage = writable('');
export const toastMessage = writable('');

let booted = false;
let toastTimer;

export const clearError = () => errorMessage.set('');
export const showError = (message) => errorMessage.set(message ?? 'Что-то пошло не так');

export function showToast(message) {
  toastMessage.set(message);
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => toastMessage.set(''), 2600);
}

export function toggleCircle(id) {
  selectedCircleIds.update((selected) => {
    if (!selected.length) return [id];
    return selected.includes(id)
      ? selected.filter((item) => item !== id)
      : [...selected, id];
  });
}

export const clearCircleFilter = () => selectedCircleIds.set([]);

export function filterEvents(list, selected) {
  if (!selected.length) return list;
  return list.filter((event) => !event.circle || selected.includes(event.circle.id));
}

export async function loadCircles() {
  const list = await api.circles();
  circles.set(list);
  const ids = new Set(list.map((circle) => circle.id));
  selectedCircleIds.update((selected) => selected.filter((id) => ids.has(id)));
}

export async function loadEvents() {
  const now = Date.now();
  const data = await api.events({
    from: new Date(now - 92 * DAY_MS).toISOString(),
    to: new Date(now + 365 * DAY_MS).toISOString(),
  });
  events.set(data.events);
}

export async function bootstrap(tg) {
  if (booted) return;
  booted = true;
  loading.set(true);

  try {
    const config = await api.config();
    appConfig.set(config);

    if (typeof window !== 'undefined') {
      const url = new URL(window.location.href);
      if (url.searchParams.has('auth_error')) {
        showError('Не удалось войти. Попробуйте ещё раз.');
        url.searchParams.delete('auth_error');
        window.history.replaceState({}, '', url);
      }
    }

    if (tg?.initData) {
      try {
        await api.loginTelegram(tg.initData);
      } catch (error) {
        if (error.status !== 401) throw error;
      }
    }

    try {
      const me = await api.me();
      user.set(me.user);
      await Promise.all([loadCircles(), loadEvents()]);

      const startParam = getStartParam();
      if (startParam?.startsWith('event_')) {
        try {
          activeEvent.set(await api.event(startParam.slice('event_'.length)));
        } catch {
          showToast('Событие не найдено или недоступно');
        }
      }
    } catch (error) {
      if (error.status === 401) {
        user.set(null);
      } else {
        throw error;
      }
    }
  } catch (error) {
    showError(error.message);
  } finally {
    loading.set(false);
  }
}

export async function openEvent(id) {
  const event = await api.event(id);
  activeEvent.set(event);
  return event;
}

export async function createEvent(payload) {
  const event = await api.createEvent(payload);
  events.update((list) =>
    [...list, event].sort((a, b) => new Date(a.startsAt) - new Date(b.startsAt)),
  );
  return event;
}

export async function updateEvent(id, payload) {
  const event = await api.updateEvent(id, payload);
  events.update((list) => list.map((item) => (item.id === id ? event : item)));
  activeEvent.set(event);
  return event;
}

export async function deleteEvent(id) {
  await api.deleteEvent(id);
  events.update((list) => list.filter((item) => item.id !== id));
  activeEvent.set(null);
}

export async function rsvp(eventId, status) {
  const event = await api.rsvp(eventId, status);
  events.update((list) => {
    const exists = list.some((item) => item.id === event.id);
    const next = exists ? list.map((item) => (item.id === event.id ? event : item)) : [...list, event];
    return next.sort((a, b) => new Date(a.startsAt) - new Date(b.startsAt));
  });
  activeEvent.set(event);
  return event;
}

export async function createCircle(payload) {
  const circle = await api.createCircle(payload);
  circles.update((list) => [...list, circle]);
  return circle;
}

export async function updateCircle(id, payload) {
  const circle = await api.updateCircle(id, payload);
  circles.update((list) => list.map((item) => (item.id === id ? circle : item)));
  events.update((list) =>
    list.map((event) =>
      event.circle?.id === id ? { ...event, circle } : event,
    ),
  );
  return circle;
}

export async function deleteCircle(id) {
  await api.deleteCircle(id);
  circles.update((list) => list.filter((item) => item.id !== id));
  selectedCircleIds.update((selected) => selected.filter((item) => item !== id));
  events.update((list) =>
    list.map((event) =>
      event.circle?.id === id
        ? {
            ...event,
            circle: null,
            privacy: event.privacy === 'circle' ? 'link' : event.privacy,
          }
        : event,
    ),
  );
}

export function currentEvent() {
  return get(activeEvent);
}
