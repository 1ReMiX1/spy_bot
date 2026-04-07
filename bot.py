
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
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
}


# ============= КЛАССЫ ДЛЯ ШПИОНА =============

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


# ============= КЛАССЫ ДЛЯ МАФИИ =============

class MafiaPlayer:
    def __init__(self, user_id, username):
        self.user_id = user_id
        self.username = username
        self.role = None
        self.alive = True
        self.voted = False
        self.night_action_done = False

class MafiaLobby:
    def __init__(self, host_id):
        self.code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
        self.host_id = host_id
        self.players = {}
        self.mafia_ids = set()
        self.komissar_id = None
        self.doctor_id = None
        self.started = False
        self.phase = "waiting"
        self.day_number = 0
        self.votes = {}
        self.night_actions = {}
        self.last_killed = None
        self.last_saved = None
        self.last_checked = None
        self.game_type = "mafia"

    def add_player(self, user_id, username):
        if user_id not in self.players and len(self.players) < 10:
            self.players[user_id] = MafiaPlayer(user_id, username)
            return True
        return False

    def remove_player(self, user_id):
        if user_id in self.players:
            self.players.pop(user_id)
            return True
        return False

    def get_alive_players(self):
        return {uid: p for uid, p in self.players.items() if p.alive}

    def get_alive_civilians(self):
        return {uid: p for uid, p in self.get_alive_players().items() 
                if uid not in self.mafia_ids}

    def get_alive_mafia(self):
        return {uid: p for uid, p in self.get_alive_players().items() 
                if uid in self.mafia_ids}

    def start_game(self):
        if len(self.players) < 4:
            return False
        
        player_count = len(self.players)
        player_ids = list(self.players.keys())
        
        if player_count >= 7:
            mafia_count = 2
        else:
            mafia_count = 1
        
        mafia_ids = random.sample(player_ids, mafia_count)
        self.mafia_ids = set(mafia_ids)
        for mid in mafia_ids:
            self.players[mid].role = "мафия"
        
        remaining = [pid for pid in player_ids if pid not in mafia_ids]
        
        if player_count >= 5 and remaining:
            self.komissar_id = random.choice(remaining)
            self.players[self.komissar_id].role = "комиссар"
            remaining.remove(self.komissar_id)
        
        if player_count >= 6 and remaining:
            self.doctor_id = random.choice(remaining)
            self.players[self.doctor_id].role = "доктор"
            remaining.remove(self.doctor_id)
        
        for pid in remaining:
            self.players[pid].role = "мирный"
        
        self.started = True
        self.phase = "night"
        self.day_number = 1
        return True

    def get_players_list(self, show_status=False):
        players_text = ""
        for i, (uid, player) in enumerate(self.players.items(), 1):
            status = ""
            if show_status:
                status = " 💀" if not player.alive else " ✅"
            players_text += f"{i}. {player.username}{status}\n"
        return players_text

    def add_night_action(self, player_id, target_id):
        self.night_actions[player_id] = target_id
        self.players[player_id].night_action_done = True

    def check_night_actions_complete(self):
        alive_mafia = self.get_alive_mafia()
        if alive_mafia and not any(mid in self.night_actions for mid in alive_mafia):
            return False
        
        if self.doctor_id and self.players[self.doctor_id].alive:
            if self.doctor_id not in self.night_actions:
                return False
        
        if self.komissar_id and self.players[self.komissar_id].alive:
            if self.komissar_id not in self.night_actions:
                return False
        
        return True

    def process_night(self):
        mafia_target = None
        for mid in self.get_alive_mafia():
            if mid in self.night_actions:
                mafia_target = self.night_actions[mid]
                break
        
        doctor_target = None
        if self.doctor_id and self.doctor_id in self.night_actions:
            doctor_target = self.night_actions[self.doctor_id]
        
        komissar_check = None
        if self.komissar_id and self.komissar_id in self.night_actions:
            komissar_check = self.night_actions[self.komissar_id]
            self.last_checked = komissar_check
        
        self.last_killed = None
        self.last_saved = None
        
        if mafia_target:
            ifself.votes[voter_id] = votee_id
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

    def check_win_condition(self):
        alive_mafia = len(self.get_alive_mafia())
        alive_civilians = len(self.get_alive_civilians())
        
        if alive_mafia == 0:
            return "civilians"
        if alive_mafia >= alive_civilians:
            return "mafia"
        return None


