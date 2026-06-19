# GameDAG — мини-приложение Telegram

Все 4 игры (Шпион, Мафия, Крокодил, Правда или Действие) работают внутри Telegram
как Web App (мини-приложение), в режиме «с одного устройства» (pass-and-play).

## Состав
- `index.html`, `style.css`, `app.js`, `data.js` — само мини-приложение (чистый фронтенд, без бэкенда).
- `bot_miniapp.py` — ваш бот с кнопками, которые открывают это мини-приложение.

## Быстрый локальный тест

### 1. Запустить мини-приложение локально
```bash
cd miniapp
python3 -m http.server 8077
```
Можно сразу открыть в браузере: http://localhost:8077/  (все игры работают и без Telegram).
Дип-линки: `?game=spy`, `?game=mafia`, `?game=crocodile`, `?game=tod`.

### 2. Получить HTTPS-ссылку (Telegram требует HTTPS для Web App)
Самый простой способ — туннель:
```bash
# вариант А: cloudflared
cloudflared tunnel --url http://localhost:8077
# вариант Б: ngrok
ngrok http 8077
```
Скопируйте выданную https://...-ссылку.

### 3. Запустить бот
```bash
export TELEGRAM_BOT_TOKEN="ваш_токен"
export WEBAPP_URL="https://ваш-туннель.trycloudflare.com"
pip install python-telegram-bot
python3 bot_miniapp.py
```
Откройте бота в Telegram, отправьте /start — кнопки откроют игры в мини-приложении.

## Потом (продакшен)
Выложите папку `miniapp` на любой статический HTTPS-хостинг (GitHub Pages, Netlify, Vercel,
Сloudflare Pages) и подставьте его адрес в `WEBAPP_URL`. Бэкенд не нужен.

## Примечания
- Старые чат-команды и сетевые режимы в боте остались нетронутыми — изменён только /start.
- Весь игровой контент (темы, слова, вопросы, роли) взят из вашего бота.
