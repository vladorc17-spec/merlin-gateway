# Merlin Gateway

Proxy server між Claude і Moodle API.

## Deploy на Railway (безкоштовно)

1. Іди на https://github.com і створи новий репозиторій `merlin-gateway`
2. Завантаж всі файли з цієї папки в репозиторій
3. Іди на https://railway.app → Sign in with GitHub
4. New Project → Deploy from GitHub repo → вибери `merlin-gateway`
5. Railway автоматично задеплоїть сервер
6. Іди в Settings → Domains → Generate Domain
7. Скопіюй URL (типу `merlin-gateway-production.up.railway.app`)

## Змінні середовища (необов'язково)

В Railway → Variables можна встановити:
- `MOODLE_TOKEN` — твій токен (вже вшитий в код)
- `GATEWAY_SECRET` — пароль для захисту (за замовчуванням: `merlin2526`)

## Endpoints

- `GET /` — статус
- `GET /courses?secret=merlin2526` — список курсів
- `GET /assignments?secret=merlin2526` — всі завдання
- `GET /files?secret=merlin2526&course=engleski` — файли курсу
- `GET /grades?secret=merlin2526&course_id=12345` — оцінки
