import telebot
from telebot import types
import requests
import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
KINOPOISK_API_KEY = os.getenv("KINOPOISK_API_KEY")

bot = telebot.TeleBot(TOKEN)

# Актуальные жанры для API Кинопоиска
GENRES = {
    "боевик": "боевик",
    "фантастика": "фантастика",
    "драма": "драма",
    "комедия": "комедия",
    "триллер": "триллер",
    "ужасы": "ужасы",
    "детектив": "детектив",
    "фэнтези": "фэнтези",
    "мелодрама": "мелодрама",
    "криминал": "криминал"
}


@bot.message_handler(commands=['start'])
def start(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btn1 = types.KeyboardButton("🎭 Топ по жанру")
    btn2 = types.KeyboardButton("📅 Топ по году")
    btn3 = types.KeyboardButton("🔍 Поиск по названию")
    markup.add(btn1, btn2, btn3)

    bot.send_message(
        message.chat.id,
        "🎬 Выберите действие:\n"
        "• Топ-3 фильмов по жанру\n"
        "• Топ-3 фильмов по году\n"
        "• Поиск по точному названию",
        reply_markup=markup
    )


def search_movies(params):
    url = "https://api.kinopoisk.dev/v1.4/movie"
    headers = {"X-API-KEY": KINOPOISK_API_KEY}
    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        return response.json().get("docs", [])
    except Exception as e:
        print(f"Ошибка API: {e}")
        return []


def show_movie_details(chat_id, movie):
    title = movie.get("name", "Без названия")
    year = movie.get("year", "N/A")
    rating = movie.get("rating", {}).get("imdb", "N/A")

    # Очистка описания от лишних символов
    description = movie.get("description", "")
    if description:
        # Удаляем HTML-теги и лишние пробелы
        import re
        description = re.sub(r'<[^>]+>', '', description)  # Удаляем HTML-теги
        description = re.sub(r'\s+', ' ', description).strip()  # Удаляем лишние пробелы
        description = description[:400]  # Обрезаем длинное описание
    else:
        description = "Описание отсутствует"

    text = (
        f"🎥 <b>{title}</b> ({year})\n"
        f"⭐ Рейтинг IMDB: <b>{rating}</b>\n"
        f"📖 Описание: {description}\n"
        f"🎭 Жанры: {', '.join(g['name'] for g in movie.get('genres', []))}"
    )

    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton(
        "Смотреть на Кинопоиске",
        url=f"https://www.kinopoisk.ru/film/{movie['id']}/"
    ))

    if movie.get("poster", {}).get("url"):
        bot.send_photo(chat_id, movie["poster"]["url"],
                       caption=text,
                       reply_markup=keyboard,
                       parse_mode='HTML')
    else:
        bot.send_message(chat_id, text,
                         reply_markup=keyboard,
                         parse_mode='HTML')


@bot.message_handler(func=lambda message: message.text == "🎭 Топ по жанру")
def ask_genre(message):
    markup = types.InlineKeyboardMarkup(row_width=2)
    for genre in GENRES:
        markup.add(types.InlineKeyboardButton(genre, callback_data=f"genre_{genre}"))
    bot.send_message(message.chat.id, "Выберите жанр для поиска топ-3:", reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data.startswith('genre_'))
def handle_genre(call):
    genre = call.data.split('_')[1]
    bot.answer_callback_query(call.id, f"⌛ Ищем топ в жанре {genre}...")

    params = {
        "genres.name": genre,
        "type": "movie",  # Только фильмы (не сериалы)
        "rating.kp": "7-10",  # Фильтруем по рейтингу Кинопоиска
        "sortField": "votes.kp",  # Сортируем по количеству оценок
        "sortType": "-1",
        "limit": 20  # Берем больше для ручной сортировки
    }

    try:
        response = requests.get(
            "https://api.kinopoisk.dev/v1.4/movie",
            headers={"X-API-KEY": KINOPOISK_API_KEY},
            params=params,
            timeout=15
        )
        response.raise_for_status()
        movies = response.json().get("docs", [])

        # Ручная сортировка по IMDB рейтингу
        movies_sorted = sorted(
            [m for m in movies if m.get("rating", {}).get("imdb")],
            key=lambda x: x["rating"]["imdb"],
            reverse=True
        )[:3]  # Берем топ-3

        if not movies_sorted:
            bot.send_message(call.message.chat.id,
                             f"Фильмы в жанре '{genre}' с рейтингом IMDB не найдены")
            return

        for movie in movies_sorted:
            show_movie_details(call.message.chat.id, movie)

    except Exception as e:
        print(f"API Error: {e}")
        bot.send_message(call.message.chat.id,
                         "Ошибка при поиске. Попробуйте позже.")


@bot.message_handler(func=lambda message: message.text == "📅 Топ по году")
def ask_year(message):
    msg = bot.send_message(
        message.chat.id,
        "Введите год выпуска (от 1900 до 2024):",
        reply_markup=types.ForceReply(selective=False)
    )
    bot.register_next_step_handler(msg, process_year)


