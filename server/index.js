import http from 'node:http';
import { config } from './config.js';
import './db.js';
import { isDevMode, json } from './http.js';
import { serveStatic } from './static.js';
import { handleAuth, handleLogout } from './routes/auth.js';
import { handleFileDelete, handleFileList, handleFileUpload } from './routes/files.js';
import { handleMe } from './routes/me.js';
import { handleTasks } from './routes/tasks.js';
import { HttpError } from './tasks.js';
import { handleWebhook, startBot } from './telegram/bot.js';

async function readJsonBody(req) {
  const chunks = [];
  let size = 0;
  for await (const chunk of req) {
    size += chunk.length;
    if (size > 1024 * 1024) throw new HttpError(413, 'Слишком большой запрос');
    chunks.push(chunk);
  }
  if (!chunks.length) return {};
  try {
    return JSON.parse(Buffer.concat(chunks).toString('utf8'));
  } catch {
    throw new HttpError(400, 'Некорректный JSON');
  }
}

async function routeApi(req, res, pathname) {
  const { method } = req;
  const body = method === 'POST' || method === 'PATCH' ? await readJsonBody(req) : {};

  if (pathname === '/api/config' && method === 'GET') {
    return json(res, 200, {
      dev: isDevMode(),
      botUsername: process.env.BOT_USERNAME || null,
      appShortName: process.env.APP_SHORT_NAME || null,
    });
  }
  if (pathname === '/api/auth' && method === 'POST') return handleAuth(req, res, body);
  if (pathname === '/api/logout' && method === 'POST') return handleLogout(req, res);
  if (pathname === '/api/me' && method === 'GET') return handleMe(req, res);

  if (pathname === '/api/tasks') return handleTasks(req, res, undefined, body);
  if (pathname.startsWith('/api/tasks/')) return handleTasks(req, res, pathname.split('/')[3], body);

  if (pathname === '/api/files') {
    if (method === 'GET') return handleFileList(req, res);
    if (method === 'POST') return handleFileUpload(req, res, body);
  }
  if (pathname.startsWith('/api/files/') && method === 'DELETE') {
    return handleFileDelete(req, res, decodeURIComponent(pathname.slice('/api/files/'.length)));
  }

  json(res, 404, { error: 'Not found' });
}

async function route(req, res) {
  const url = new URL(req.url, `http://${req.headers.host || 'localhost'}`);

  if (url.pathname.startsWith('/api/')) return routeApi(req, res, url.pathname);

  if (url.pathname === '/healthz') {
    res.writeHead(200, { 'Content-Type': 'text/plain' });
    return res.end('ok');
  }

  if (req.method !== 'GET' && req.method !== 'HEAD') {
    res.writeHead(405, { 'Content-Type': 'text/plain' });
    return res.end('Method not allowed');
  }

  // SPA: страницы без расширения (/, /app, /любой/путь) отдают index.html,
  // навигацию дальше ведёт SvelteKit. Всё с точкой — файл из static/.
  if (!url.pathname.includes('.') && (await serveStatic(res, '/'))) return;
  if (await serveStatic(res, url.pathname)) return;

  res.writeHead(404, { 'Content-Type': 'text/plain; charset=utf-8' });
  res.end('Not found');
}

const server = http.createServer((req, res) => {
  if (req.method === 'POST' && req.url === '/telegram/webhook') return handleWebhook(req, res);

  route(req, res).catch((error) => {
    const status = error instanceof HttpError ? error.status : 500;
    if (status === 500) console.error('[http]', error);
    if (res.headersSent) return res.end();
    json(res, status, { error: status === 500 ? 'Внутренняя ошибка' : error.message });
  });
});

server.listen(config.port, () => {
  console.log(`[http] http://localhost:${config.port}`);
  if (isDevMode()) console.log('[http] режим разработки включён (DEV_BYPASS_AUTH=true)');
  startBot();
});