# ============= ГЛОБАЛЬНЫЕ =============

LOBBIES = {}
MAFIA_LOBBIES = {}

# ============= КОМАНДЫ =============

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🕵️ ШПИОН", callback_data="game_spy")],
        [InlineKeyboardButton("🔪 МАФИЯ", callback_data="game_mafia")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = "👋 Добро пожаловать в GameDAG!\n\nВыбери игру:"
    await update.message.reply_text(text, reply_markup=reply_markup)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = """
📖 КАК ИГРАТЬ:

🕵️ ШПИОН:
1. Выбери игру и тему
2. Отправь код друзьям
3. /startgame КОД
4. Обсуждайте и голосуйте!

🔪 МАФИЯ:
1. Создай лобби мафии
2. /joinmafia КОД
3. /startmafia КОД
4. Ночью действуют роли
5. Днём город голосует

/stats - Статистика
/top - Топ игроков
"""
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

async def spy_command(query):
    all_themes = list(THEMES.keys())
    keyboard = [[InlineKeyboardButton(theme, callback_data=f"theme_{theme}")] for theme in all_themes]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text("🎯 ШПИОН - Выберите тему:", reply_markup=reply_markup)

async def mafia_command(query):
    user_id = query.from_user.id
    username = query.from_user.username or "Игрок"
    
    lobby = MafiaLobby(host_id=user_id)
    lobby.add_player(user_id, username)
    MAFIA_LOBBIES[lobby.code] = lobby
    
    text = f"✅ Лобби МАФИИ создано!\n\n📌 Код: <b>{lobby.code}</b>\n👥 Игроков: 1/10\n\n📍 Минимум 4 игрока\n\nОтправь код друзьям:\n<code>/joinmafia {lobby.code}</code>\n\nЗапусти игру:\n<code>/startmafia {lobby.code}</code>"
    await query.edit_message_text(text=text, parse_mode="HTML")

async def game_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    game = query.data.split("_")[1]
    
    if game == "spy":
        await spy_command(query)
    else:
        await mafia_command(query)

async def theme_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    theme = query.data.split("_", 1)[1]
    lobby = Lobby(host_id=query.from_user.id, theme=theme)
    lobby.add_player(query.from_user.id, query.from_user.username or "Игрок")
    LOBBIES[lobby.code] = lobby
    text = f"✅ Лобби создано!\n\n📌 Код: <b>{lobby.code}</b>\n🎯 Тема: {theme}\n👥 Игроков: 1/10\n\nОтправь код друзьям:\n<code>/join {lobby.code}</code>\n\nЗапусти игру:\n<code>/startgame {lobby.code}</code>"
    await query.edit_message_text(text=text, parse_mode="HTML")


# ============= КОМАНДЫ ДЛЯ ШПИОНА =============

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

    await update.message.reply_text(f"✅ ИГРА НАЧАЛАСЬ!\n\n📨 Все получили роли!\n\nГолосование через 120 секунд...")

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

# ============= КОМАНДЫ ДЛЯ МАФИИ =============

async def join_mafia(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if len(context.args) != 1:
        await update.message.reply_text("❌ /joinmafia <код>")
        return
    code = context.args[0].upper()
    if code not in MAFIA_LOBBIES:
        await update.message.reply_text(f"❌ Лобби {code} не найдено.")
        return
    lobby = MAFIA_LOBBIES[code]
    if lobby.started:
        await update.message.reply_text("❌ Игра уже началась.")
        return
    if user.id in lobby.players:
        await update.message.reply_text("❌ Ты уже в лобби.")
        return
    if not lobby.add_player(user.id, user.username or "Игрок"):
        await update.message.reply_text("❌ Лобби переполнено.")
        return
    
    text = f"✅ Присоединился к мафии!\n\n📌 Код: {code}\n👥 Игроков: {len(lobby.players)}/10"
    await update.message.reply_text(text)

async def mafia_players(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 1:
        await update.message.reply_text("❌ /mafiapl <код>")
        return
    code = context.args[0].upper()
    if code not in MAFIA_LOBBIES:
        await update.message.reply_text(f"❌ Лобби не найдено.")
        return
    lobby = MAFIA_LOBBIES[code]
    players_list = lobby.get_players_list(show_status=lobby.started)
    status_text = f"Фаза: {lobby.phase}\n" if lobby.started else ""
    text = f"👥 Игроки в лобби {code}:\n\n{players_list}{status_text}Всего: {len(lobby.players)}/10"
    await update.message.reply_text(text)

async def leave_mafia(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if len(context.args) != 1:
        await update.message.reply_text("❌ /leavemafia <код>")
        return
    code = context.args[0].upper()
    if code not in MAFIA_LOBBIES:
        await update.message.reply_text(f"❌ Лобби не найдено.")
        return
    lobby = MAFIA_LOBBIES[code]
    if user.id not in lobby.players:
        await update.message.reply_text("❌ Ты не в лобби.")
        return
    lobby.remove_player(user.id)
    await update.message.reply_text(f"✅ Вышел из лобби {code}")
    if user.id == lobby.host_id or len(lobby.players) == 0:
        if code in MAFIA_LOBBIES:
            del MAFIA_LOBBIES[code]

async def start_mafia_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if len(context.args) != 1:
        await update.message.reply_text("❌ /startmafia <код>")
        return
    code = context.args[0].upper()
    if code not in MAFIA_LOBBIES:
        await update.message.reply_text(f"❌ Лобби не найдено.")
        return
    lobby = MAFIA_LOBBIES[code]
    if lobby.host_id != user.id:
        await update.message.reply_text("❌ Только хост может начать.")
        return
    if lobby.started:
        await update.message.reply_text("❌ Игра уже запущена.")
        return
    if not lobby.start_game():
        await update.message.reply_text("❌ Минимум 4 игрока.")
        return

    for player_id, player in lobby.players.items():
        role_emoji = {"мафия": "🔪", "комиссар": "👮", "доктор": "👨‍⚕️", "мирный": "👤"}
        role_name = player.role.upper()
        emoji = role_emoji.get(player.role, "👤")
        
        role_text = f"{emoji} ТВОЯ РОЛЬ: <b>{role_name}</b>\n\n"
        
        if player.role == "мафия":
            mafia_partners = [lobby.players[mid].username for mid in lobby.mafia_ids if mid != player_id]
            if mafia_partners:
                role_text += f"Твои напарники: {', '.join(mafia_partners)}\n\n"
            role_text += "Ночью убиваешь мирных жителей."
        elif player.role == "комиссар":
            role_text += "Ночью проверяешь игроков."
        elif player.role == "доктор":
            role_text += "Ночью лечишь игроков."
        else:
            role_text += "Днём помогай найти мафию!"
        
        try:
            await context.bot.send_message(chat_id=player_id, text=role_text, parse_mode="HTML")
        except Exception as e:
            print(f"Ошибка: {e}")

    await update.message.reply_text(f"✅ МАФИЯ НАЧАЛАСЬ!\n\n🌙 Ночь {lobby.day_number}\n📨 Все получили роли!")
    
    await asyncio.sleep(3)
    await start_night_phase(context, code)

async def start_night_phase(context: ContextTypes.DEFAULT_TYPE, code: str):
    if code not in MAFIA_LOBBIES:
        return
    lobby = MAFIA_LOBBIES[code]
    
    for mafia_id in lobby.get_alive_mafia():
        alive_targets = [p for pid, p in lobby.get_alive_players().items() if pid not in lobby.mafia_ids]
        if not alive_targets:
            continue
        
        keyboard = [[InlineKeyboardButton(f"🔪 {p.username}", callback_data=f"mafia_kill_{code}_{p.user_id}")] 
                    for p in alive_targets]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        try:
            await context.bot.send_message(
                chat_id=mafia_id,
                text="🌙 НОЧЬ - Кого убить?",
                reply_markup=reply_markup
            )
        except:
            pass
    
    if lobby.doctor_id and lobby.players[lobby.doctor_id].alive:
        alive_targets = list(lobby.get_alive_players().values())
        keyboard = [[InlineKeyboardButton(f"💊 {p.username}", callback_data=f"mafia_heal_{code}_{p.user_id}")] 
                    for p in alive_targets]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        try:
            await context.bot.send_message(
                chat_id=lobby.doctor_id,
                text="🌙 НОЧЬ - Кого лечить?",
                reply_markup=reply_markup
            )
        except:
            pass
    
    if lobby.komissar_id and lobby.players[lobby.komissar_id].alive:
        alive_targets = [p for pid, p in lobby.get_alive_players().items() if pid != lobby.komissar_id]
        keyboard = [[InlineKeyboardButton(f"🔍 {p.username}", callback_data=f"mafia_check_{code}_{p.user_id}")] 
                    for p in alive_targets]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        try:
            await context.bot.send_message(
                chat_id=lobby.komissar_id,
                text="🌙 НОЧЬ - Кого проверить?",
                reply_markup=reply_markup
            )
        except:
            pass
    
    async def check_night_complete():
        for _ in range(60):
            await asyncio.sleep(2)
            if code not in MAFIA_LOBBIES:
                return
            if lobby.check_night_actions_complete():
                await end_night_phase(context, code)
                return
        
        if code in MAFIA_LOBBIES:
            await end_night_phase(context, code)
    
    context.application.create_task(check_night_complete())

async def mafia_night_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    parts = query.data.split("_")
    action = parts[1]
    code = parts[2]
    target_id = int(parts[3])
    player_id = query.from_user.id
    
    if code not in MAFIA_LOBBIES:
        await query.edit_message_text("❌ Игра не найдена.")
        return
    
    lobby = MAFIA_LOBBIES[code]
    
    if player_id not in lobby.players or not lobby.players[player_id].alive:
        await query.edit_message_text("❌ Ты не можешь действовать.")
        return
    
    target_name = lobby.players[target_id].username
    
    if action == "kill":
        if player_id not in lobby.mafia_ids:
            await query.edit_message_text("❌ Ты не мафия.")
            return
        lobby.add_night_action(player_id, target_id)
        await query.edit_message_text(f"🔪 Цель выбрана: {target_name}")
    
    elif action == "heal":
        if player_id != lobby.doctor_id:
            await query.edit_message_text("❌ Ты не доктор.")
            return
        lobby.add_night_action(player_id, target_id)
        await query.edit_message_text(f"💊 Лечишь: {target_name}")
    
    elif action == "check":
        if player_id != lobby.komissar_id:
            await query.edit_message_text("❌ Ты не комиссар.")
            return
        lobby.add_night_action(player_id, target_id)
        if target_id in lobby.mafia_ids:
            result = "🔴 МАФИЯ!"
        else:
            result = "🟢 Мирный житель"
        await query.edit_message_text(f"🔍 Проверка {target_name}:\n{result}")

async def end_night_phase(context: ContextTypes.DEFAULT_TYPE, code: str):
    if code not in MAFIA_LOBBIES:
        return
    
    lobby = MAFIA_LOBBIES[code]
    lobby.process_night()
    
    night_report = f"☀️ УТРО НАСТУПИЛО!\n\nДень {lobby.day_number}\n\n"
    
    if lobby.last_killed:
        killed_name = lobby.players[lobby.last_killed].username
        night_report += f"💀 Ночью погиб: {killed_name}\n"
    elif lobby.last_saved:
        night_report += f"💊 Доктор спас жителя!\n"
    else:
        night_report += f"✅ Ночь прошла спокойно\n"
    
    for player_id in lobby.players:
        try:
            await context.bot.send_message(chat_id=player_id, text=night_report)
        except:
            pass
    
    win_condition = lobby.check_win_condition()
    if win_condition:
        await end_mafia_game(context, code, win_condition)
        return
    
    await asyncio.sleep(3)
    await start_day_voting(context, code)

async def start_day_voting(context: ContextTypes.DEFAULT_TYPE, code: str):
    if code not in MAFIA_LOBBIES:
        return
    
    lobby = MAFIA_LOBBIES[code]
    lobby.votes = {}
    for player in lobby.players.values():
        player.voted = False
    
    alive_players = list(lobby.get_alive_players().values())
    keyboard = [[InlineKeyboardButton(f"🗳️ {p.username}", callback_data=f"mafia_vote_{code}_{p.user_id}")] 
                for p in alive_players]
    keyboard.append([InlineKeyboardButton("⏭️ Пропустить день", callback_data=f"mafia_vote_{code}_skip")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = "☀️ ДНЕВНОЕ ГОЛОСОВАНИЕ!\n\nКого выгнать из города?"
    
    for player_id, player in lobby.get_alive_players().items():
        try:
            await context.bot.send_message(chat_id=player_id, text=text, reply_markup=reply_markup)
        except:
            pass
    
    async def check_votes_complete():
        for _ in range(60):
            await asyncio.sleep(2)
            if code not in MAFIA_LOBBIES:
                return
            alive_count = len(lobby.get_alive_players())
            if len(lobby.votes) >= alive_count:
                await end_day_voting(context, code)
                return
        
        if code in MAFIA_LOBBIES:
            await end_day_voting(context, code)
    
    context.application.create_task(check_votes_complete())

async def mafia_day_vote(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    parts = query.data.split("_")
    code = parts[2]
    target = parts[3]
    voter_id = query.from_user.id
    
    if code not in MAFIA_LOBBIES:
        await query.edit_message_text("❌ Игра не найдена.")
        return
    
    lobby = MAFIA_LOBBIES[code]
    
    if voter_id not in lobby.players or not lobby.players[voter_id].alive:
        await query.edit_message_text("❌ Ты не можешь голосовать.")
        return
    
    if target == "skip":
        lobby.votes[voter_id] = None
        await query.edit_message_text("⏭️ Пропускаешь голосование")
    else:
        target_id = int(target)
        if target_id not in lobby.players or not lobby.players[target_id].alive:
            await query.edit_message_text("❌ Игрок не найден.")
            return
        
        lobby.add_vote(voter_id, target_id)
        target_name = lobby.players[target_id].username
        await query.edit_message_text(f"✅ Голос за: {target_name}")

async def end_day_voting(context: ContextTypes.DEFAULT_TYPE, code: str):
    if code not in MAFIA_LOBBIES:
        return
    
    lobby = MAFIA_LOBBIES[code]
    expelled_id, max_votes = lobby.get_vote_results()
    
    day_result = f"📊 РЕЗУЛЬТАТЫ ГОЛОСОВАНИЯ:\n\n"
    
    if expelled_id is None or expelled_id not in lobby.players:
        day_result += "🤝 Город не смог принять решение!\n"
    else:
        expelled_name = lobby.players[expelled_id].username
        expelled_role = lobby.players[expelled_id].role
        lobby.players[expelled_id].alive = False
        
        role_emoji = {"мафия": "🔪", "комиссар": "👮", "доктор": "👨‍⚕️", "мирный": "👤"}
        emoji = role_emoji.get(expelled_role, "👤")
        
        day_result += f"💀 Изгнан: {expelled_name}\n"
        day_result += f"{emoji} Роль: {expelled_role.upper()}\n"
    
    for player_id in lobby.players:
        try:
            await context.bot.send_message(chat_id=player_id, text=day_result)
        except:
            pass
    
    win_condition = lobby.check_win_condition()
    if win_condition:
        await end_mafia_game(context, code, win_condition)
        return
    
    lobby.day_number += 1
    lobby.phase = "night"
    
    await asyncio.sleep(3)
    
    for player_id in lobby.players:
        try:
            await context.bot.send_message(
                chat_id=player_id,
                text=f"🌙 Наступает ночь {lobby.day_number}..."
            )
        except:
            pass
    
    await asyncio.sleep(2)
    await start_night_phase(context, code)

async def end_mafia_game(context: ContextTypes.DEFAULT_TYPE, code: str, winner: str):
    if code not in MAFIA_LOBBIES:
        return
    
    lobby = MAFIA_LOBBIES[code]
    
    if winner == "civilians":
        result_text = "🎉 ПОБЕДА МИРНЫХ ЖИТЕЛЕЙ!\n\n"
        result_text += "Вся мафия повержена!\n\n"
        
        for player_id, player in lobby.players.items():
            if player_id not in lobby.mafia_ids:
                add_win(player_id, player.username)
            else:
                add_loss(player_id, player.username)
    
    else:
        result_text = "🔪 ПОБЕДА МАФИИ!\n\n"
        result_text += "Мафия захватила город!\n\n"
        
        for player_id, player in lobby.players.items():
            if player_id in lobby.mafia_ids:
                add_win(player_id, player.username)
            else:
                add_loss(player_id, player.username)
    
    result_text += "👥 РОЛИ:\n"
    for player_id, player in lobby.players.items():
        role_emoji = {"мафия": "🔪", "комиссар": "👮", "доктор": "👨‍⚕️", "мирный": "👤"}
        emoji = role_emoji.get(player.role, "👤")
        status = "💀" if not player.alive else "✅"
        result_text += f"{emoji} {player.username} - {player.role} {status}\n"
    
    for player_id in lobby.players:
        try:
            await context.bot.send_message(chat_id=player_id, text=result_text)
        except:
            pass
    
    del MAFIA_LOBBIES[code]

# ============= MAIN =============

def main():
    init_db()
    print("=" * 50)
    print("✅ Бот запущен!")
    print("=" * 50)
    
    app = ApplicationBuilder().token("8708766321:AAHEK975FqlBqTusXmedyU9UctMWNKKYCRU").build()

    # Общие команды
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(CommandHandler("top", top_command))
    
    # Команды для шпиона
    app.add_handler(CommandHandler("join", join_lobby))
    app.add_handler(CommandHandler("players", players_command))
    app.add_handler(CommandHandler("leave", leave_lobby))
    app.add_handler(CommandHandler("startgame", start_game))
    
    # Команды для мафии
    app.add_handler(CommandHandler("joinmafia", join_mafia))
    app.add_handler(CommandHandler("mafiapl", mafia_players))
    app.add_handler(CommandHandler("leavemafia", leave_mafia))
    app.add_handler(CommandHandler("startmafia", start_mafia_game))
    
    # Callback handlers
    app.add_handler(CallbackQueryHandler(game_choice, pattern=r"^game_"))
    app.add_handler(CallbackQueryHandler(theme_selected, pattern=r"^theme_"))
    app.add_handler(CallbackQueryHandler(vote_handler, pattern=r"^vote_"))
    app.add_handler(CallbackQueryHandler(mafia_night_action, pattern=r"^mafia_(kill|heal|check)_"))
    app.add_handler(CallbackQueryHandler(mafia_day_vote, pattern=r"^mafia_vote_"))

    app.run_polling()

if __name__ == "__main__":
    main()
