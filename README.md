# Планы — социальный календарь в Telegram

Telegram Mini App для совместных планов: создаёте событие, кидаете ссылку в чат,
друзья открывают карточку и отвечают «Иду / Думаю / Не смогу». Всё обсуждение
идёт в комментариях под событием, а бот напоминает о встрече за 24 и 2 часа.

Текущая реализация — **MVP**: вход через Telegram Mini App и email (внутри — Keycloak),
лента и календарь, круги-категории, создание событий, RSVP, комментарии,
обложки, шеринг и напоминания.

---

## Стек

| Часть | Технологии |
|---|---|
| Frontend | Svelte 5 / SvelteKit 3, `adapter-static`, чистый CSS на переменных Telegram |
| Backend | Python 3.12, FastAPI, aiogram 3, Keycloak OIDC |
| БД | PostgreSQL, SQLAlchemy 2 async, Alembic |
| Инфраструктура | Docker, Docker Compose, Nginx, HTTPS |

Фронтенд оставлен на Svelte (вместо React/Next из исходного ТЗ) — под задачу
«Telegram Mini App + статика» он проще и легче; API и модель данных от этого
не меняются.

---

## Как это работает

```
Browser ──HTTPS──▶ Nginx ──▶ FastAPI (uvicorn)
Telegram WebApp ──▶ (тот же домен)        │
                                          ├─ /api/v1/...       REST API
                                          ├─ /auth/keycloak/*  OIDC login
                                          ├─ /uploads/...      обложки
                                          ├─ /telegram/webhook бот
                                          ├─ /                 Svelte SPA
                                          ├─ aiogram           /start
                                          └─ reminder loop     24ч / 2ч
                                                    │
                                                    ▼
                                      PostgreSQL (SQLAlchemy + Alembic)
                                                    │
Browser ──redirect──▶ Keycloak (OIDC provider)
```

Бот и API живут в одном процессе. Для MVP этого достаточно; при масштабировании
напоминания лучше вынести в отдельный worker с очередью.

## Аутентификация

Поддерживаются три способа:

1. **Telegram Mini App** — `initData` проверяется по HMAC, пользователь
   создаётся/обновляется, выдаётся серверная cookie-сессия.
2. **Keycloak (браузер)** — OIDC Authorization Code Flow + PKCE. Бэкенд
   перенаправляет в Keycloak, обменивает код на токены, проверяет подпись
   `id_token` по JWKS, создаёт пользователя по `sub` и выдаёт ту же
   cookie-сессию.
3. **Dev-режим** — `DEV_BYPASS_AUTH=true` только при не-HTTPS `PUBLIC_URL`,
   чтобы смотреть UI в браузере без внешних сервисов.

Один пользователь может иметь `telegram_id` или `keycloak_sub` (или оба, если
вы позже добавите связывание аккаунтов). Сейчас автоматического связывания
Telegram- и Keycloak-аккаунтов нет.

---

## Схема базы данных

### `users`

| Поле | Тип | Описание |
|---|---|---|
| `id` | UUID PK | внутренний id |
| `telegram_id` | BIGINT UNIQUE, nullable | Telegram ID |
| `keycloak_sub` | VARCHAR UNIQUE, nullable | `sub` из Keycloak |
| `email` | VARCHAR, nullable | email из Keycloak |
| `username`, `first_name`, `last_name` | VARCHAR | профиль |
| `photo_url` | VARCHAR | аватар |
| `language_code` | VARCHAR | язык Telegram |
| `timezone` | VARCHAR | часовой пояс пользователя |
| `created_at`, `last_seen_at` | TIMESTAMPTZ | служебные |

### `circles`

| Поле | Тип | Описание |
|---|---|---|
| `id` | UUID PK | |
| `owner_id` | UUID FK → users | владелец |
| `name` | VARCHAR(50) | «Семья», «Друзья», «Работа»… |
| `color` | VARCHAR(7) | HEX-цвет |
| `position` | INT | порядок в фильтрах |

У пользователя уникальные имена кругов. При первом входе создаются четыре круга.

### `events`

