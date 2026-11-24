#!/usr/bin/env python3
"""Минимальный YAML-ридер для deploy.sh.

Поддерживает верхний уровень и один уровень вложенности (section.key).
Значения — строки без кавычек.

    python3 scripts/yaml_get.py remoteDocker.sshHost .deploy.yml
"""

from __future__ import annotations

import sys
from pathlib import Path


def clean(value: str) -> str:
    return value.strip().strip("\"'")


def main() -> None:
    if len(sys.argv) != 3:
        sys.exit("Использование: yaml_get.py <section.key|key> <file>")

    key_path, file = sys.argv[1], sys.argv[2]
    keys = key_path.split(".")
    section = ""

    for line in Path(file).read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or ":" not in stripped:
            continue

        key, _, value = stripped.partition(":")
        key = key.strip()
        indented = line[:1].isspace()

        if not indented:
            section = key
            if len(keys) == 1 and key == keys[0]:
                print(clean(value))
                return
            continue

        if len(keys) == 2 and section == keys[0] and key == keys[1]:
            print(clean(value))
            return

    sys.exit(f'Не найден ключ "{key_path}" в {file}')


if __name__ == "__main__":
    main()
