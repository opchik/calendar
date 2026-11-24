const DAY_MS = 24 * 60 * 60 * 1000;

const timeFormatter = new Intl.DateTimeFormat('ru-RU', {
  hour: '2-digit',
  minute: '2-digit',
});

const weekdayFormatter = new Intl.DateTimeFormat('ru-RU', { weekday: 'short' });
const monthFormatter = new Intl.DateTimeFormat('ru-RU', { month: 'long' });
const monthShortFormatter = new Intl.DateTimeFormat('ru-RU', { month: 'short' });
const fullDateFormatter = new Intl.DateTimeFormat('ru-RU', {
  weekday: 'long',
  day: 'numeric',
  month: 'long',
  hour: '2-digit',
  minute: '2-digit',
});

export const parseDate = (value) => (value instanceof Date ? value : new Date(value));

export function startOfDay(value) {
  const date = parseDate(value);
  return new Date(date.getFullYear(), date.getMonth(), date.getDate());
}

export function addDays(value, days) {
  const date = parseDate(value);
  return new Date(date.getTime() + days * DAY_MS);
}

export function isSameDay(a, b) {
  const first = parseDate(a);
  const second = parseDate(b);
  return (
    first.getFullYear() === second.getFullYear() &&
    first.getMonth() === second.getMonth() &&
    first.getDate() === second.getDate()
  );
}

export const dayKey = (value) => {
  const date = parseDate(value);
  return `${date.getFullYear()}-${date.getMonth()}-${date.getDate()}`;
};

export const formatTime = (value) => timeFormatter.format(parseDate(value));
export const formatWeekday = (value) => weekdayFormatter.format(parseDate(value));
export const formatMonth = (value) => monthFormatter.format(parseDate(value));
export const formatMonthShort = (value) => monthShortFormatter.format(parseDate(value));

export function formatFullDate(value) {
  const text = fullDateFormatter.format(parseDate(value));
  return text.charAt(0).toUpperCase() + text.slice(1);
}

export function formatDayTitle(value) {
  const date = parseDate(value);
  const today = startOfDay(new Date());
  if (isSameDay(date, today)) return 'Сегодня';
  if (isSameDay(date, addDays(today, 1))) return 'Завтра';
  const text = new Intl.DateTimeFormat('ru-RU', {
    weekday: 'long',
    day: 'numeric',
    month: 'long',
  }).format(date);
  return text.charAt(0).toUpperCase() + text.slice(1);
}

export function pluralize(count, one, few, many) {
  const mod10 = count % 10;
  const mod100 = count % 100;
  if (mod10 === 1 && mod100 !== 11) return one;
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 10 || mod100 >= 20)) return few;
  return many;
}

export function participantsLabel(count) {
  return `${count} ${pluralize(count, 'участник', 'участника', 'участников')}`;
}

export function groupUpcoming(events, now = new Date()) {
  const todayStart = startOfDay(now);
  const tomorrowStart = addDays(todayStart, 1);
  const weekEnd = addDays(todayStart, 7);

  const groups = [
    { key: 'today', title: 'Сегодня', events: [] },
    { key: 'week', title: 'На неделе', events: [] },
    { key: 'later', title: 'Позже', events: [] },
  ];

  const sorted = [...events]
    .filter((event) => parseDate(event.startsAt).getTime() >= todayStart.getTime())
    .sort((a, b) => parseDate(a.startsAt) - parseDate(b.startsAt));

  for (const event of sorted) {
    const startsAt = parseDate(event.startsAt);
    if (startsAt < tomorrowStart) groups[0].events.push(event);
    else if (startsAt < weekEnd) groups[1].events.push(event);
    else groups[2].events.push(event);
  }

  return groups.filter((group) => group.events.length);
}

export function buildMonthCells(year, month) {
  const first = new Date(year, month, 1);
  const leading = (first.getDay() + 6) % 7;
  const daysInMonth = new Date(year, month + 1, 0).getDate();
  const cells = [];

  for (let i = 0; i < leading; i += 1) cells.push(null);
  for (let day = 1; day <= daysInMonth; day += 1) {
    cells.push(new Date(year, month, day));
  }
  while (cells.length % 7 !== 0) cells.push(null);
  return cells;
}

export function eventsByDay(events) {
  const map = new Map();
  for (const event of events) {
    const key = dayKey(event.startsAt);
    if (!map.has(key)) map.set(key, []);
    map.get(key).push(event);
  }
  for (const list of map.values()) {
    list.sort((a, b) => parseDate(a.startsAt) - parseDate(b.startsAt));
  }
  return map;
}

export function toDatetimeLocal(value) {
  const date = parseDate(value);
  const pad = (number) => String(number).padStart(2, '0');
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

export function defaultEventDate() {
  const date = new Date(Date.now() + 60 * 60 * 1000);
  date.setMinutes(Math.ceil(date.getMinutes() / 15) * 15, 0, 0);
  return toDatetimeLocal(date);
}

export function fromDatetimeLocal(value) {
  return new Date(value).toISOString();
}

export function relativeLabel(value) {
  const diff = parseDate(value).getTime() - Date.now();
  if (diff < 0) return 'уже прошло';
  const hours = Math.floor(diff / (60 * 60 * 1000));
  if (hours < 1) return `через ${Math.max(1, Math.floor(diff / (60 * 1000)))} мин`;
  if (hours < 24) return `через ${hours} ${pluralize(hours, 'час', 'часа', 'часов')}`;
  const days = Math.floor(hours / 24);
  return `через ${days} ${pluralize(days, 'день', 'дня', 'дней')}`;
}

export const STATUS_LABELS = {
  going: 'Иду',
  maybe: 'Думаю',
  declined: 'Не смогу',
};

export function monthRange(date) {
  const start = new Date(date.getFullYear(), date.getMonth(), 1);
  const end = new Date(date.getFullYear(), date.getMonth() + 1, 0, 23, 59, 59);
  return { start, end };
}