| Поле | Тип | Описание |
|---|---|---|
| `id` | UUID PK | используется в `startapp=event_<id>` |
| `owner_id` | UUID FK → users | автор |
| `circle_id` | UUID FK → circles, nullable | категория |
| `title` | VARCHAR(120) | название |
| `description` | TEXT | детали |
| `starts_at` | TIMESTAMPTZ | дата и время |
| `location_text`, `location_url` | VARCHAR | место или ссылка |
| `cover` | VARCHAR | `preset:*` или `/uploads/...` |
| `privacy` | VARCHAR | `private`, `link`, `circle` |
| `created_at`, `updated_at` | TIMESTAMPTZ | |

### `event_participants`

| Поле | Тип | Описание |
|---|---|---|
| `event_id` | UUID FK → events | часть составного PK |
| `user_id` | UUID FK → users | часть составного PK |
| `status` | VARCHAR | `going`, `maybe`, `declined` |
| `role` | VARCHAR | `owner`, `guest` |
| `created_at`, `updated_at` | TIMESTAMPTZ | |

Уникальная пара `(event_id, user_id)`. Автор автоматически становится
участником со статусом `going` и ролью `owner`.

### `comments`

| Поле | Тип | Описание |
|---|---|---|
| `id` | UUID PK | |
| `event_id` | UUID FK → events | |
| `user_id` | UUID FK → users | автор |
| `text` | TEXT | до 1000 символов |
| `created_at` | TIMESTAMPTZ | |

### `sessions`

| Поле | Тип | Описание |
|---|---|---|
| `id` | UUID PK | |
| `user_id` | UUID FK → users | |
| `token_hash` | VARCHAR(64) UNIQUE | SHA-256 от cookie-токена |
| `expires_at`, `last_seen_at` | TIMESTAMPTZ | |

Сессии серверные — можно отзывать и делать logout.

### `reminder_logs`

| Поле | Тип | Описание |
|---|---|---|
| `event_id`, `user_id` | FK | участник и событие |
| `kind` | VARCHAR | `24h` или `2h` |
| `sent_at` | TIMESTAMPTZ | когда отправлено |

Уникальность `(event_id, user_id, kind)` не даёт отправить напоминание дважды.

---

## User Flow

### 1. Приглашение по ссылке

1. Пользователь создаёт событие.
2. Приложение формирует ссылку
   `https://t.me/<bot>/<app>?startapp=event_<uuid>`.
3. Друг открывает ссылку в Telegram → запускается Mini App.
4. Фронтенд получает `Telegram.WebApp.initDataUnsafe.start_param` или
   `?startapp=event_<uuid>`.
5. `initData` уходит на `POST /api/v1/auth/telegram`; сервер проверяет подпись,
   создаёт пользователя при необходимости и выдаёт cookie-сессию.
6. Приложение загружает событие по id и открывает карточку.
7. Гость видит детали, участников, комментарии и кнопки
   **«Иду» / «Думаю» / «Не смогу»**.
8. После ответа создаётся/обновляется `event_participants`.
   Событие появляется в его ленте при статусах `going` и `maybe`.
9. Дальше он может писать комментарии и делиться ссылкой.

### 2. Создание события

1. Главный экран → кнопка **＋**.
2. Форма: название, дата/время, место или ссылка, детали, круг,
   приватность, обложка (8 пресетов или своя картинка).
3. `POST /api/v1/events`.
4. Автор автоматически становится участником.
5. Карточка сразу открывается, можно нажать «Поделиться ссылкой».

### 3. Лента и календарь

- **Лента**: группы «Сегодня / На неделе / Позже».
- **Календарь**: месячная сетка с цветными точками по кругам.
- Фильтр по кругам: скрыть «Работу» или оставить только «Друзей».

### 4. Напоминания

Фоновый loop раз в минуту ищет события:

- от 2 до 24 часов до начала → напоминание `24h`;
- менее 2 часов до начала → напоминание `2h`.

Сообщение получают только участники со статусом `going`. Факт отправки
пишется в `reminder_logs`, поэтому повторной отправки не будет.

---

## Структура проекта

