# Разворачивание coffee_bot на сервере (Ubuntu + systemd)

Предполагается свежий VPS на Ubuntu 22.04/24.04, доступ по SSH под root (или sudo-пользователем).

## 1. Подготовка сервера

```bash
apt update && apt upgrade -y
apt install -y python3 python3-venv python3-pip git
```

## 2. Создать отдельного пользователя для бота (не root)

```bash
adduser --disabled-password --gecos "" botuser
```

## 3. Скопировать проект на сервер

С локальной машины (замени `SERVER_IP`):

```bash
scp -r D:/Programming/DevSC/coffee_bot botuser@SERVER_IP:/home/botuser/coffee_bot
```

Либо через `git clone`, если проект уже в репозитории.

**Важно**: убедись, что скопировалась актуальная `database/inventory.db` (с уже импортированными 263 товарами и `product_info`) — повторный импорт на сервере не нужен.

## 4. Установить зависимости

```bash
su - botuser
cd /home/botuser/coffee_bot
python3 -m venv venv
venv/bin/pip install -r requirements.txt
```

## 5. Проверить `.env`

Файл `.env` должен быть на сервере рядом с `main.py` (не в `.env.example`) и содержать реальный `BOT_TOKEN` и `ALLOWED_USER_IDS`. Если копировался через `scp -r`, он уже на месте — проверь:

```bash
cat /home/botuser/coffee_bot/.env
```

## 6. Пробный ручной запуск (проверить, что всё стартует)

```bash
cd /home/botuser/coffee_bot
venv/bin/python main.py
```

Если бот отвечает в Telegram — Ctrl+C, переходим к systemd.

## 7. Установить systemd-сервис

От root/sudo:

```bash
cp /home/botuser/coffee_bot/deploy/coffee-bot.service /etc/systemd/system/coffee-bot.service
systemctl daemon-reload
systemctl enable coffee-bot
systemctl start coffee-bot
```

## 8. Проверка статуса и логов

```bash
systemctl status coffee-bot
journalctl -u coffee-bot -f
```

`Restart=on-failure` в unit-файле перезапустит бота автоматически, если процесс упадёт. `enable` гарантирует автозапуск после перезагрузки сервера.

## Обновление бота в будущем

```bash
systemctl stop coffee-bot
# обновить файлы (scp/git pull)
systemctl start coffee-bot
```
