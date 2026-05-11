# 📚 Первая Зачётка

> Веб-приложение для продажи восстановленной техники с системой заказов и авторизацией

---

## 📌 О проекте

**Первая Зачётка** — это веб-приложение на Flask, которое позволяет пользователям покупать восстановленную технику (ноутбуки, принтеры и др.), а администраторам — управлять товарами и заказами.

Проект реализует базовую логику маркетплейса:
- каталог товаров
- регистрация и авторизация
- оформление заказов
- админ-панель

---

## 🔥 Актуальность

Проект демонстрирует:
- работу с базой данных (PostgreSQL)
- систему аутентификации (JWT + cookies)
- разграничение прав доступа
- CRUD-операции
- серверный рендеринг (Flask + Jinja2)
- репликацию Master-Slave (PostgreSQL + Docker)

---

## ⚙️ Основной функционал

### 🛍️ Каталог товаров
- Просмотр всех товаров
- Фильтрация по:
  - типу (`type`)
  - состоянию (`condition`)
- Сортировка по цене
- Отображение только активных товаров

---

### 👤 Пользователь

#### Регистрация и вход
- Регистрация с проверкой пароля (минимум 8 символов, заглавная буква, спецсимвол)
- Хеширование пароля через werkzeug
- Авторизация через JWT (cookie)
- Вход по email или username

#### Профиль
- Просмотр профиля по username
- Обновление токена
- Админ видит все профили, пользователь только свой

---

### 🛒 Заказы
- Покупка товара
- Проверка на повторную покупку
- Автоматическое изменение статуса товара (`sold`)
- Просмотр своих заказов со статусами

---

### 🔐 Роли

#### Пользователь
- Просмотр товаров
- Покупка
- Просмотр своих заказов

#### Администратор
- Создание товара
- Редактирование товара
- Удаление товара
- Просмотр всех заказов
- Изменение статуса заказа (В обработке / Оплачен / Доставлен)
- Доступ к dashboard

---

### 📊 Dashboard (админ)

API `/api/dashboard`:
- Статистика заказов по статусам (pie chart)
- Количество товаров по типам (doughnut chart)
- Заказы по датам (line chart)

---

### 🧪 API

- `/api/about` — данные о проекте из JSON
- `/api/hash/<text>` — генерация hash + логирование в БД
- `/api/dashboard` — статистика для графиков
- Supporting сервис (FastAPI, порт 8000):
  - `/api/stats` — общая статистика
  - `/api/users` — список пользователей
  - `/api/orders` — список заказов

---

## 🗄️ Структура базы данных

### `user`
```sql
id SERIAL PRIMARY KEY
username TEXT UNIQUE
email TEXT UNIQUE
password TEXT
is_admin INTEGER
uuid TEXT
created_at TEXT
```

### `item`
```sql
id SERIAL PRIMARY KEY
title TEXT
price INTEGER
type TEXT
condition TEXT
description TEXT
number TEXT
status TEXT
```

### `orders`
```sql
id SERIAL PRIMARY KEY
user_id INTEGER -> REFERENCES user(id)
item_id INTEGER -> REFERENCES item(id)
status TEXT
created_at TEXT
```

### `hash_log`
```sql
id SERIAL PRIMARY KEY
request TEXT
result TEXT
created_at TEXT
```

---

## 🛠️ Технологический стек

- **Backend:** Flask, FastAPI
- **База данных:** PostgreSQL (Docker)
- **Репликация:** Master-Slave (WAL streaming)
- **Аутентификация:** JWT
- **Шаблоны:** Jinja2
- **Безопасность:** werkzeug.security
- **Контейнеризация:** Docker, docker-compose

---

## 🔐 Безопасность

- Хеширование паролей
- Валидация пароля (длина, заглавная буква, спецсимвол)
- JWT с временем жизни 7 дней
- Защищённые маршруты:
  - `@jwt_required`
  - `@admin_required`

---

## 🗃️ Репликация Master-Slave

- **Master** (порт 5432) — все операции записи
- **Slave** (порт 5433) — все операции чтения
- Репликация через WAL (Write-Ahead Log) в режиме `streaming`
- Настроена через `pg_basebackup`

Проверка статуса:
```bash
docker exec -it postgres_master psql -U postgres -c "SELECT * FROM pg_stat_replication;"
```

---

## 🚀 Запуск

```bash
pip install -r requirements.txt
docker-compose up -d
python main.py
```

Supporting сервис:
```bash
cd supporting
python main.py
```

Открыть в браузере:
http://127.0.0.1:5000

---

## 👨‍💻 Автор

- Дутченко Дмитрий — FullStack Developer (main role) + Data Engineer (sub role) — teamlead

---

## 📈 Возможности для развития

- Добавление изображений товаров
- Система отзывов
- Онлайн-оплата
- Email-уведомления
- Автоматический failover (Patroni)
