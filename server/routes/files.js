import { createWriteStream } from 'node:fs';
import { mkdir, readdir, stat, unlink } from 'node:fs/promises';
import path from 'node:path';
import { config } from '../config.js';
import { json, requireUser } from '../http.js';
import { HttpError } from '../tasks.js';

const ALLOWED_EXTENSIONS = new Set(['.txt', '.md', '.json', '.jpg', '.jpeg', '.png', '.webp', '.gif']);

const userDir = (userId) => path.join(config.filesDir, String(userId));

/** POST /api/files — сохраняет файл пользователя. Body: { name, content: base64 }. */
export async function handleFileUpload(req, res, body) {
  const userId = requireUser(req).telegram_id;
  const { name, content } = body;

  if (typeof name !== 'string' || typeof content !== 'string') {
    throw new HttpError(400, 'Ожидаются поля name и content (base64)');
  }

  const baseName = path.basename(name).replace(/[^\w.-]+/g, '_');
  if (!ALLOWED_EXTENSIONS.has(path.extname(baseName).toLowerCase())) {
    throw new HttpError(400, 'Недопустимый тип файла');
  }

  const bytes = Buffer.from(content, 'base64');
  if (!bytes.length) throw new HttpError(400, 'Файл пустой');
  if (bytes.length > config.maxFileBytes) {
    throw new HttpError(413, `Максимум ${config.maxFileBytes / 1024 / 1024} МБ`);
  }

  const dir = userDir(userId);
  await mkdir(dir, { recursive: true });
  if ((await readdir(dir)).length >= config.maxFilesPerUser) {
    throw new HttpError(403, `Максимум ${config.maxFilesPerUser} файлов`);
  }

  const storedName = `${Date.now()}-${baseName}`;
  await new Promise((resolve, reject) => {
    const stream = createWriteStream(path.join(dir, storedName));
    stream.on('error', reject);
    stream.on('end', resolve);
    stream.end(bytes);
  });

  json(res, 201, { file: { name: baseName, storedName, size: bytes.length } });
}

/** GET /api/files — список файлов пользователя. */
export async function handleFileList(req, res) {
  const userId = requireUser(req).telegram_id;
  const dir = userDir(userId);
  const names = await readdir(dir).catch(() => []);

  const files = await Promise.all(
    names.map(async (storedName) => {
      const info = await stat(path.join(dir, storedName));
      return { name: storedName.slice(storedName.indexOf('-') + 1), storedName, size: info.size };
    })
  );

  json(res, 200, { files: files.sort((a, b) => b.storedName.localeCompare(a.storedName)) });
}

/** DELETE /api/files/:storedName */
export async function handleFileDelete(req, res, storedName) {
  const dir = userDir(requireUser(req).telegram_id);
  const filePath = path.join(dir, path.basename(storedName));

  await unlink(filePath).catch(() => {
    throw new HttpError(404, 'Файл не найден');
  });
  json(res, 200, { ok: true });
}
