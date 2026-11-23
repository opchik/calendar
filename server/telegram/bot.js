import { config } from '../config.js';
import { listTasks } from '../tasks.js';
import { upsertUser } from '../users.js';
import { appButton, importTasks, menuButton } from './import.js';

let polling = false;

async function call(method, body = {}) {
  const res = await fetch(`https://api.telegram.org/bot${config.botToken}/${method}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  const data = await res.json();
  if (!data.ok) throw new Error(`${method}: ${data.description}`);
  return data.result;
}

const fromTelegram = (from) => ({
  id: from.id,
  first_name: from.first_name,
  last_name: from.last_name,
  username: from.username,
  language_code: from.language_code,
});

const displayName = (from) => [from.first_name, from.last_name].filter(Boolean).join(' ') || 'друг';

const sendText = (chatId, text, markup) =>
  call('sendMessage', { chat_id: chatId, text, reply_markup: markup });

async function onStart(message) {
  const user = upsertUser(fromTelegram(message.from));
  const tasks = listTasks(user.telegram_id);
  const pending = tasks.filter((task) => !task.done);

  const text = [
    `Привет, ${displayName(message.from)}!`,
    '',
    tasks.length
      ? `Открытых задач: ${pending.length} из ${tasks.length}.`
      : 'У вас пока нет задач.',
    ...tasks.slice(0, 10).map((task) => `${task.done ? '✅' : '◻️'} ${task.title}`),
    '',
    'Нажмите кнопку ниже, чтобы открыть календарь.',
    'Хотите загрузить список — пришлите файл .txt: каждая строка станет задачей.',
  ].join('\n');

  await sendText(message.chat.id, text, { inline_keyboard: [[appButton()]] });
}

async function onDocument(message) {
  const doc = message.document;
  const name = doc.file_name || '';

  if (!/\.txt$/i.test(name) || doc.file_size > 1024 * 1024) {
    return sendText(message.chat.id, 'Пришлите файл .txt до 1 МБ — каждая строка станет задачей.');
  }

  const user = upsertUser(fromTelegram(message.from));
  const file = await call('getFile', { file_id: doc.file_id });
  const res = await fetch(`https://api.telegram.org/file/bot${config.botToken}/${file.file_path}`);

  if (!res.ok) return sendText(message.chat.id, 'Не удалось скачать файл, попробуйте ещё раз.');

  const count = importTasks(user.telegram_id, await res.text());
  await sendText(
    message.chat.id,
    count ? `Добавлено задач: ${count}.` : 'В файле не нашлось строк для импорта.',
    { inline_keyboard: [[appButton()]] }
  );
}

async function onUpdate(update) {
  const message = update.message;
  if (!message?.from || message.from.is_bot) return;

  const text = message.text || '';
  if (text.startsWith('/start')) return onStart(message);
  if (message.document) return onDocument(message);
  if (text && !text.startsWith('/')) {
    return sendText(message.chat.id, 'Задачи удобнее вести в приложении:', {
      inline_keyboard: [[appButton()]],
    });
  }
}

function setupMenuButton() {
  const menu = menuButton();
  if (!menu) return;

  return call('setChatMenuButton', { menu_button: menu });
}

async function poll() {
  polling = true;
  let offset = 0;

  while (polling) {
    try {
      const updates = await call('getUpdates', { offset, timeout: 30, allowed_updates: ['message'] });
      for (const update of updates) {
        offset = update.update_id + 1;
        onUpdate(update).catch((error) => console.error('[bot]', error.message));
      }
    } catch (error) {
      console.error('[bot] polling:', error.message);
      await new Promise((resolve) => setTimeout(resolve, 3000));
    }
  }
}

/** Webhook от Telegram: POST /telegram/webhook с secret_token. */
export async function handleWebhook(req, res) {
  if (req.headers['x-telegram-bot-api-secret-token'] !== config.webhookSecret) {
    res.writeHead(401).end();
    return;
  }

  const chunks = [];
  for await (const chunk of req) chunks.push(chunk);

  try {
    onUpdate(JSON.parse(Buffer.concat(chunks).toString('utf8'))).catch((error) =>
      console.error('[bot]', error.message)
    );
  } catch {
    // некорректный JSON — не наш запрос
  }
  res.writeHead(200).end();
}

export async function startBot() {
  if (!config.botToken) return;

  try {
    if (config.botMode === 'webhook') {
      const url = `${config.publicUrl}/telegram/webhook`;
      await call('setWebhook', {
        url,
        secret_token: config.webhookSecret,
        allowed_updates: ['message'],
      });
      console.log('[bot] webhook установлен:', url);
    } else {
      await call('deleteWebhook', { drop_pending_updates: false });
      console.log('[bot] режим polling');
      poll();
    }
    await setupMenuButton();
  } catch (error) {
    console.error('[bot] не удалось запустить:', error.message);
  }

  const stop = () => {
    polling = false;
    process.exit(0);
  };
  process.once('SIGINT', stop);
  process.once('SIGTERM', stop);
}
