import { readFileSync } from 'node:fs';

/**
 * Минимальный YAML-ридер для deploy.sh: верхний уровень и один уровень
 * вложенности (section.key). Значения — строки без кавычек.
 *   node scripts/yaml-get.mjs remoteDocker.sshHost .deploy.yml
 */
const [keyPath, file] = process.argv.slice(2);
const keys = keyPath.split('.');

let section = '';
for (const line of readFileSync(file, 'utf8').split(/\r?\n/)) {
  if (!line.trim() || line.trim().startsWith('#')) continue;

  const indented = /^\s/.test(line);
  const match = line.match(/^\s*([\w-]+):\s*(.*)$/);
  if (!match) continue;

  const [, key, value] = match;
  if (!indented) {
    section = key;
    if (keys.length === 1 && key === keys[0]) {
      console.log(value.replace(/^["']|["']$/g, ''));
      process.exit(0);
    }
    continue;
  }

  if (keys.length === 2 && section === keys[0] && key === keys[1]) {
    console.log(value.replace(/^["']|["']$/g, ''));
    process.exit(0);
  }
}

console.error(`Не найден ключ "${keyPath}" в ${file}`);
process.exit(1);