```
backend/
  alembic/                   миграции
  alembic.ini
  requirements.txt
  requirements-mysql.txt     опционально: MySQL-драйвер asyncmy
  app/
    main.py                  FastAPI, статика, webhook, lifespan
    config.py                настройки из env
    db.py                    async engine + session factory
    models.py                SQLAlchemy-модели
    schemas.py               Pydantic-схемы
    security.py              initData, токены сессий
    deps.py                  текущий пользователь, сессия БД
    api/v1/
      auth.py                Telegram-авторизация
      keycloak.py            OIDC login/callback
      users.py               /me
      circles.py             круги
      events.py              события, RSVP, комментарии
      uploads.py             загрузка обложек
      system.py              /config
    services/
      users.py               upsert Telegram/Keycloak пользователей
      keycloak.py            discovery, PKCE, обмен кода, JWT/JWKS
      circles.py             CRUD кругов
      events.py              доступ, сериализация, CRUD, RSVP
      reminders.py           фоновые напоминания
    bot/
      runtime.py             aiogram dispatcher, /start, webhook/polling

src/                         фронтенд Svelte
  app.html
  app.css
  routes/+layout.svelte      инициализация Telegram и загрузка данных
  routes/+page.svelte        лента, календарь, модалки
  lib/api.js                 REST-клиент
  lib/telegram.js            Telegram SDK, start_param, share
  lib/stores/app.js          состояние приложения
  lib/utils/date.js          даты, группировка, сетка месяца
  lib/utils/covers.js        пресеты обложек
  lib/components/            EventCard, CalendarView, CreateEventSheet,
                             EventDetailSheet, CircleFilters, CirclesSheet…

Dockerfile
docker-compose.yml           db + api
deploy.sh                    доставка образа на сервер
deploy/nginx/
  calendar-http.conf         HTTP для первого запуска/certbot
  calendar.conf              HTTPS reverse proxy
Makefile
```

---

## Запуск приложения

Нужны **Python 3.12+**, **Node.js 22.12+** и PostgreSQL 16
(или Docker для БД).

### Режимы запуска

Да, FastAPI можно запускать **с визуалом в браузере без Telegram-бота**.
Для этого используется dev-режим: приложение работает без авторизации,
а бот и напоминания отключены.

| Режим | `BOT_TOKEN` | `DEV_BYPASS_AUTH` | `PUBLIC_URL` | Что работает |
|---|---|---|---|---|
| Браузер без авторизации | пусто | `true` | `http://localhost:8000` | UI, события, RSVP, комментарии, обложки. Без Telegram, Keycloak, бота и напоминаний |
| Браузер + бот | реальный | `true` | `http://localhost:8000` | То же + бот и напоминания в Telegram. Браузер остаётся в dev-режиме |
| Браузер + email | опционально | `false` | `https://...` | Вход по email (Keycloak), UI, события, бот при наличии `BOT_TOKEN` |
| Полный Telegram + email | реальный | `false` | `https://...` | Вход через `initData` и по email, Mini App, бот, deep links, напоминания |

`DEV_BYPASS_AUTH=true` работает только при **не-HTTPS** `PUBLIC_URL`.
Это защита от случайного включения dev-входа в проде.

### Шаг 1. Настройки

```bash
cp .env.example .env
```

**Браузер без Telegram-бота:**

```dotenv
BOT_TOKEN=
BOT_MODE=polling
DEV_BYPASS_AUTH=true
PUBLIC_URL=http://localhost:8000
DATABASE_URL=postgresql+asyncpg://calendar:calendar@localhost:5433/calendar
POSTGRES_PORT=5433
```

В этом режиме:
- `GET /api/v1/me` возвращает dev-пользователя;
- кнопка «Поделиться» даёт ссылку
  `http://localhost:8000/?startapp=event_<uuid>` — она открывается в браузере;
- ссылки `https://t.me/...` не используются, потому что бота нет;
- бот и напоминания пишут в лог предупреждение и не запускаются.

**Для Telegram** дополнительно заполните `BOT_TOKEN`, `BOT_USERNAME`,
`APP_SHORT_NAME`, поставьте `DEV_BYPASS_AUTH=false` и HTTPS-адрес в
`PUBLIC_URL`.

