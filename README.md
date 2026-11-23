# Calendar — Telegram Mini App (SvelteKit + Node)

Мини-приложение для задач, которое открывается прямо в Telegram:
фронтенд — **Svelte 5 / SvelteKit 3**, бэкенд — **Node 22** без фреймворков
и без npm-зависимостей в рантайме (SQLite через встроенный `node:sqlite`).
Бот находит в вашем чате и открывает приложение, умеет импортировать задачи
из `.txt`.

---

## 1. Как это устроено

```
              Telegram (телефон / десктоп)
                       │  открывает webview по ссылке из BotFather
                       ▼
   ┌──────────────────────────────────────────────────────────┐
   │  Один контейнер (Node 22)                                 │
   │                                                          │
   │  SvelteKit SPA  (static/)                                 │
   │    index.html + _app/… — собранный фронтенд               │
   │        │ fetch /api/* (cookie-сессия)                     │
   │        ▼                                                  │
   │  HTTP-сервер (server/index.js)                            │
   │    GET  /healthz                                          │
   │    GET  /api/config    — dev-режим, имена бота и приложения│
   │    POST /api/auth      — initData → HttpOnly cookie       │
   │    /api/me, /api/tasks, /api/files                        │
   │    POST /telegram/webhook — обновления бота (webhook)     │
   │                                                          │
   │  Бот (server/telegram/bot.js)                              │
   │    polling локально / webhook в проде                     │
   │    /start → задачи + кнопка приложения                    │
   │    документ .txt → каждая строка = задача                 │
   │    меню-кнопка чата (web_app) при HTTPS                   │
   │                                                          │
   │  SQLite (/data/app.db) + файлы (/data/files)              │
   └──────────────────────────────────────────────────────────┘
                       │
                       ▼
              Telegram Bot API
```

**Ключевые решения**

| Что | Почему так |
|---|---|
| Svelte 5 (runes) + SvelteKit 3, `adapter-static` | один экран, натив-react-like реактивность, минимум кода; сборка в чистую статику |
| `ssr: false` → приложение работает в браузере Telegram | сервер не рендерит UI, только отдаёт файлы и JSON — деплой простой |
| Сервер — ванильный `node:http`, без зависимостей | образ ставит npm-пакеты только на этапе сборки фронтенда |
| Авторизация: `initData` → HMAC-подпись → HttpOnly cookie | нельзя доверять данным из клиента; cookie защищает API |
| Сессия — подписанный cookie, таблицы сессий нет | нет миграций, состояние переживает рестарт |
| Бот в том же процессе | один контейнер, один деплой; `BOT_MODE` переключает polling/webhook |
| `DEV_BYPASS_AUTH=true` | посмотреть UI в браузере без Telegram (только не-HTTPS) |

**Структура**

```
src/                         фронтенд (Svelte)
  app.html                   шаблон: Telegram SDK + %sveltekit.head/body%
  app.css                    стили на переменных темы Telegram
  routes/+layout.svelte      инициализация Telegram + загрузка данных
  routes/+page.svelte        единственный экран
  lib/api.js                 клиент REST API
  lib/telegram.js            обёртка window.Telegram.WebApp
  lib/stores/tasks.js        состояние: пользователь, задачи, ошибки
  lib/components/            TaskForm, TaskList, TaskItem, LoginScreen, ErrorBanner
server/                      бэкенд (Node)
  index.js                   HTTP-сервер и роутинг
  config.js                  настройки из env
  db.js                      схема SQLite
  session.js                 подписанный cookie
  http.js                    json / requireUser / dev-режим
  static.js                  отдача static/ + защита от ../ traversal
  tasks.js, users.js         доменная логика
  routes/                    auth, me, tasks, files
  cli.js                     локальное управление задачами из терминала
  telegram/initData.js       проверка подписи Telegram
  telegram/bot.js            бот: polling/webhook, /start, импорт .txt
  telegram/import.js         импорт задач и кнопки бота
static/                      результат `npm run build` (в git не попадает)
vite.config.js               SvelteKit-конфиг (SvelteKit 3: без svelte.config.js)
Dockerfile, docker-compose.yml, deploy.sh
```

