import { get, writable } from 'svelte/store';
import { api } from '#lib/api.js';

/** Ошибки показываем одной плашкой. */
export const errorMessage = writable('');
export const clearError = () => errorMessage.set('');

/** Пользователь; null — экран «откройте приложение в Telegram». */
export const user = writable(null);
export const tasks = writable([]);

/** Флаги сервера: dev-режим, username бота, short name мини-приложения. */
export const appConfig = writable({ dev: false, botUsername: null, appShortName: null });

const DAY = 24 * 60 * 60 * 1000;
const AUTH_KEY = 'auth_ts';

/** Telegram initData → cookie-сессия. Не чаще раза в сутки. */
async function ensureSession(tg) {
  if (!tg?.initData) return;
  if (Date.now() - Number(localStorage.getItem(AUTH_KEY) || 0) < DAY) return;

  await api.auth(tg.initData);
  localStorage.setItem(AUTH_KEY, String(Date.now()));
}

export async function addTask(title) {
  const { task } = await api.createTask(title);
  tasks.update((list) => [task, ...list]);
}

export async function toggleTask(id) {
  const snapshot = get(tasks);
  const target = snapshot.find((task) => task.id === id);
  if (!target) return;

  const done = !target.done;
  tasks.update((list) => list.map((item) => (item.id === id ? { ...item, done } : item)));
  try {
    const { task } = await api.updateTask(id, { done });
    tasks.update((list) => list.map((item) => (item.id === id ? task : item)));
  } catch (error) {
    tasks.set(snapshot);
    throw error;
  }
}

export async function removeTask(id) {
  const snapshot = get(tasks);
  tasks.update((list) => list.filter((task) => task.id !== id));
  try {
    await api.deleteTask(id);
  } catch (error) {
    tasks.set(snapshot);
    throw error;
  }
}

/** Запуск приложения: флаги → авторизация → пользователь и задачи. */
export async function start(tg) {
  try {
    appConfig.set(await api.config());
    await ensureSession(tg);

    user.set((await api.me()).user);
    tasks.set((await api.listTasks()).tasks);
  } catch (error) {
    if (error.status === 401) {
      user.set(null);
      tasks.set([]);
      return;
    }
    errorMessage.set(error.message);
  }
}
