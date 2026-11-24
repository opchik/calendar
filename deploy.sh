#!/usr/bin/env bash
# Публикует локальный образ на удалённый сервер и перезапускает контейнер.
# Требуется: docker, ssh, python3; на сервере — docker + docker compose v2,
# а также каталог composePath с docker-compose.yml и .env.
# Параметры берутся из .deploy.yml (пример — .deploy.example.yml).
set -euo pipefail

cd "$(dirname "$0")"

command -v docker >/dev/null || { echo "docker не установлен"; exit 1; }
command -v npm >/dev/null || { echo "npm не установлен (нужен для сборки фронтенда)"; exit 1; }
command -v python3 >/dev/null || { echo "python3 не установлен"; exit 1; }
[ -f .deploy.yml ] || { echo "Нет .deploy.yml — скопируйте .deploy.example.yml"; exit 1; }

get() { python3 scripts/yaml_get.py "$1" .deploy.yml; }

IMAGE="$(get image)"
SSH_HOST="$(get remoteDocker.sshHost)"
PEM="$(get remoteDocker.pemPath || true)"
REMOTE_DIR="$(get remoteDocker.composePath)"
SERVER_URL="$(get remoteDocker.serverUrl || true)"

[ -n "$IMAGE" ] && [ -n "$SSH_HOST" ] && [ -n "$REMOTE_DIR" ] || {
  echo "Заполните image, remoteDocker.sshHost и remoteDocker.composePath в .deploy.yml"
  exit 1
}

ssh_cmd=(ssh -o StrictHostKeyChecking=accept-new)
[ -n "$PEM" ] && ssh_cmd+=(-i "$PEM")

echo "→ Сборка фронтенда"
npm ci --no-audit --no-fund
npm run build

echo "→ Сборка образа $IMAGE"
docker build -t "$IMAGE" .

echo "→ Отправка образа на $SSH_HOST"
docker save "$IMAGE" | "${ssh_cmd[@]}" "$SSH_HOST" docker load

echo "→ Перезапуск на сервере ($REMOTE_DIR)"
"${ssh_cmd[@]}" "$SSH_HOST" "cd '$REMOTE_DIR' && docker compose up -d --remove-orphans"

echo "→ Готово${SERVER_URL:+: $SERVER_URL}"