**Для входа по email в браузере (Keycloak):**

```dotenv
DEV_BYPASS_AUTH=false
KEYCLOAK_ENABLED=true
KEYCLOAK_ISSUER=https://kc.example.com/realms/calendar
KEYCLOAK_CLIENT_ID=calendar-web
KEYCLOAK_CLIENT_SECRET=
```

Callback в Keycloak:
`PUBLIC_URL/api/v1/auth/keycloak/callback`.

### Шаг 2. Зависимости

```bash
make install
```

Команда создаёт `backend/.venv`, ставит Python-зависимости и выполняет
`npm ci`.

### Шаг 3. База данных

Если PostgreSQL ещё нет:

```bash
docker compose up -d db
# или
make db
```

В `.env.example` уже выбран `POSTGRES_PORT=5433`, чтобы не конфликтовать
с локальным PostgreSQL на `5432`. Если хотите использовать другой порт,
измените одновременно `POSTGRES_PORT` и порт в `DATABASE_URL`.

Если PostgreSQL уже установлен локально, просто укажите его в `DATABASE_URL`
и не поднимайте контейнер `db`.

### Шаг 4. Миграции

```bash
make migrate
```

Без этого приложение ответит ошибкой `relation "users" does not exist`.

### Шаг 5. Сборка фронтенда

```bash
npm run build
```

FastAPI раздаёт собранные файлы из `static/`. Если `static/index.html` нет,
корневая страница вернёт `Frontend is not built`.

### Шаг 6. Запуск

```bash
make backend
```

Приложение: <http://localhost:8000>.

Для режима «браузер без бота» вы сразу попадёте внутрь без авторизации.
Проверка:

```bash
curl -s localhost:8000/healthz      # {"status":"ok"}
curl -s localhost:8000/readyz       # {"status":"ready"}
curl -s localhost:8000/api/v1/config
```

### Шаг 7. Разработка с hot-reload

```bash
# терминал 1 — API и БД
make backend

# терминал 2 — Svelte
make frontend       # http://localhost:5173, /api проксируется на :8000
```

### Шаг 8. Docker

```bash
npm ci && npm run build
cp .env.example .env
# заполните .env под нужный режим
docker compose up -d --build
docker compose logs -f calendar
curl localhost:8000/healthz
```

Одной командой: `make up`. Compose поднимает PostgreSQL и приложение,
миграции Alembic выполняются в контейнере при старте.

Остановить:

```bash
docker compose down          # данные сохранятся
docker compose down -v       # удалить БД и загруженные файлы
```

### Частые проблемы

| Симптом | Причина / решение |
|---|---|
| `Frontend is not built` | не выполнен `npm run build` |
| `relation "users" does not exist` | не выполнен `make migrate` |
| `address already in use` | занят `APP_PORT` или `POSTGRES_PORT` — поменяйте в `.env` |
| В браузере 401 и экран входа | `DEV_BYPASS_AUTH` выключен или `PUBLIC_URL` начинается с `https://` |
| Бот не отвечает | нет `BOT_TOKEN`, неверный `BOT_MODE` или Telegram недоступен |
| Mini App открывает экран входа | для Telegram нужен HTTPS и `DEV_BYPASS_AUTH=false`, домен должен совпадать с `PUBLIC_URL` |
| Страница в браузере не грузится из-за `telegram.org` | SDK подключается только внутри Telegram; в обычном браузере он не запрашивается |

---

## Настройка Telegram

