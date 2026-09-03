# TLOG Analyzer — GitHub Pages + Render

Готова версія без Google Apps Script.

## Структура

- `index.html` — GitHub Pages frontend
- `map3d.js` — lazy 3D
- `backend/main.py` — FastAPI + pymavlink
- `backend/requirements.txt`
- `render.yaml` — Render Blueprint
- `offline/` — локальна версія

## Онлайн схема

GitHub Pages -> Render FastAPI -> JSON -> браузер.

TLOG передається напряму через `multipart/form-data`, без Base64 і без Google Apps Script.

## GitHub Pages

1. Створіть порожній repository.
2. Завантажте в нього ВЕСЬ вміст ZIP.
3. `Settings -> Pages`.
4. Source: `Deploy from a branch`.
5. Branch: `main`.
6. Folder: `/ (root)`.
7. Save.

## Поточний API

Frontend налаштований на:

`https://tlog-api.onrender.com`

Якщо Render має інший URL, змініть у `index.html`:

`const API_BASE_URL = 'https://tlog-api.onrender.com';`

## Render

Для нового backend:
1. Render -> New -> Blueprint.
2. Підключити цей GitHub repository.
3. Render прочитає `render.yaml`.
4. Перевірити `https://<render-url>/health`.

Якщо використовується вже існуючий Render, треба оновити `main.py`,
бо для GitHub Pages додано CORS.

## Offline

Папка `offline`:
1. `SETUP_ONCE.bat` — один раз.
2. `START_OFFLINE.bat` — запуск.

## Що з алгоритмом

Основні алгоритми аналізу взяті з останньої стабільної версії.
Для GitHub backend додано тільки CORS middleware. Це не змінює
розрахунки TLOG.