---

## 2. Что нужно установить

- **Node.js 22.12+** (`node -v`) — для локальной разработки;
- **Docker + Docker Compose v2** — для запуска в контейнере;
- **Telegram** на телефоне или десктопе и аккаунт в [@BotFather](https://t.me/botfather).

---

## 3. Локальный запуск

### Вариант А — «хочу просто посмотреть»

```bash
npm install            # один раз
npm run build          # собрать фронтенд в static/
DEV_BYPASS_AUTH=true SESSION_SECRET=dev-secret-123456789012345678901234 node server/index.js
```

Откройте <http://localhost:3000>. Вы сразу в приложении как «Разработчик»:
можно добавлять, отмечать и удалять задачи. Данные лежат в `./data/app.db`.

### Вариант Б — разработка с hot-reload

Два терминала:

```bash
# 1) API и бот
DEV_BYPASS_AUTH=true SESSION_SECRET=dev-secret-123456789012345678901234 node server/index.js

# 2) Svelte с hot-reload (проксирует /api на :3000)
npm run dev            # http://localhost:5173
```

### Вариант В — Docker

```bash
cp .env.example .env   # минимум: BOT_TOKEN, SESSION_SECRET, PUBLIC_URL
docker compose up -d --build
docker compose logs -f calendar
curl localhost:3000/healthz        # → ok
```

Данные — в volume `calendar-data`, `docker compose down` их не удаляет
(полный сброс: `docker compose down -v`).

### CLI для быстрой проверки данных

```bash
npm run task -- list
npm run task -- add "Купить хлеб"
npm run task -- done 1
npm run task -- import tasks.txt
```

---

## 4. Проверка локально — контрольный список

| # | Что проверяем | Как | Ожидаемо |
|---|---|---|---|
| 1 | Сервер жив | `curl localhost:3000/healthz` | `ok` |
| 2 | UI грузится | открыть `http://localhost:3000` | «Привет, Разработчик!», список задач |
| 3 | Добавление | ввести задачу, «Добавить» | появилась в списке, сохранилась после F5 |
| 4 | Отметка | нажать кружок слева | зачёркнуто, сохранилось после F5 |
| 5 | Удаление | нажать ✕ | исчезло, после F5 не вернулось |
| 6 | Пустая задача | ввести пробелы | кнопка ничего не отправляет |
| 7 | API без сессии | `curl -i localhost:3000/api/me` (при `DEV_BYPASS_AUTH=false`) | `401` |
| 8 | Гостевая страница | открыть без Telegram при `DEV_BYPASS_AUTH=false` | «…открыть внутри Telegram» |
| 9 | Безопасность статики | `curl --path-as-is localhost:3000/../.env` | `404` |
| 10 | Webhook | `curl -X POST localhost:3000/telegram/webhook -d '{}'` | `401` без секретного заголовка |

---

## 5. Как попасть в приложение в **своём** Telegram

> Мини-приложение — это сайт, который Telegram открывает во встроенном
> браузере. Ему нужен **публичный HTTPS-адрес**: `localhost` телефон не видит,
> а BotFather принимает только `https://` (в тестовом окружении — ещё `http://`).

### Шаг 1. Домен и HTTPS на сервере

Направьте A-запись домена на IP сервера и поставьте TLS-прокси, например Caddy:

```caddyfile
calendar.example.com {
    reverse_proxy 127.0.0.1:3000
}
```

### Шаг 2. Бот

В [@BotFather](https://t.me/botfather): `/newbot` → имя → **токен**.

### Шаг 3. Мини-приложение

В BotFather: `/newapp` → выбрать бота → название → URL `https://calendar.example.com`.
Запомните **short name** (он в конце имени приложения).

### Шаг 4. Настройки

`.env`:

```dotenv
BOT_TOKEN=123456789:AAH...            # из шага 2
SESSION_SECRET=<openssl rand -hex 32> # подпись сессий и webhook
PUBLIC_URL=https://calendar.example.com
BOT_MODE=webhook
DEV_BYPASS_AUTH=false
BOT_USERNAME=my_calendar_bot          # без @
APP_SHORT_NAME=calendar               # short name из шага 3
```

### Шаг 5. Запуск

```bash
docker compose up -d --build
docker compose logs -f calendar
```

В логах должно быть:

```
[bot] webhook установлен: https://calendar.example.com/telegram/webhook
```

### Шаг 6. Открыть у себя в Telegram

Любой из способов — все ведут в одно и то же приложение:

1. **Прямая ссылка** `https://t.me/<BOT_USERNAME>/<APP_SHORT_NAME>` —
   перешлите её себе в «Избранное» и открывайте в один клик.
2. **Кнопка «Календарь»** в чате с ботом — появляется слева от поля ввода
   автоматически при старте сервера (меню-кнопка).
3. **`/start`** в чате с ботом → inline-кнопка «Открыть календарь».
4. Любое сообщение боту → он ответит кнопкой на приложение.

Внутри приложения первый запуск выглядит так: Telegram передаёт подписанные
данные пользователя → сервер проверяет подпись бота → выдаёт cookie-сессию →
вы видите «Привет, <ваше имя>!» и свой список задач (у каждого пользователя он отдельный).

### Вариант без сервера — временная ссылка

```bash
docker compose up -d --build
cloudflared tunnel --url http://localhost:3000   # бесплатно, даёт https://*.trycloudflare.com
```

Полученный HTTPS-адрес укажите в `PUBLIC_URL`, выполните `docker compose up -d`
и пропишите его в BotFather (`/myapps` → Edit link). Открывать — той же ссылкой
`https://t.me/<бот>/<short_name>`.

---

## 6. REST API

Авторизация — cookie `sid`. В dev-режиме cookie не обязательна.

| Метод | Путь | Тело | Ответ |
|---|---|---|---|
| GET | `/api/config` | — | `{ dev, botUsername, appShortName }` |
| POST | `/api/auth` | `{ initData }` | `{ ok: true }` + `Set-Cookie` |
| POST | `/api/logout` | — | `{ ok: true }` |
| GET | `/api/me` | — | `{ user }` |
| GET | `/api/tasks` | — | `{ tasks: [{ id, title, done, createdAt }] }` |
| POST | `/api/tasks` | `{ title }` | `201 { task }` |
| PATCH | `/api/tasks/:id` | `{ done?, title? }` | `{ task }` |
| DELETE | `/api/tasks/:id` | — | `{ ok: true }` |
| GET | `/api/files` | — | `{ files }` |
| POST | `/api/files` | `{ name, content: base64 }` | `201 { file }` |
| DELETE | `/api/files/:storedName` | — | `{ ok: true }` |

Ошибки: `{ "error": "…" }` со статусом 400/401/404/405/413/500.

---

## 7. Переменные окружения

| Переменная | По умолчанию | Описание |
|---|---|---|
| `BOT_TOKEN` | — | токен из BotFather; без него нет входа из Telegram и бота |
| `SESSION_SECRET` | случайный | подпись cookie и `secret_token` webhook |
| `PUBLIC_URL` | — | публичный адрес; нужен для webhook и кнопок |
| `BOT_MODE` | `polling` | `polling` (локально) или `webhook` (прод) |
| `BOT_USERNAME`, `APP_SHORT_NAME` | — | для ссылки `https://t.me/…` на гостевом экране |
| `DEV_BYPASS_AUTH` | `false` | вход без Telegram; работает только без HTTPS |
| `PORT` | `3000` | порт сервера |
| `DATA_DIR` | `data` | каталог SQLite и файлов |
| `STATIC_DIR` | `static` | собранный фронтенд |
| `INIT_DATA_MAX_AGE_SEC` | `86400` | срок жизни `initData` |
| `SESSION_TTL_SEC` | `2592000` | срок жизни cookie |

---

## 8. Ограничения и что дальше

- Календаря-сетки по месяцам ещё нет: сегодня это список задач;
  следующий шаг — поле `due_date` и выбор даты в UI.
- Нет rate limit и логирования запросов — для публичного приложения стоит добавить.
- Файлы хранятся на диске; для нескольких серверов — S3-совместимое хранилище.
- Смена `SESSION_SECRET` разлогинивает всех (нужно переоткрыть приложение).