1. В [@BotFather](https://t.me/botfather) создайте бота и получите `BOT_TOKEN`.
2. Поставьте публичный HTTPS-домен (Caddy/Nginx) на приложение.
3. В BotFather: `/newapp` → выберите бота → URL `https://calendar.example.com`.
4. Запомните `BOT_USERNAME` и short name приложения (`APP_SHORT_NAME`).
5. Заполните `.env`:

```dotenv
BOT_TOKEN=123456789:AAH...
PUBLIC_URL=https://calendar.example.com
BOT_USERNAME=my_calendar_bot
APP_SHORT_NAME=plans
BOT_MODE=webhook
DEV_BYPASS_AUTH=false
```

6. Запустите `docker compose up -d --build`.

Ссылка на событие будет выглядеть так:

```
https://t.me/my_calendar_bot/plans?startapp=event_<uuid>
```

Для webhook Telegram нужен HTTPS и заголовок
`X-Telegram-Bot-Api-Secret-Token`; секрет берётся из `WEBHOOK_SECRET` или
вычисляется из `BOT_TOKEN`.

---

## Настройка Keycloak

Пример: Keycloak доступен по адресу `https://kc.example.com`, realm — `calendar`.

1. Создайте realm `calendar` (или используйте существующий).
2. Создайте клиент:
   - **Client type**: OpenID Connect;
   - **Client ID**: `calendar-web`;
   - **Valid redirect URIs**:
     `https://calendar.example.com/api/v1/auth/keycloak/callback`;
   - **Web origins**: `https://calendar.example.com`;
   - **Standard flow**: включён;
   - **Direct access grants**: выключены;
   - **PKCE**: S256 (для public-клиента обязателен).
3. Выберите тип клиента:
   - **Public + PKCE** — `KEYCLOAK_CLIENT_SECRET` оставьте пустым;
   - **Confidential** — скопируйте Client secret в `KEYCLOAK_CLIENT_SECRET`.
4. Заполните `.env`:

```dotenv
KEYCLOAK_ENABLED=true
KEYCLOAK_ISSUER=https://kc.example.com/realms/calendar
KEYCLOAK_CLIENT_ID=calendar-web
KEYCLOAK_CLIENT_SECRET=
KEYCLOAK_SCOPES=openid profile email
```

5. Перезапустите приложение.

Бэкенд сам получает OIDC-конфиг из
`KEYCLOAK_ISSUER/.well-known/openid-configuration`, обменивает код на токены,
проверяет `id_token` по JWKS и создаёт пользователя по `sub`. Сервер приложения
должен иметь сетевой доступ к Keycloak.

Если Keycloak отдаёт отдельные адреса для браузера и бэкенда, задайте
`KEYCLOAK_AUTHORIZATION_ENDPOINT`, `KEYCLOAK_TOKEN_ENDPOINT`,
`KEYCLOAK_JWKS_URI` и при необходимости `KEYCLOAK_REDIRECT_URI`.

После включения Keycloak на экране входа в браузере появляется кнопка
**«Войти через email»**. Telegram-вход продолжает работать отдельно.

---

## API

Все методы кроме `/config` требуют cookie-сессию.

| Метод | Путь | Описание |
|---|---|---|
| GET | `/api/v1/config` | dev-режим, имена бота, Keycloak включён/выключен |
| POST | `/api/v1/auth/telegram` | `{ initData }` → cookie-сессия |
| GET | `/api/v1/auth/keycloak/login?next=/` | редирект в Keycloak |
| GET | `/api/v1/auth/keycloak/callback` | OIDC callback → cookie-сессия |
| POST | `/api/v1/auth/logout` | отзыв локальной сессии |
| GET | `/api/v1/me` | текущий пользователь |
| GET/POST | `/api/v1/circles` | список / создание круга |
| PATCH/DELETE | `/api/v1/circles/{id}` | изменение / удаление |
| GET | `/api/v1/events?from&to&circles` | события за период |
| POST | `/api/v1/events` | создание |
| GET/PATCH/DELETE | `/api/v1/events/{id}` | карточка, изменение, удаление |
| POST | `/api/v1/events/{id}/rsvp` | `{ status: going\|maybe\|declined }` |
| GET/POST | `/api/v1/events/{id}/comments` | комментарии |
| POST | `/api/v1/uploads/cover` | multipart-загрузка обложки |
| GET | `/healthz`, `/readyz` | liveness / readiness |
| POST | `/telegram/webhook` | Telegram webhook |

---

## Переменные окружения

| Переменная | По умолчанию | Описание |
|---|---|---|
| `BOT_TOKEN` | — | токен бота; без него бот и Telegram-вход отключены |
| `BOT_MODE` | `polling` | `polling` или `webhook` |
| `PUBLIC_URL` | `http://localhost:8000` | публичный адрес приложения |
| `BOT_USERNAME`, `APP_SHORT_NAME` | — | для ссылок `t.me/...` |
| `WEBHOOK_SECRET` | из `BOT_TOKEN` | секрет webhook |
| `KEYCLOAK_ENABLED` | `false` | включить вход через Keycloak |
| `KEYCLOAK_ISSUER` | — | например `https://kc.example.com/realms/calendar` |
| `KEYCLOAK_CLIENT_ID` | — | client id в Keycloak |
| `KEYCLOAK_CLIENT_SECRET` | — | секрет confidential-клиента; пусто для public+PKCE |
| `KEYCLOAK_SCOPES` | `openid profile email` | scope для OIDC |
| `KEYCLOAK_REDIRECT_URI` | `PUBLIC_URL/api/v1/auth/keycloak/callback` | переопределение callback |
| `KEYCLOAK_*_ENDPOINT`, `KEYCLOAK_JWKS_URI` | discovery | необязательные ручные endpoint'ы |
| `DEV_BYPASS_AUTH` | `true` в `.env.example` | вход без авторизации, только не-HTTPS |
| `DATABASE_URL` | PostgreSQL localhost:5432 | строка SQLAlchemy; в `.env.example` порт 5433 |
| `DB_POOL_SIZE`, `DB_MAX_OVERFLOW`, `DB_POOL_RECYCLE` | 5/10/1800 | пул соединений |
| `REMINDER_INTERVAL_SEC` | 60 | период проверки напоминаний |
| `MAX_COVER_MB` | 5 | лимит обложки |
| `STATIC_DIR`, `UPLOAD_DIR` | `static`, `data/uploads` | пути |
| `APP_PORT`, `BIND_ADDR` | 8000, 127.0.0.1 | порт и адрес в compose |
| `POSTGRES_USER/PASSWORD/DB/PORT` | calendar/calendar/calendar/5432 | БД в compose; в `.env.example` порт 5433 |

### MySQL

Установите `backend/requirements-mysql.txt` и задайте:

```dotenv
DATABASE_URL=mysql+asyncmy://calendar:calendar@localhost:3306/calendar
```

Модели используют переносимые типы SQLAlchemy. Перед продом прогоняйте
интеграционные тесты на обеих СУБД: поведение MySQL и PostgreSQL отличается
в датах, регистре и upsert-сценариях.

---

## Запуск на тестовом сервере для знакомых

Ниже — полный сценарий для одного Linux-сервера с Docker и Nginx.

### 1. DNS и сервер

- Направьте A-запись `calendar.example.com` на IP сервера.
- Откройте наружу только `80` и `443`.
- `8000` (приложение) и `5433` (PostgreSQL) должны оставаться на
  `127.0.0.1` — Nginx проксирует запросы внутри сервера.

### 2. Пакеты

```bash
sudo apt update
sudo apt install -y docker.io docker-compose-v2 nginx certbot
sudo systemctl enable --now docker nginx
```

Если пакет `docker-compose-v2` недоступен в вашем дистрибутиве, поставьте
`docker-compose-plugin` из официального репозитория Docker.

Для сборки фронтенда на сервере нужен Node.js 22.12+:

```bash
curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -
sudo apt install -y nodejs
```

Альтернатива: собирать фронтенд на локальной машине и доставлять готовый образ
через `deploy.sh` — тогда Node на сервере не нужен.

Проверьте:

```bash
docker --version
docker compose version
node --version
```

### 3. Код и настройки

```bash
sudo mkdir -p /opt/calendar
sudo chown "$USER":"$USER" /opt/calendar
git clone <repo-url> /opt/calendar
cd /opt/calendar
cp .env.example .env
nano .env
```

Для тестового сервера `.env` примерно такой:

```dotenv
BOT_TOKEN=123456789:AAH...
BOT_MODE=webhook
PUBLIC_URL=https://calendar.example.com
BOT_USERNAME=my_calendar_bot
APP_SHORT_NAME=plans
DEV_BYPASS_AUTH=false

KEYCLOAK_ENABLED=true
KEYCLOAK_ISSUER=https://kc.example.com/realms/calendar
KEYCLOAK_CLIENT_ID=calendar-web
KEYCLOAK_CLIENT_SECRET=
KEYCLOAK_SCOPES=openid profile email

POSTGRES_USER=calendar
POSTGRES_PASSWORD=change-me-strong-password
POSTGRES_DB=calendar
POSTGRES_PORT=5433
APP_PORT=8000
BIND_ADDR=127.0.0.1
DATABASE_URL=postgresql+asyncpg://calendar:change-me-strong-password@localhost:5433/calendar
```

Если в пароле есть `@`, `:`, `/` и другие спецсимволы — URL-кодируйте его
в `DATABASE_URL` или используйте простой пароль из букв и цифр для теста.
Внутри `docker compose` приложение подключается к БД по имени сервиса `db`,
поэтому `DATABASE_URL` нужен в основном для локального `alembic`.

### 4. Сборка и запуск

```bash
cd /opt/calendar
npm ci
npm run build
docker compose up -d --build
docker compose logs -f calendar
```

При старте контейнер сам выполняет `alembic upgrade head`. Дождитесь:

```text
Application startup complete.
```

Проверка:

```bash
curl -s http://127.0.0.1:8000/healthz
curl -s http://127.0.0.1:8000/readyz
```

### 5. Nginx и HTTPS

Сначала включите HTTP-конфиг для первичной проверки и выпуска сертификата:

```bash
cd /opt/calendar
sudo cp deploy/nginx/calendar-http.conf /etc/nginx/sites-available/calendar
sudo sed -i 's/calendar.example.com/ВАШ_ДОМЕН/g' /etc/nginx/sites-available/calendar
sudo ln -sf /etc/nginx/sites-available/calendar /etc/nginx/sites-enabled/calendar
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl reload nginx
```

Проверьте `http://ВАШ_ДОМЕН/healthz`.

Выпустите сертификат через webroot (Nginx при этом можно не останавливать):

```bash
sudo mkdir -p /var/www/certbot
sudo certbot certonly --webroot -w /var/www/certbot -d ВАШ_ДОМЕН
sudo cp deploy/nginx/calendar.conf /etc/nginx/sites-available/calendar
sudo sed -i 's/calendar.example.com/ВАШ_ДОМЕН/g' /etc/nginx/sites-available/calendar
sudo nginx -t
sudo systemctl reload nginx
```

Проверка:

```bash
curl -I http://ВАШ_ДОМЕН          # 301 → https
curl -s https://ВАШ_ДОМЕН/healthz
curl -s https://ВАШ_ДОМЕН/readyz
```

Продление сертификата уже настроено пакетом certbot (systemd timer).
Проверьте: `sudo certbot renew --dry-run`.

### 6. BotFather и Keycloak

- В BotFather: `/newapp` → URL `https://ВАШ_ДОМЕН`.
- В Keycloak: redirect URI
  `https://ВАШ_ДОМЕН/api/v1/auth/keycloak/callback`,
  web origin `https://ВАШ_ДОМЕН`.
- Перезапустите приложение после изменения `.env`:

```bash
docker compose up -d
```

### 7. Что проверить в браузере и Telegram

1. Открыть `https://ВАШ_ДОМЕН` в браузере → должна быть кнопка
   **«Войти через email»**.
2. Войти тестовым пользователем по email → появится календарь.
3. Создать событие → «Поделиться ссылкой» → ссылка
   `https://t.me/<bot>/<app>?startapp=event_<uuid>`.
4. Открыть ссылку в Telegram → карточка события → RSVP → комментарий.
5. Проверить, что событие появилось в ленте и календаре.
6. Проверить напоминания (или временно уменьшить время события).

### 8. Деплой обновлений

Если образ собирается на локальной машине и передаётся на сервер:

```bash
cp .deploy.example.yml .deploy.yml
# заполните image, remoteDocker.sshHost, pemPath, composePath, serverUrl
./deploy.sh
```

Скрипт собирает фронтенд, собирает образ, передаёт его по SSH и выполняет
`docker compose up -d` на сервере. Миграции Alembic запускаются автоматически.

Если собираете прямо на сервере:

```bash
cd /opt/calendar
git pull
npm ci && npm run build
docker compose up -d --build
```

---

## Что не сделано по исходному ТЗ

### Авторизация и контакты

- ✅ Вход через Telegram `initData`.
- ✅ Вход через Keycloak (OIDC Authorization Code + PKCE) для браузера.
- ✅ Цветные круги «Семья / Друзья / Личное / Работа» и свои круги.
- ❌ Нет списка контактов и распределения друзей по кругам: сейчас круг — это
  категория события, а не группа людей.
- ❌ Приватность «Для круга» не ограничивает доступ участниками круга. Сейчас
  событие с `privacy=circle` доступно автору, участникам и всем, у кого есть
  ссылка (как `link`). Для настоящей приватности нужна таблица участников
  круга и проверка доступа.
- ❌ Нет автоматического связывания Telegram- и Keycloak-аккаунтов одного
  человека. Сейчас это два разных пользователя.
- ❌ Logout очищает локальную сессию, но не завершает SSO-сессию Keycloak.
- ❌ Нет refresh-токенов, ролей Keycloak и разграничения прав по ролям.

### Главный экран и календарь

- ✅ Лента «Сегодня / На неделе / Позже».
- ✅ Месячная сетка с цветными точками.
- ✅ Быстрый выбор месяца и года (пикер с сеткой месяцев и полем года).
- ✅ Фильтр по кругам.
- ❌ Нет автоматических фильтров вроде «скрыть Работу на выходных».
- ❌ Нет поиска, пагинации и просмотра прошедших событий отдельной лентой.
- ❌ Нет real-time обновлений: изменения видны после перезагрузки/повторного
  запроса.

### Создание события

- ✅ Название, дата/время, место текстом или ссылкой, круг, приватность,
  8 пресетов обложки и загрузка своей картинки.
- ❌ Нет редактирования события из UI, хотя `PATCH /api/v1/events/{id}` уже
  реализован.
- ❌ Нет выбора часового пояса пользователя в интерфейсе (сейчас по умолчанию
  `Europe/Moscow`).
- ❌ Нет событий на весь день и повторяющихся событий.
- ❌ Загруженные обложки не сжимаются и не чистятся автоматически.

### Шеринг и RSVP

- ✅ Ссылка `t.me/<bot>/<app>?startapp=event_<id>` при настроенном боте.
- ✅ Без бота ссылка имеет вид `PUBLIC_URL?startapp=event_<id>` и работает в
  браузере в dev-режиме.
- ✅ Карточка события, участники, RSVP «Иду / Думаю / Не смогу».
- ✅ Событие появляется в ленте при статусах `going` и `maybe`.
- ❌ При статусе «Не смогу» событие не попадает в ленту (доступ по ссылке
  сохраняется).
- ❌ Нет live-обновления списка участников у других пользователей.
- ❌ Нет уведомлений автору о новых ответах и комментариях.

### Мини-чат события

- ✅ Комментарии под событием, автор и время.
- ❌ Нет WebSocket/real-time, редактирования и удаления комментариев,
  пагинации и модерации.

### Бот и напоминания

- ✅ `/start`, кнопка Mini App, deep links, напоминания за 24 и 2 часа
  участникам со статусом `going`.
- ❌ Напоминания работают внутри процесса API. При нескольких инстансах нужен
  отдельный worker и распределённый планировщик, иначе возможны гонки.
- ❌ Нет retry/outbox для гарантированной доставки сообщений.
- ❌ Нет уведомлений об изменении или отмене события.
- ❌ Нет Web Push для браузерного режима.

### Продовая инфраструктура

- ❌ Нет rate limiting, CSRF-токенов, капчи и защиты от перебора.
- ❌ Нет автотестов и CI (проверка выполнялась вручную: API, миграции,
  Docker Compose, сборка Svelte, headless Chrome/Firefox).
- ❌ Файлы лежат на локальном диске `/data/uploads`; для нескольких серверов
  нужен S3/MinIO.
- ❌ Нет Redis, фоновой очереди и кэша.
- ❌ Нет аудита действий и админ-панели.
- ❌ Нет ICS-экспорта и синхронизации с внешними календарями.
