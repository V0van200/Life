# Как подключать интерфейс

Базовый URL API задаётся конфигурацией клиента. Все бизнес-маршруты требуют `Authorization: Bearer <token>`. Получить токен через POST `/api/v1/auth/login` с username/password. Токен не хранить в репозитории и не выводить в логи. Предпочтительно хранить в памяти приложения; интеграция с HttpOnly cookie пока не реализована.

## Основные маршруты

| Метод и путь | Действие |
|---|---|
| GET /health | Проверка доступности БД |
| POST /api/v1/auth/login | Вход |
| POST /api/v1/auth/logout | Отзыв текущей сессии |
| GET /api/v1/modules | Возможности ядра |
| GET, POST /api/v1/records | Список / создание объектов |
| GET, PUT /api/v1/records/{id} | Просмотр / обновление с version |
| POST /api/v1/services/{id}/deactivate | Остановить формирование новых платежей |
| GET, POST /api/v1/links | Связи объектов |
| GET, POST /api/v1/accounts | Балансы / создание счёта |
| GET, POST /api/v1/operations | История / запись операции |
| POST /api/v1/obligations/generate?start=...&end=... | Сформировать график |
| GET /api/v1/obligations?start=...&end=... | Посмотреть платежи |
| POST /api/v1/obligations/{id}/pay | Подтвердить оплату |
| GET /api/v1/calendar?start=...&end=... | Общая временная выборка |
| GET /api/v1/courses/{id}/progress | Прогресс курса |
| GET /api/v1/finance/summary?start=...&end=... | Остатки, потоки и неоплаченные обязательства отдельно по валютам |
| GET /api/v1/audit | История изменений |
| GET /api/v1/export/operations.csv | Экспорт для Excel |

## Создание услуги

```json
{
  "kind": "service",
  "title": "OneDash — игровой сервер",
  "data": {
    "category": "server",
    "provider": "OneDash",
    "details": {"purpose": "Тестовый пример, заменить своими данными"},
    "amount_minor": 110000,
    "currency": "RUB",
    "first_due": "2026-11-01",
    "repeat": "days",
    "interval": 30,
    "provider_balance_minor": null
  }
}
```

Это пример, не настоящая стоимость или инфраструктура пользователя. После создания вызвать generate на нужный месяц; прочитать obligations; после реального платежа вызвать pay с account_id и occurred_at. Нельзя одновременно добавлять ручной расход и подтверждать то же обязательство: это две разные команды и разные ключи.

## Изменение задачи

PUT требует текущую version и полное содержимое data. При 409 перечитать запись и показать пользователю конфликт; не подменять версию автоматически. Поля типа задаются схемами `backend/life/schemas.py`; дополнительные неизвестные поля отклоняются. Все типы представлены в описании ниже; OpenAPI описывает оболочку records, а детали data проверяются на сервере по kind.

| kind | Поля data |
|---|---|
| project | status: idea/active/paused/done; description |
| task | status: todo/doing/done; due: YYYY-MM-DD или null; planned_minutes |
| event | start, end: ISO с offset; icon |
| service | provider, category, details, amount_minor, currency, first_due, repeat, interval, active, provider_balance_minor |
| course | steps: уникальные названия шагов |
| study | course_id, step, start, end, evidence |
| note | text |
| custom_type | fields: словарь имя → text/integer/boolean/date |
| custom | type_id, values |

Денежная операция требует key, kind, account_id, amount_minor, occurred_at, title; optional target_id только для transfer, optional record_id для связи. После обрыва связи повторять запрос с исходным key и неизменённым телом. Для нового пользовательского действия создавать новый UUID key. Не считать 409 успехом без чтения результата и проверки причины.

Списки records/operations/audit поддерживают limit 1..200 и offset. Текущая пагинация не является стабильным снимком при конкурентном редактировании. Диапазоны дат start/end включительны, максимум 366 дней разницы.
