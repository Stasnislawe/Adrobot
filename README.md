# Keitaro Wrapper

Django-приложение для управления кампаниями в Keitaro через API. Позволяет создавать кампании с двумя потоками (Google Redirect + Offer Stream) и редактировать офферы в потоке с возможностью закрепления весов, мягкого удаления и синхронизации с Keitaro.

## Возможности

- Создание кампании с указанием названия, гео и ID оффера.
- Автоматическое создание двух потоков:
  - Поток с фильтром по стране → редирект на Google.
  - Поток с выбранным оффером (вес 100%).
- Редактирование потока с офферами:
  - Добавление/удаление офферов (мягкое удаление).
  - Закрепление (pin) веса.
  - Пересчёт весов при изменении состава.
  - Синхронизация с Keitaro (Fetch, Push, Cancel).
- Поиск офферов через автокомплит.

## Технологии

- Python 3.12+, Django 5+ (6.0.3)
- SQLite (по умолчанию), можно заменить на PostgreSQL
- Django Templates + jQuery (UI)
- Keitaro API (v1)

## Установка

1. Клонируйте репозиторий:
   ```bash
   git clone https://github.com/yourusername/keitaro-wrapper.git

2. Создайте виртуальное окружение и активируйте его:
   ```bash
   python -m venv venv
   source venv/bin/activate      # Linux/macOS
   venv\Scripts\activate         # Windows

3. Установите зависимости:
   ```bash
   pip install -r requirements.txt

4. Скопируйте .env.example в .env и отредактируйте под свои параметры:
   ```bash
   cp .env.example .env
   ```

5. Примените миграции:
   ```bash
   python manage.py migrate

   
6. Запустите сервер разработки:
   ```bash
   python manage.py runserver

7. Откройте в браузере: http://127.0.0.1:8000/   
