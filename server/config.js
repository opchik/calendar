import { randomBytes } from 'node:crypto';
import { mkdirSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const num = (value, fallback) => (Number.isFinite(Number(value)) ? Number(value) : fallback);

const dataDir = path.resolve(process.env.DATA_DIR || 'data');
const filesDir = path.resolve(process.env.FILES_DIR || path.join(dataDir, 'files'));
mkdirSync(filesDir, { recursive: true });

const botToken = process.env.BOT_TOKEN || '';

export const config = {
  port: num(process.env.PORT, 3000),
  botToken,
  botMode: process.env.BOT_MODE || 'polling',
  publicUrl: (process.env.PUBLIC_URL || '').replace(/\/$/, ''),
  sessionSecret: process.env.SESSION_SECRET || randomBytes(32).toString('hex'),
  // Заголовок X-Telegram-Bot-Api-Secret-Token для webhook — без спецсимволов
  webhookSecret: (process.env.SESSION_SECRET || '').replace(/[^A-Za-z0-9_-]/g, '') || randomBytes(24).toString('hex'),
  sessionTtlSec: num(process.env.SESSION_TTL_SEC, 30 * 24 * 60 * 60),
  initDataMaxAgeSec: num(process.env.INIT_DATA_MAX_AGE_SEC, 24 * 60 * 60),
  devBypass: process.env.DEV_BYPASS_AUTH === 'true',
  maxFilesPerUser: num(process.env.MAX_FILES_PER_USER, 50),
  maxFileBytes: num(process.env.MAX_FILE_MB, 10) * 1024 * 1024,
  dataDir,
  filesDir,
  // Собранный фронтенд SvelteKit (npm run build → static/)
  staticDir: process.env.STATIC_DIR || fileURLToPath(new URL('../static/', import.meta.url)),
};

if (!config.botToken && !process.env.QUIET_CONFIG) {
  console.warn('[config] BOT_TOKEN не задан — вход через Telegram и бот недоступны');
}
if (!process.env.SESSION_SECRET && !process.env.QUIET_CONFIG) {
  console.warn('[config] SESSION_SECRET не задан — сессии сбросятся при перезапуске');
}
