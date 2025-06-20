# Отчёт по проектной практике
**Тема:** «Автоматизация внутренних бизнес-процессов университета. 2ГИС»
**Студент:** Ларионова Мария Ильинична 
**Период:** 03.02.2025 - 24.05.2025  
**Руководитель:** Рябчикова Анна Валерьевна 

##  Цели и задачи
1. Разработка Telegram-бота для поиска фильмов на Python
2. Создание презентационного сайта проектной деятельности

##  Технологический стек
**Backend:**
- Python 3.10
- Библиотеки: python-telegram-bot, requests, python-dotenv, sqlite3, pydantic

**Frontend:**
- HTML5, CSS3, JS


##  Ход работы
### Этап 1: Анализ (03.2025)
- Проведено интервью с представителями компании-партнёра
- Составлены планы и измерены планы корпусов БС с помощью пожарных планов
- Составлены планы и измерены планы корпусов ПК с помощью пожарных планов
- Составлены планы и измерены планы корпусов Пр с помощью пожарных планов

### Этап 2: Разработка (03-04.2025)
**Telegram-бот:**
- Добавлена функция поиска по названию
```python
    @bot.message_handler(func=lambda message: message.text == "🔍 Поиск по названию")
def ask_movie_title(message):
    msg = bot.send_message(
        message.chat.id,
        "🎬 Введите название фильма (например: 'Интерстеллар' или 'The Matrix'):",
        reply_markup=types.ForceReply(selective=True)
    )
    bot.register_next_step_handler(msg, process_movie_title)
