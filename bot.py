from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
import random
import string
from datetime import datetime
import sqlite3
import asyncio

# ============= БАЗА ДАННЫХ =============

def init_db():
    conn = sqlite3.connect('spy_bot.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS stats (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        wins INTEGER DEFAULT 0,
        losses INTEGER DEFAULT 0,
        total_games INTEGER DEFAULT 0
    )''')
    conn.commit()
    conn.close()

def add_win(user_id, username):
    conn = sqlite3.connect('spy_bot.db')
    c = conn.cursor()
    c.execute('SELECT * FROM stats WHERE user_id = ?', (user_id,))
    if c.fetchone() is None:
        c.execute('INSERT INTO stats (user_id, username, wins, total_games) VALUES (?, ?, ?, ?)',
                  (user_id, username, 1, 1))
    else:
        c.execute('UPDATE stats SET wins = wins + 1, total_games = total_games + 1 WHERE user_id = ?',
                  (user_id,))
    conn.commit()
    conn.close()

def add_loss(user_id, username):
    conn = sqlite3.connect('spy_bot.db')
    c = conn.cursor()
    c.execute('SELECT * FROM stats WHERE user_id = ?', (user_id,))
    if c.fetchone() is None:
        c.execute('INSERT INTO stats (user_id, username, losses, total_games) VALUES (?, ?, ?, ?)',
                  (user_id, username, 1, 1))
    else:
        c.execute('UPDATE stats SET losses = losses + 1, total_games = total_games + 1 WHERE user_id = ?',
                  (user_id,))
    conn.commit()
    conn.close()

def get_user_stats(user_id):
    conn = sqlite3.connect('spy_bot.db')
    c = conn.cursor()
    c.execute('SELECT * FROM stats WHERE user_id = ?', (user_id,))
    result = c.fetchone()
    conn.close()
    if result:
        return {'user_id': result[0], 'username': result[1], 'wins': result[2], 'losses': result[3], 'total_games': result[4]}
    return None

def get_top_players(limit=10):
    conn = sqlite3.connect('spy_bot.db')
    c = conn.cursor()
    c.execute('SELECT username, wins, total_games FROM stats ORDER BY wins DESC LIMIT ?', (limit,))
    results = c.fetchall()
    conn.close()
    return results

# ============= ТЕМЫ =============

THEMES = {
    "🦸 Супергерои": [
        "Бэтмен", "Человек-паук", "Супермен", "Женщина-кошка", "Тор", 
        "Железный человек", "Капитан Америка", "Черная вдова", "Халк",
        "Соколиный глаз", "Доктор Стрэндж", "Черная Пантера", "Человек-муравей",
        "Ванда Максимова", "Капитан Марвел", "Локи", "Танос", "Росомаха",
    ],
    "🚀 Фантастика": [
        "Космический корабль", "Лаборатория", "Планета", "Робот", "Станция на луне",
        "Портал", "Черная дыра", "Инопланетная колония", "Космическая станция",
        "Параллельный мир", "Машина времени", "Квантовый реактор", "Киборг",
    ],
    "🏢 Места": [
        "Кафе", "Библиотека", "Школа", "Море", "Парк", "Супермаркет", "Кинотеатр",
        "Больница", "Аэропорт", "Вокзал", "Офис", "Банк", "Ресторан", "Отель",
        "Музей", "Театр", "Церковь", "Полиция", "Пожарная", "Спортзал",
    ],
    "🎬 Фильмы": [
        "Матрица", "Аватар", "Интерстеллар", "Война миров", "Назад в будущее",
        "Титаник", "Аватар 2", "Начало", "Дюна", "Звездные войны",
        "Чужой", "Терминатор", "Робокоп", "Пятый элемент", "Касабланка",
    ],
    "🦁 Животные": [
        "Лев", "Тигр", "Медведь", "Волк", "Лиса", "Заяц", "Олень",
        "Орел", "Акула", "Крокодил", "Слон", "Жираф", "Зебра", "Панда",
        "Обезьяна", "Пингвин", "Кит", "Дельфин", "Попугай", "Змея",
    ],
    "💼 Профессии": [
        "Врач", "Учитель", "Полицейский", "Пожарный", "Летчик", "Капитан",
        "Повар", "Актер", "Художник", "Музыкант", "Архитектор", "Инженер",
        "Программист", "Юрист", "Ученый", "Водитель", "Парикмахер",
    ],
    "🍕 Еда": [
        "Пицца", "Бургер", "Суши", "Паста", "Салат", "Хлеб", "Сыр",
        "Колбаса", "Курица", "Рыба", "Говядина", "Макароны", "Рис",
        "Картофель", "Помидоры", "Огурец", "Каша", "Омлет", "Торт",
    ],
    "⚽ Спорт": [
        "Футбол", "Баскетбол", "Теннис", "Волейбол", "Хоккей", "Лыжи",
        "Плавание", "Гимнастика", "Боксинг", "Борьба", "Тяжелая атлетика",
        "Легкая атлетика", "Керлинг", "Фигурное катание", "Серфинг",
    ],
    "🎵 Музыка": [
        "Рок", "Поп", "Джаз", "Классика", "Рэп", "Электро", "Кантри",
        "Блюз", "Фанк", "Диско", "Метал", "Регги", "Фолк", "Опера",
        "Симфония", "Концерт", "Балет", "Гимн", "Колыбельная",
    ],
    "📚 История": [
        "Древний Рим", "Средние века", "Ренессанс", "Наполеон", "Викинги",
        "Пирамиды", "Великая Китайская стена", "Титаник", "Холодная война",
        "Французская революция", "Средневековый замок", "Мумия", "Крестовый поход",
    ],
    "🌍 Природа": [
        "Лес", "Пустыня", "Полярная область", "Вулкан", "Гейзер", "Водопад",
        "Каньон", "Ледник", "Болото", "Остров", "Горы", "Долина", "Озеро",
        "Река", "Пещера", "Скала", "Коралловый риф", "Мангровый лес",
    ],
    "🎲 Игры": [
        "Казино", "Бильярд", "Боулинг", "Шахматы", "Покер", "Дартс",
        "Видеоигра", "Настольная игра", "Лотерея", "Рулетка", "Лабиринт",
        "Кроссворд", "Квиз", "Скраббл", "Домино", "Кубик",
    ],
    "🎉 Праздники": [
        "Новый год", "Рождество", "Пасха", "День рождения", "Свадьба",
        "Хэллоуин", "День Валентина", "День матери", "День отца",
        "Карнавал", "Масленица", "День Благодарения", "День независимости",
    ],
    "🏙️ Города": [
        "Москва", "Санкт-Петербург", "Нью-Йорк", "Лос-Анджелес", "Чикаго",
        "Лондон", "Париж", "Берлин", "Токио", "Пекин", "Шанхай",
        "Индия", "Дели", "Бангкок", "Сингапур", "Гонконг", "Дубай",
    ],
    "❄️ Сезоны": [
        "Зима", "Весна", "Лето", "Осень", "Новый год", "Снег", "Лёд",
        "Метель", "Вьюга", "Мороз", "Оттепель", "Дождь", "Гром", "Молния",
    ],
    "🚗 Техника": [
        "Автомобиль", "Самолет", "Вертолет", "Поезд", "Метро", "Трамвай",
        "Корабль", "Подводная лодка", "Танк", "Ракета", "Спутник",
        "Компьютер", "Смартфон", "Планшет", "Часы", "Телевизор",
    ],
    "🎨 Искусство": [
        "Живопись", "Скульптура", "Архитектура", "Фотография", "Кино",
        "Театр", "Танец", "Музыка", "Литература", "Поэзия", "Комикс",
        "Анимация", "Карикатура", "Портрет", "Натюрморт", "Пейзаж",
    ],
}

# ============= КЛАССЫ =============

class Player:
    def __init__(self, user_id, username):
        self.user_id = user_id
        self.username = username
        self.voted = False

class Lobby:
    def __init__(self, host_id, theme):
        self.code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
        self.host_id = host_id
        self.theme = theme
        self.players = {}
        self.spy_ids = set()
        self.location = None
        self.started = False
        self.voting = False
        self.votes = {}

    def add_player(self, user_id, username):
        if user_id not in self.players:
            self.players[user_id] = Player(user_id, username)
            return True
        return False

    def remove_player(self, user_id):
        if user_id in self.players:
            self.players.pop(user_id)
            return True
        return False

    def start_game(self):
        if len(self.players) < 3:
            return False
        self.location = random.choice(THEMES[self.theme])
        spy_count = max(1, len(self.players) // 5)
        spy_ids = random.sample(list(self.players.keys()), spy_count)
        self.spy_ids = set(spy_ids)
        self.started = True
        return True

    def get_players_list(self):
        players_text = ""
        for i, (uid, player) in enumerate(self.players.items(), 1):
            players_text += f"{i}. {player.username}\n"
        return players_text

    def add_vote(self, voter_id, votee_id):
        self.votes[voter_id] = votee_id
        self.players[voter_id].voted = True

    def get_vote_results(self):
        vote_counts = {}
        for votee_id in self.votes.values():
            vote_counts[votee_id] = vote_counts.get(votee_id, 0) + 1
        if not vote_counts:
            return None, 0
        max_votes = max(vote_counts.values())
        players_with_max = [uid for uid, count in vote_counts.items() if count == max_votes]
        if len(players_with_max) > 1:
            return None, max_votes
        return players_with_max[0], max_votes

# ============= ГЛОБАЛЬНЫЕ =============

LOBBIES = {}

# ============= КОМАНДЫ =============

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = """
🕵️ Добро пожаловать в ШПИОН! 🕵️

/startlobby - Создать лобби
/join <код> - Присоединиться
/startgame <код> - Начать игру
/players <код> - Список игроков
/leave <код> - Выйти
/stats - Твоя статистика
/top - Топ игроков
/help - Справка
"""
    await update.message.reply_text(text)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = """
📖 КАК ИГРАТЬ:

1️⃣ /startlobby - хост создает лобби
2️⃣ Выбирает тему
3️⃣ Отправляет код друзьям
4️⃣ Друзья: /join КОД
5️⃣ Когда 3+ игроков: /startgame КОД
6️⃣ Все получат роль в личном сообщении
7️⃣ Задавайте вопросы друг другу
8️⃣ После обсуждения - голосование
9️⃣ Проголосуйте за шпиона!

🎯 Правила:
- Обычные игроки видят локацию
- Шпион не видит локацию
- Нужно найти и выбрать шпиона
- Если выбрали правильно - обычные выигрывают
- Если нет - шпион выигрывает
"""
    await update.message.reply_text(text)

async def themes_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = "📚 Доступные темы:\n\n"
    for theme, locations in THEMES.items():
        text += f"{theme}:\n{', '.join(locations[:5])}...\n\n"
    await update.message.reply_text(text)

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    stats = get_user_stats(user_id)
    if not stats:
        text = "📊 У тебя пока нет статистики."
    else:
        total = stats['total_games']
        win_rate = (stats['wins'] / total * 100) if total > 0 else 0
        text = f"📊 Твоя статистика:\n\n👤 {stats['username']}\n\n🏆 Всего игр: {total}\n✅ Побед: {stats['wins']}\n❌ Поражений: {stats['losses']}\n📈 Винрейт: {win_rate:.1f}%"
    await update.message.reply_text(text)

async def top_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    top_players = get_top_players(10)
    if not top_players:
        text = "🏆 Топ пуст."
    else:
        text = "🏆 ТОП 10 ИГРОКОВ:\n\n"
        for i, (username, wins, total) in enumerate(top_players, 1):
            win_rate = (wins / total * 100) if total > 0 else 0
            text += f"{i}. {username} - {wins}/{total} ({win_rate:.1f}%)\n"
    await update.message.reply_text(text)

async def start_lobby(update: Update, context: ContextTypes.DEFAULT_TYPE):
    all_themes = list(THEMES.keys())
    keyboard = [[InlineKeyboardButton(theme, callback_data=f"theme_{theme}")] for theme in all_themes]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("🎯 Выберите тему для игры:", reply_markup=reply_markup)

async def theme_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    theme = query.data.split("_", 1)[1]
    lobby = Lobby(host_id=query.from_user.id, theme=theme)
    lobby.add_player(query.from_user.id, query.from_user.username or "Игрок")
    LOBBIES[lobby.code] = lobby
    text = f"✅ Лобби создано!\n\n📌 Код: <b>{lobby.code}</b>\n🎯 Тема: {theme}\n👥 Игроков: 1/10\n\nОтправь код друзьям:\n<code>/join {lobby.code}</code>\n\nЗапусти игру:\n<code>/startgame {lobby.code}</code>"
    await query.edit_message_text(text=text, parse_mode="HTML")

async def join_lobby(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if len(context.args) != 1:
        await update.message.reply_text("❌ /join <код>")
        return
    code = context.args[0].upper()
    if code not in LOBBIES:
        await update.message.reply_text(f"❌ Лобби {code} не найдено.")
        return
    lobby = LOBBIES[code]
    if lobby.started:
        await update.message.reply_text("❌ Игра уже началась.")
        return
    if user.id in lobby.players:
        await update.message.reply_text("❌ Ты уже в лобби.")
        return
    if len(lobby.players) >= 10:
        await update.message.reply_text("❌ Лобби переполнено.")
        return
    lobby.add_player(user.id, user.username or "Игрок")
    text = f"✅ Присоединился!\n\n📌 Код: {code}\n🎯 Тема: {lobby.theme}\n👥 Игроков: {len(lobby.players)}/10"
    await update.message.reply_text(text)

async def players_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 1:
        await update.message.reply_text("❌ /players <код>")
        return
    code = context.args[0].upper()
    if code not in LOBBIES:
        await update.message.reply_text(f"❌ Лобби не найдено.")
        return
    lobby = LOBBIES[code]
    players_list = lobby.get_players_list()
    text = f"👥 Игроки в лобби {code}:\n\n{players_list}Всего: {len(lobby.players)}/10"
    await update.message.reply_text(text)

async def leave_lobby(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if len(context.args) != 1:
        await update.message.reply_text("❌ /leave <код>")
        return
    code = context.args[0].upper()
    if code not in LOBBIES:
        await update.message.reply_text(f"❌ Лобби не найдено.")
        return
    lobby = LOBBIES[code]
    if user.id not in lobby.players:
        await update.message.reply_text("❌ Ты не в лобби.")
        return
    lobby.remove_player(user.id)
    await update.message.reply_text(f"✅ Вышел из лобби {code}")
    if user.id == lobby.host_id or len(lobby.players) == 0:
        if code in LOBBIES:
            del LOBBIES[code]

async def start_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if len(context.args) != 1:
        await update.message.reply_text("❌ /startgame <код>")
        return
    code = context.args[0].upper()
    if code not in LOBBIES:
        await update.message.reply_text(f"❌ Лобби не найдено.")
        return
    lobby = LOBBIES[code]
    if lobby.host_id != user.id:
        await update.message.reply_text("❌ Только хост может начать.")
        return
    if lobby.started:
        await update.message.reply_text("❌ Игра уже запущена.")
        return
    if not lobby.start_game():
        await update.message.reply_text("❌ Минимум 3 игрока.")
        return

    for player_id, player in lobby.players.items():
        if player_id in lobby.spy_ids:
            role_text = "🕵️ ТЫ - ШПИОН!\n\nУзнай локацию, не выдав себя!"
        else:
            role_text = f"🎯 ЛОКАЦИЯ: <b>{lobby.location}</b>\n\nНайди шпиона!"
        try:
            await context.bot.send_message(chat_id=player_id, text=role_text, parse_mode="HTML")
        except Exception as e:
            print(f"Ошибка: {e}")

    await update.message.reply_text(f"✅ ИГРА НАЧАЛАСЬ!\n\n🎯 Локация выбрана\n🕵️ Шпион назначен\n\n📨 Все получили роли!\n\nГолосование через 120 секунд...")

    async def start_voting_task():
        await asyncio.sleep(120)
        await start_voting(context, code)
    
    context.application.create_task(start_voting_task())

async def start_voting(context: ContextTypes.DEFAULT_TYPE, code: str):
    if code not in LOBBIES:
        return
    lobby = LOBBIES[code]
    lobby.voting = True
    keyboard = [[InlineKeyboardButton(f"🗳️ {player.username}", callback_data=f"vote_{code}_{player_id}")] for player_id, player in lobby.players.items()]
    reply_markup = InlineKeyboardMarkup(keyboard)
    text = "⏰ ГОЛОСОВАНИЕ!\n\nКто шпион?"
    for player_id in lobby.players:
        try:
            await context.bot.send_message(chat_id=player_id, text=text, reply_markup=reply_markup)
        except Exception as e:
            print(f"Ошибка: {e}")

async def vote_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    parts = query.data.split("_")
    code = parts[1]
    votee_id = int(parts[2])
    voter_id = query.from_user.id
    
    if code not in LOBBIES:
        await query.edit_message_text("❌ Лобби не найдено.")
        return
    lobby = LOBBIES[code]
    if voter_id not in lobby.players:
        await query.edit_message_text("❌ Ты не в лобби.")
        return
    if votee_id not in lobby.players:
        await query.edit_message_text("❌ Игрок не найден.")
        return
    
    lobby.add_vote(voter_id, votee_id)
    votee_name = lobby.players[votee_id].username
    await query.edit_message_text(f"✅ Голос за {votee_name}")
    
    if len(lobby.votes) == len(lobby.players):
        await finish_voting(context, code)

async def finish_voting(context: ContextTypes.DEFAULT_TYPE, code: str):
    if code not in LOBBIES:
        return
    lobby = LOBBIES[code]
    lobby.game_over = True
    expelled_id, max_votes = lobby.get_vote_results()
    
    if expelled_id is None:
        result_text = "🤝 НИЧЬЯ!\n\nШпион выжил! 🕵️"
        for spy_id in lobby.spy_ids:
            add_win(spy_id, lobby.players[spy_id].username)
        for player_id in lobby.players:
            if player_id not in lobby.spy_ids:
                add_loss(player_id, lobby.players[player_id].username)
    else:
        expelled_name = lobby.players[expelled_id].username
        if expelled_id in lobby.spy_ids:
            result_text = f"🎉 ПОЙМАЛИ ШПИОНА!\n\n{expelled_name} БЫЛ ШПИОН!"
            for player_id in lobby.players:
                if player_id not in lobby.spy_ids:
                    add_win(player_id, lobby.players[player_id].username)
            for spy_id in lobby.spy_ids:
                add_loss(spy_id, lobby.players[spy_id].username)
        else:
            result_text = f"❌ ОШИБКА!\n\n{expelled_name} - обычный игрок!\n\nШпион выжил!"
            for spy_id in lobby.spy_ids:
                add_win(spy_id, lobby.players[spy_id].username)
            for player_id in lobby.players:
                if player_id not in lobby.spy_ids:
                    add_loss(player_id, lobby.players[player_id].username)
    
    for player_id in lobby.players:
        try:
            await context.bot.send_message(chat_id=player_id, text=result_text)
        except:
            pass
    
    if code in LOBBIES:
        del LOBBIES[code]

# ============= MAIN =============

def main():
    init_db()
    print("=" * 50)
    print("✅ Бот запущен!")
    print("=" * 50)
    
    app = ApplicationBuilder().token("8708766321:AAHEK975FqlBqTusXmedyU9UctMWNKKYCRU").build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("themes", themes_command))
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(CommandHandler("top", top_command))
    app.add_handler(CommandHandler("startlobby", start_lobby))
    app.add_handler(CommandHandler("join", join_lobby))
    app.add_handler(CommandHandler("players", players_command))
    app.add_handler(CommandHandler("leave", leave_lobby))
    app.add_handler(CommandHandler("startgame", start_game))
    app.add_handler(CallbackQueryHandler(theme_selected, pattern=r"^theme_"))
    app.add_handler(CallbackQueryHandler(vote_handler, pattern=r"^vote_"))

    app.run_polling()

if __name__ == "__main__":
    main()