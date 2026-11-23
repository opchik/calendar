import { readFile } from 'node:fs/promises';
import path from 'node:path';
import { config } from './config.js';

/** SvelteKit (adapter-static) собирает сюда index.html и каталог _app/. */
const STATIC_DIR = path.resolve(config.staticDir);

const CONTENT_TYPES = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.svg': 'image/svg+xml',
  '.png': 'image/png',
  '.ico': 'image/x-icon',
  '.json': 'application/json',
  '.woff2': 'font/woff2',
  '.map': 'application/json',
};

/** Отдаёт файл из static/, если он существует. Возвращает false для 404. */
export async function serveStatic(res, pathname) {
  const relative = pathname === '/' ? 'index.html' : pathname.slice(1);
  const filePath = path.resolve(STATIC_DIR, relative);

  // Защита от выхода за пределы static/ через ../ и %2e%2e
  if (!filePath.startsWith(STATIC_DIR + path.sep)) return false;

  let data;
  try {
    data = await readFile(filePath);
  } catch {
    return false;
  }

  const ext = path.extname(filePath);
  res.writeHead(200, {
    'Content-Type': CONTENT_TYPES[ext] || 'application/octet-stream',
    'Cache-Control': ext === '.html' ? 'no-cache' : 'public, max-age=31536000, immutable',
  });
  res.end(data);
  return true;
}