def process_year(message):
    try:
        year = int(message.text)
        if 1900 <= year <= 2024:
            # Первый запрос: получаем ID самых популярных фильмов года
            params_popular = {
                "year": year,
                "type": "movie",
                "sortField": "votes.kp",
                "sortType": "-1",
                "limit": 50
            }

            response = requests.get(
                "https://api.kinopoisk.dev/v1.4/movie",
                headers={"X-API-KEY": KINOPOISK_API_KEY},
                params=params_popular,
                timeout=10
            )

            movies = response.json().get("docs", [])

            if not movies:
                bot.send_message(message.chat.id, f"Фильмы {year} года не найдены")
                return

            # Фильтруем фильмы с рейтингом IMDB
            movies_with_rating = [
                m for m in movies
                if m.get("rating") and m["rating"].get("imdb")
            ]

            if not movies_with_rating:
                bot.send_message(
                    message.chat.id,
                    f"Фильмы {year} года есть, но у них нет рейтинга IMDB"
                )
                return

            # Сортируем по рейтингу IMDB и берем топ-3
            top_movies = sorted(
                movies_with_rating,
                key=lambda x: x["rating"]["imdb"],
                reverse=True
            )[:3]

            for movie in top_movies:
                show_movie_details(message.chat.id, movie)

        else:
            bot.send_message(
                message.chat.id,
                "Пожалуйста, введите год между 1900 и 2024"
            )

    except ValueError:
        bot.send_message(
            message.chat.id,
            "Некорректный формат года. Введите число, например: 2010"
        )
    except Exception as e:
        print(f"Ошибка при поиске по году: {e}")
        bot.send_message(
            message.chat.id,
            "Произошла ошибка при поиске. Попробуйте позже."
        )


@bot.message_handler(func=lambda message: message.text == "🔍 Поиск по названию")
def ask_movie_title(message):
    msg = bot.send_message(
        message.chat.id,
        "🎬 Введите название фильма (например: 'Интерстеллар' или 'The Matrix'):",
        reply_markup=types.ForceReply(selective=True)
    )
    bot.register_next_step_handler(msg, process_movie_title)


def process_movie_title(message):
    try:
        search_query = message.text.strip()
        if len(search_query) < 2:
            bot.send_message(message.chat.id, "❌ Слишком короткий запрос. Введите минимум 2 символа")
            return

        # Параметры для расширенного поиска
        search_params = {
            "query": search_query,
            "limit": 5,
            "selectFields": ["name", "alternativeName", "year", "rating", "poster", "id"],
            "type": "movie",
            "isStrict": False
        }

        response = requests.get(
            "https://api.kinopoisk.dev/v1.4/movie/search",
            headers={"X-API-KEY": KINOPOISK_API_KEY},
            params=search_params,
            timeout=15
        )
        response.raise_for_status()

        data = response.json()
        movies = data.get("docs", [])

        if not movies:
            bot.send_message(
                message.chat.id,
                f"❌ Фильмы по запросу '{search_query}' не найдены.\n"
                "Попробуйте:\n"
                "- Уточнить название\n"
                "- Использовать оригинальное название\n"
                "- Проверить орфографию"
            )
            return

        # Формируем список вариантов
        markup = types.InlineKeyboardMarkup()
        for idx, movie in enumerate(movies[:5], 1):  # Ограничиваем 5 результатами
            title = movie.get("name") or movie.get("alternativeName") or "Без названия"
            year = movie.get("year", "")
            btn_text = f"{idx}. {title} ({year})" if year else f"{idx}. {title}"

            markup.add(types.InlineKeyboardButton(
                btn_text,
                callback_data=f"select_{movie['id']}"
            ))

        bot.send_message(
            message.chat.id,
            f"🔍 Найдено {len(movies)} вариантов:",
            reply_markup=markup
        )

    except requests.exceptions.RequestException as e:
        print(f"Ошибка API: {str(e)}")
        bot.send_message(
            message.chat.id,
            "⚠️ Ошибка соединения с сервером. Попробуйте позже."
        )
    except Exception as e:
        print(f"Общая ошибка: {str(e)}")
        bot.send_message(
            message.chat.id,
            "⚠️ Произошла непредвиденная ошибка. Попробуйте другой запрос."
        )


# Обработчик выбора фильма
@bot.callback_query_handler(func=lambda call: call.data.startswith('select_'))
def handle_movie_selection(call):
    try:
        movie_id = call.data.split('_')[1]

        # Получаем полную информацию о фильме
        response = requests.get(
            f"https://api.kinopoisk.dev/v1.4/movie/{movie_id}",
            headers={"X-API-KEY": KINOPOISK_API_KEY},
            timeout=10
        )
        response.raise_for_status()

        movie = response.json()
        show_movie_details(call.message.chat.id, movie)

    except Exception as e:
        print(f"Ошибка загрузки фильма: {str(e)}")
        bot.send_message(
            call.message.chat.id,
            "❌ Не удалось загрузить информацию о фильме"
        )


if __name__ == '__main__':
    print("Бот запущен и готов к работе!")
    bot.infinity_polling(timeout=60)