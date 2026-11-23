import { createInterface } from 'node:readline';
import { createReadStream } from 'node:fs';
import { config } from './config.js';
import { db } from './db.js';
import { importTasks } from './telegram/import.js';

const DEV_USER_ID = 1;
const [command, ...args] = process.argv.slice(2);

const now = () => Math.floor(Date.now() / 1000);
const usage = [
  'Команды:',
  '  npm run task -- list',
  '  npm run task -- add "Купить хлеб"',
  '  npm run task -- done <id>',
  '  npm run task -- import tasks.txt   (или stdin)',
  '',
  `Данные: ${config.dataDir}`,
].join('\n');

const commands = {
  list() {
    const rows = db
      .prepare('SELECT id, title, done FROM tasks WHERE user_id = ? ORDER BY done, id DESC')
      .all(DEV_USER_ID);

    if (!rows.length) return console.log('Задач нет');
    for (const row of rows) console.log(`${row.done ? '✓' : '·'} ${row.id}  ${row.title}`);
  },

  add() {
    const title = args.join(' ').trim();
    if (!title) throw new Error('Укажите задачу: npm run task -- add "Купить хлеб"');

    const { lastInsertRowid } = db
      .prepare('INSERT INTO tasks (user_id, title, created_at, updated_at) VALUES (?, ?, ?, ?)')
      .run(DEV_USER_ID, title.slice(0, 200), now(), now());

    console.log(`Добавлено (id ${lastInsertRowid}): ${title}`);
  },

  done() {
    const id = Number(args[0]);
    if (!Number.isInteger(id)) throw new Error('Укажите id: npm run task -- done 3');

    const { changes } = db
      .prepare('UPDATE tasks SET done = 1, updated_at = ? WHERE id = ? AND user_id = ?')
      .run(now(), id, DEV_USER_ID);

    if (!changes) throw new Error(`Не найдено: id ${id}`);
    console.log(`Готово: id ${id}`);
  },

  async import() {
    const lines = [];
    const input = args[0] ? createReadStream(args[0]) : process.stdin;
    for await (const line of createInterface({ input, crlfDelay: Infinity })) lines.push(line);

    const count = importTasks(DEV_USER_ID, lines.join('\n'));
    console.log(`Импортировано задач: ${count}`);
  },
};

if (!commands[command]) {
  console.log(usage);
  process.exit(command ? 1 : 0);
}

try {
  await commands[command]();
} catch (error) {
  console.error(error.message);
  process.exit(1);
}
