from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
import random
import string
import sqlite3
import asyncio
import os
from contextlib import contextmanager
import logging

# ============= НАСТРОЙКА ЛОГИРОВАНИЯ =============
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ============= КОНФИГУРАЦИЯ =============
# ВАЖНО: Используйте переменные окружения для токена!
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', 'YOUR_TOKEN_HERE')
DB_PATH = 'spy_bot.db'

if BOT_TOKEN == 'YOUR_TOKEN_HERE':
    logger.error("❌ ОШИБКА: Токен не установлен! Используйте переменную окружения TELEGRAM_BOT_TOKEN")
    exit(1)

# ============= БАЗА ДАННЫХ (ИСПРАВЛЕНО) =============

@contextmanager
def get_db_connection():
    """Безопасное управление соединением с БД"""
    conn = sqlite3.connect(DB_PATH)
    try:
        yield conn
    except Exception as e:
        logger.error(f"Database error: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

def init_db():
    """Инициализация базы данных с индексами"""
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS stats (
            user_id INTEGER PRIMARY KEY,
            username TEXT NOT NULL,
            wins INTEGER DEFAULT 0,
            losses INTEGER DEFAULT 0,
            total_games INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
        
        # Индекс для быстрого поиска топа
        c.execute('''CREATE INDEX IF NOT EXISTS idx_wins 
                     ON stats(wins DESC, total_games DESC)''')
        conn.commit()
        logger.info("✅ База данных инициализирована")

def add_win(user_id, username):
    """Добавить победу игроку"""
    if not username:
        username = f"User_{user_id}"
    
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute('''INSERT INTO stats (user_id, username, wins, total_games) 
                     VALUES (?, ?, 1, 1)
                     ON CONFLICT(user_id) DO UPDATE SET
                     wins = wins + 1,
                     total_games = total_games + 1,
                     username = ?,
                     updated_at = CURRENT_TIMESTAMP''',
                  (user_id, username, username))
        conn.commit()

def add_loss(user_id, username):
    """Добавить поражение игроку"""
    if not username:
        username = f"User_{user_id}"
    
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute('''INSERT INTO stats (user_id, username, losses, total_games) 
                     VALUES (?, ?, 1, 1)
                     ON CONFLICT(user_id) DO UPDATE SET
                     losses = losses + 1,
                     total_games = total_games + 1,
                     username = ?,
                     updated_at = CURRENT_TIMESTAMP''',
                  (user_id, username, username))
        conn.commit()

def get_user_stats(user_id):
    """Получить статистику игрока"""
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute('SELECT * FROM stats WHERE user_id = ?', (user_id,))
        result = c.fetchone()
        if result:
            return {
                'user_id': result[0],
                'username': result[1],
                'wins': result[2],
                'losses': result[3],
                'total_games': result[4]
            }
    return None

def get_top_players(limit=10):
    """Получить топ игроков"""
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute('''SELECT username, wins, total_games 
                     FROM stats 
                     WHERE total_games > 0
                     ORDER BY wins DESC, total_games DESC 
                     LIMIT ?''', (limit,))
        return c.fetchall()
        # ============= КРОКОДИЛ - СЛОВА =============

CROCODILE_WORDS = {
    "🟢 Легкие": [
        "кот", "собака", "дом", "машина", "дерево", "книга", "стол", "стул",
        "телефон", "вода", "хлеб", "рыба", "птица", "цветок", "солнце",
        "луна", "звезда", "река", "гора", "море", "лес", "поле", "город",
        "школа", "доктор", "учитель", "повар", "актер", "мяч", "велосипед",
        "самолет", "корабль", "поезд", "автобус", "яблоко", "банан",
        "апельсин", "помидор", "огурец", "морковь", "слон", "жираф",
        "медведь", "лев", "тигр", "обезьяна", "заяц", "змея", "черепаха",
        "попугай", "пожарный", "рюкзак", "зонт", "очки", "часы", "ключ",
    ],
    "🟡 Средние": [
        "библиотека", "компьютер", "телевизор", "холодильник", "микроволновка",
        "пылесос", "кондиционер", "лифт", "эскалатор", "супергерой",
        "волшебник", "пират", "рыцарь", "принцесса", "динозавр", "дракон",
        "единорог", "баскетбол", "футбол", "теннис", "плавание", "гимнастика",
        "фотограф", "художник", "музыкант", "певец", "танцор", "космонавт",
        "подводная лодка", "вертолет", "ракета", "радуга", "молния",
        "шоколад", "мороженое", "пицца", "суши", "гамбургер", "аквариум",
        "зоопарк", "цирк", "карусель", "батут", "водопад", "вулкан",
    ],
    "🔴 Сложные": [
        "телепортация", "клонирование", "гравитация", "эволюция", "революция",
        "философия", "психология", "дирижер", "архитектор", "программист",
        "хирург", "дипломат", "парламент", "правительство", "конституция",
        "реинкарнация", "медитация", "гипноз", "телекинез", "экстрасенс",
        "инфляция", "монополия", "санкции", "абсурд", "парадокс",
        "иллюзия", "галлюцинация", "прокрастинация", "импровизация",
        "манипуляция", "провокация", "реабилитация", "конфиденциальность",
    ],
}


# ============= ТЕМЫ (БЕЗ ИЗМЕНЕНИЙ) =============

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
        "Титаник", "Начало", "Дюна", "Звездные войны",                          # ← убран "Аватар 2"
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
    "🎮 Стримеры-Ютуберы": [                                                             # ← новая категория
        "Mellstroy", "T2x2", "zubarefff", "Buster", "Братишкин",
        "Влад Бумага", "Evelone", "Evgen792", "paradeev1ch",
        "koreshzy", "StRoGo", "Dmitry_Lixxx", "SASAVOT", "GENSYXA",
        "JesusAVGN", "mazellovvv", "Papich", "Marmok", "deepins02",
        "Recrent", "ЛИТВИН", "Асхаб Тамаев", "Дима Масленников",
        "Kuplinov", "Wylsacom", "Сливки шоу",
    ],
}

# ============= КЛАССЫ (БЕЗ ИЗМЕНЕНИЙ) =============

class Player:
    def __init__(self, user_id, username):
        self.user_id = user_id
        self.username = username or f"Player_{user_id}"
        self.voted = False

class Lobby:
    def __init__(self, host_id, theme, single_device=False):
        self.code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
        self.host_id = host_id
        self.theme = theme
        self.players = {}
        self.spy_ids = set()
        self.location = None
        self.started = False
        self.voting = False
        self.votes = {}
        self.single_device = single_device
        self.current_reveal_index = 0
        self.roles_assigned = False
        self.player_order = []
        self.last_message_id = None
        self.lobby_message_ids = {}

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
        self.player_order = list(self.players.keys())
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


class MafiaPlayer:
    def __init__(self, user_id, username):
        self.user_id = user_id
        self.username = username or f"Player_{user_id}"
        self.role = None
        self.alive = True
        self.voted = False
        self.night_action_done = False

class MafiaLobby:
    def __init__(self, host_id, single_device=False):
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
        self.single_device = single_device
        self.current_reveal_index = 0
        self.roles_assigned = False
        self.player_order = []
        self.last_message_id = None
        self.lobby_message_ids = {}

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
        self.player_order = list(self.players.keys())
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
            if mafia_target == doctor_target:
                self.last_saved = mafia_target
            else:
                self.players[mafia_target].alive = False
                self.last_killed = mafia_target

        self.night_actions = {}
        for player in self.players.values():
            player.night_action_done = False

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

    def check_win_condition(self):
        alive_mafia = len(self.get_alive_mafia())
        alive_civilians = len(self.get_alive_civilians())

        if alive_mafia == 0:
            return "civilians"
        if alive_mafia >= alive_civilians:
            return "mafia"
        return None

class TODLobby:
    def __init__(self, host_id, mode, single_device=False):
        self.code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
        self.host_id = host_id
        self.mode = mode
        self.single_device = single_device
        self.players = {}
        self.player_order = []
        self.current_player_index = 0
        self.started = False
        self.round_number = 1
        self.max_rounds = 5
        self.rounds_completed = 0
        self.last_message_id = None
        self.lobby_message_ids = {}
        self.used_truths = set()
        self.used_dares = set()

    def add_player(self, user_id, username):
        if user_id not in self.players and len(self.players) < 15:
            self.players[user_id] = Player(user_id, username)
            return True
        return False

    def remove_player(self, user_id):
        if user_id in self.players:
            self.players.pop(user_id)
            return True
        return False

    def get_current_player_id(self):
        if not self.player_order:
            return None
        return self.player_order[self.current_player_index % len(self.player_order)]

    def get_random_truth(self):
        questions = TOD_QUESTIONS[self.mode]["truth"]
        available = [q for q in questions if q not in self.used_truths]
        if not available:
            self.used_truths.clear()
            available = questions
        q = random.choice(available)
        self.used_truths.add(q)
        return q

    def get_random_dare(self):
        dares = TOD_QUESTIONS[self.mode]["dare"]
        available = [d for d in dares if d not in self.used_dares]
        if not available:
            self.used_dares.clear()
            available = dares
        d = random.choice(available)
        self.used_dares.add(d)
        return d

    def next_turn(self):
        self.current_player_index += 1
        if self.current_player_index % len(self.player_order) == 0:
            self.round_number += 1
        self.rounds_completed += 1

    def is_game_over(self):
        return self.round_number > self.max_rounds

    def get_players_list(self):
        text = ""
        for i, (uid, player) in enumerate(self.players.items(), 1):
            text += f"{i}. {player.username}\n"
        return text

# ============= КРОКОДИЛ - КЛАСС =============

class CrocodileLobby:
    def __init__(self, host_id, difficulty, single_device=False):
        self.code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
        self.host_id = host_id
        self.players = {}
        self.difficulty = difficulty
        self.single_device = single_device
        self.started = False
        self.current_word = None
        self.words_used = set()
        self.current_explainer_index = 0
        self.player_order = []
        self.scores = {}
        self.round_number = 1
        self.max_rounds = 3
        self.words_per_turn = 3
        self.words_explained_this_turn = 0
        self.correct_this_turn = 0
        self.last_message_id = None
        self.lobby_message_ids = {}
        self.waiting_guess = False  # Для сетевого режима

    def add_player(self, user_id, username):
        if user_id not in self.players and len(self.players) < 10:
            self.players[user_id] = Player(user_id, username)
            self.scores[user_id] = 0
            return True
        return False

    def remove_player(self, user_id):
        if user_id in self.players:
            self.players.pop(user_id)
            self.scores.pop(user_id, None)
            return True
        return False

    def get_current_explainer_id(self):
        if not self.player_order:
            return None
        return self.player_order[self.current_explainer_index % len(self.player_order)]

    def get_next_word(self):
        words = CROCODILE_WORDS[self.difficulty]
        available = [w for w in words if w not in self.words_used]
        if not available:
            self.words_used.clear()
            available = words
        word = random.choice(available)
        self.words_used.add(word)
        self.current_word = word
        return word

    def next_turn(self):
        self.current_explainer_index += 1
        self.words_explained_this_turn = 0
        self.correct_this_turn = 0
        if self.current_explainer_index % len(self.player_order) == 0:
            self.round_number += 1

    def is_game_over(self):
        return self.round_number > self.max_rounds

    def get_scoreboard(self):
        sorted_scores = sorted(self.scores.items(), key=lambda x: x[1], reverse=True)
        text = "🏆 СЧЁТ:\n"
        medals = ["🥇", "🥈", "🥉"]
        for i, (uid, score) in enumerate(sorted_scores, 1):
            medal = medals[i - 1] if i <= 3 else f"{i}."
            name = self.players[uid].username if uid in self.players else f"Игрок {uid}"
            text += f"{medal} {name} — {score} очков\n"
        return text

    def get_players_list(self):
        text = ""
        for i, (uid, player) in enumerate(self.players.items(), 1):
            text += f"{i}. {player.username}\n"
        return text

# ============= ГЛОБАЛЬНЫЕ =============

LOBBIES = {}
MAFIA_LOBBIES = {}
CROCODILE_LOBBIES = {}
WAITING_PLAYER_COUNT = {}
CROCODILE_GUESSING = {}  # code -> True, для сетевого режима
TOD_LOBBIES = {}

TOD_QUESTIONS = {
    "normal": {
        "truth": [
            "Какой твой самый большой страх?",
            "Что ты никогда не расскажешь родителям?",
            "Какая твоя самая глупая покупка?",
            "Кого из присутствующих ты считаешь самым странным?",
            "Что тебя больше всего раздражает в людях?",
            "Какой твой самый неловкий момент в жизни?",
            "Если бы ты мог стать кем-то из присутствующих на день, кем бы ты стал?",
            "Какую ложь ты говоришь чаще всего?",
            "Что ты делаешь, когда думаешь, что за тобой никто не наблюдает?",
            "Какой твой самый стыдный музыкальный вкус?",
            "Во сколько лет ты впервые влюбился?",
            "Какой подарок ты делал вид, что тебе понравился, хотя на самом деле нет?",
            "Что ты никогда не простишь человеку?",
            "Какую знаменитость ты тайно обожаешь?",
            "Признайся в чём-то, за что тебе до сих пор стыдно.",
            "Какая твоя самая дурацкая суеверие или примета?",
            "Что ты делал в детстве и о чём сейчас жалеешь?",
            "Кому из присутствующих ты бы доверил хранить свои секреты?",
            "Какой твой тайный талант?",
            "Сколько денег ты тратишь на себя в месяц?",
            "Что бы ты сделал с миллионом рублей прямо сейчас?",
            "Кого из присутствующих ты бы взял с собой в путешествие?",
            "Что тебе снилось последний раз?",
            "Есть ли у тебя привычка, которой ты стыдишься?",
            "Какую профессию ты бы выбрал, если бы не было денежных ограничений?",
            "Что ты ненавидишь, но всё равно делаешь?",
            "Кого из присутствующих ты считаешь умнее всех?",
            "В чём ты притворяешься лучше, чем есть на самом деле?",
            "Что бы ты изменил в своей внешности, если бы мог?",
            "Какой твой самый бесполезный навык?",
        ],
        "dare": [
            "Говори только вопросами следующие 3 минуты.",
            "Напиши комплимент каждому игроку.",
            "Изобрази любое животное — остальные угадывают.",
            "Спой куплет любой песни.",
            "Сделай 20 приседаний прямо сейчас.",
            "Позвони кому-нибудь и скажи, что скучаешь по нему.",
            "Говори с акцентом следующие 5 минут.",
            "Напиши смешное сообщение в любой чат.",
            "Сделай странное лицо и держи его 30 секунд.",
            "Расскажи анекдот — если не смешной, делаешь ещё одно задание.",
            "Попробуй облизать локоть.",
            "Станцуй 1 минуту без музыки.",
            "Изобрази знаменитого человека — остальные угадывают.",
            "Скажи тост за каждого игрока.",
            "Сделай стойку у стены на 30 секунд.",
            "Напой мелодию — остальные угадывают песню.",
            "Назови 5 достоинств игрока справа от тебя.",
            "Произнеси алфавит наоборот.",
            "Сделай фото с самым нелепым выражением лица.",
            "Изобрази робота следующие 2 минуты.",
            "Напиши статус в соцсети: «Я лучший/лучшая!»",
            "Повтори за ведущим любую фразу с закрытым ртом.",
            "Говори «Эм» перед каждым словом следующие 2 минуты.",
            "Изобрази сцену из любого фильма.",
            "Подержи кубик льда в руке 30 секунд.",
            "Перечисли 10 стран за 15 секунд.",
            "Сделай комплимент самому себе вслух.",
            "Позвони маме и скажи что-нибудь смешное.",
            "Изобрази учителя, который объясняет урок.",
            "Попробуй сказать скороговорку 3 раза подряд быстро.",
        ],
    },
    "18plus": {
        "truth": [
            "Каким был твой первый поцелуй и с кем?",
            "Какой твой самый смелый поступок на вечеринке?",
            "Есть ли среди присутствующих тот, кто тебе нравится?",
            "С кем из знаменитостей ты бы провёл ночь?",
            "Какой твой самый безумный флирт?",
            "Признайся в самом диком поступке под воздействием алкоголя.",
            "Кому из присутствующих ты бы написал первым в 2 ночи?",
            "Сколько человек тебя целовало?",
            "Что ты считаешь идеальным свиданием?",
            "Опиши свой идеальный тип партнёра.",
            "Какой твой самый страстный поцелуй и где это было?",
            "Есть ли у тебя запасной человек на крайний случай?",
            "Что самое смелое ты когда-либо писал в переписке?",
            "Признайся: ты когда-нибудь танцевал стриптиз хотя бы для себя?",
            "Какую черту ты первым замечаешь в потенциальном партнёре?",
            "Опиши самый романтичный момент в твоей жизни.",
            "Что тебя заводит больше всего в людях?",
            "Признайся: ты ревнивый человек?",
            "Какой самый безумный комплимент тебе говорили?",
            "Ты когда-нибудь влюблялся с первого взгляда?",
            "Признайся в чём-то, что тебе стыдно искать в интернете.",
            "Что ты делаешь, чтобы привлечь внимание понравившегося человека?",
            "Ты когда-нибудь целовал кого-то из этой компании?",
            "Что для тебя является главным в физической привлекательности?",
            "Расскажи о своём самом запоминающемся свидании.",
            "Признайся: ты когда-нибудь притворялся, что не видишь сообщение?",
            "Какой твой самый неожиданный флирт?",
            "С кем из присутствующих ты бы сходил на свидание?",
            "Какой твой самый смелый поцелуй на публике?",
            "Расскажи о своей самой странной влюблённости.",
        ],
        "dare": [
            "Сделай массаж плеч игроку справа в течение 1 минуты.",
            "Напиши страстное признание в любви выдуманное и зачитай вслух.",
            "Позвони кому-нибудь и скажи комплимент соблазнительным голосом.",
            "Спой серенаду игроку слева.",
            "Сделай игроку напротив комплимент его внешности глядя в глаза.",
            "Изобрази танец стриптизёра хотя бы 30 секунд.",
            "Напиши интригующее сообщение в любой чат.",
            "Скажи каждому игроку что тебе в нём нравится во внешности.",
            "Сыграй в гляделки с игроком напротив — кто засмеётся проигрывает.",
            "Придумай и расскажи страстную историю любви за 1 минуту.",
            "Изобрази главного героя мелодрамы в сцене расставания.",
            "Опиши свой идеальный романтический вечер максимально подробно.",
            "Поговори с игроком справа голосом персонажа из романтического фильма.",
            "Придумай пикантный тост и произнеси его.",
            "Станцуй медленный танец с воображаемым партнёром.",
            "Попробуй завязать разговор с кем-нибудь максимально флиртующим образом.",
            "Назови 3 человека из присутствующих с которыми бы сходил на свидание.",
            "Нашепчи что-нибудь на ухо игроку рядом.",
            "Изобрази как ты флиртуешь когда сильно нервничаешь.",
            "Напиши анонимное любовное письмо и дай прочитать всем.",
            "Расскажи о своём типе идеального партнёра максимально подробно.",
            "Изобрази сцену ревности максимально драматично.",
            "Сделай комплимент каждому игроку касающийся его характера.",
            "Изобрази актёра в сцене поцелуя с воображаемым партнёром.",
            "Расскажи свою самую романтическую историю из жизни.",
            "Изобрази как выглядит человек влюблённый по уши.",
            "Напой романтическую песню глядя в глаза игроку напротив.",
            "Придумай романтическое прозвище каждому игроку.",
            "Изобрази сцену из романтического фильма на выбор компании.",
            "Расскажи что бы ты сделал на идеальном первом свидании.",
        ],
    },
}

async def update_lobby_message(context, player_id, lobby, text):
    """Удаляет старое сообщение лобби и отправляет новое"""
    old_msg_id = lobby.lobby_message_ids.get(player_id)
    if old_msg_id:
        try:
            await context.bot.delete_message(
                chat_id=player_id,
                message_id=old_msg_id
            )
        except Exception:
            pass

    try:
        sent = await context.bot.send_message(
            chat_id=player_id,
            text=text,
            parse_mode="HTML"
        )
        lobby.lobby_message_ids[player_id] = sent.message_id
    except Exception as e:
        logger.error(f"Ошибка обновления сообщения лобби для {player_id}: {e}")

# ============= КОМАНДЫ =============

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Стартовое меню"""
    keyboard = [
        [InlineKeyboardButton("🕵️ ШПИОН", callback_data="game_spy")],
        [InlineKeyboardButton("🔪 МАФИЯ", callback_data="game_mafia")],
        [InlineKeyboardButton("🐊 КРОКОДИЛ", callback_data="game_crocodile")],
        [InlineKeyboardButton("🎭 ПРАВДА ИЛИ ДЕЙСТВИЕ", callback_data="game_tod")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    text = "👋 Добро пожаловать в GameDAG!\n\nВыбери игру:"
    await update.message.reply_text(text, reply_markup=reply_markup)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Помощь"""
    text = """
📖 КАК ИГРАТЬ:

🕵️ ШПИОН:
1. Выбери игру и тему
2. Выбери режим (сеть/одно устройство)
3. Для сети: отправь код друзьям /join КОД
4. Для одного устройства: введи кол-во игроков
5. Обсуждайте и голосуйте!

🔪 МАФИЯ:
1. Создай лобби мафии
2. Выбери режим
3. Для сети: /joinmafia КОД
4. Для одного устройства: введи кол-во игроков
5. Ночью действуют роли, днём город голосует

/stats - Статистика
/top - Топ игроков
"""
    await update.message.reply_text(text)

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Статистика игрока"""
    user_id = update.effective_user.id
    stats = get_user_stats(user_id)
    if not stats:
        text = "📊 У тебя пока нет статистики."
    else:
        total = stats['total_games']
        win_rate = (stats['wins'] / total * 100) if total > 0 else 0
        text = (f"📊 Твоя статистика:\n\n👤 {stats['username']}\n\n"
                f"🏆 Всего игр: {total}\n✅ Побед: {stats['wins']}\n"
                f"❌ Поражений: {stats['losses']}\n📈 Винрейт: {win_rate:.1f}%")
    await update.message.reply_text(text)

async def top_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Топ игроков"""
    top_players = get_top_players(10)
    if not top_players:
        text = "🏆 Топ пуст."
    else:
        text = "🏆 ТОП 10 ИГРОКОВ:\n\n"
        for i, (username, wins, total) in enumerate(top_players, 1):
            win_rate = (wins / total * 100) if total > 0 else 0
            text += f"{i}. {username} - {wins}/{total} ({win_rate:.1f}%)\n"
    await update.message.reply_text(text)

async def game_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выбор игры"""
    query = update.callback_query
    await query.answer()
    game = query.data.split("_")[1]

    if game == "spy":
        all_themes = list(THEMES.keys())
        keyboard = [[InlineKeyboardButton(theme, callback_data=f"theme_{theme}")] for theme in all_themes]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("🎯 ШПИОН - Выберите тему:", reply_markup=reply_markup)

    elif game == "mafia":
        keyboard = [
            [InlineKeyboardButton("🌐 Игра по сети", callback_data="mafia_mode_network")],
            [InlineKeyboardButton("📱 С одного устройства", callback_data="mafia_mode_single")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("🔪 МАФИЯ - Выберите режим:", reply_markup=reply_markup)

    elif game == "tod":
        await tod_mode_selected(update, context)
        return

    elif game == "crocodile":
        keyboard = [
            [InlineKeyboardButton(diff, callback_data=f"croc_diff_{diff}")]
            for diff in CROCODILE_WORDS.keys()
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "🐊 КРОКОДИЛ\n\nОдин объясняет — остальные угадывают!\n\nВыберите сложность слов:",
            reply_markup=reply_markup
        )

async def theme_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выбор темы для шпиона"""
    query = update.callback_query
    await query.answer()
    theme = query.data.split("_", 1)[1]

    keyboard = [
        [InlineKeyboardButton("🌐 Игра по сети", callback_data=f"spy_mode_network_{theme}")],
        [InlineKeyboardButton("📱 С одного устройства", callback_data=f"spy_mode_single_{theme}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(f"🎯 Тема: {theme}\n\nВыберите режим:", reply_markup=reply_markup)

async def spy_mode_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выбор режима для шпиона"""
    query = update.callback_query
    await query.answer()

    parts = query.data.split("_")
    mode = parts[2]
    theme = "_".join(parts[3:])

    if mode == "single":
        WAITING_PLAYER_COUNT[query.from_user.id] = {
            "type": "spy",
            "theme": theme,
            "chat_id": query.message.chat_id
        }
        await query.edit_message_text(
            f"🎯 Тема: {theme}\n📱 Режим: С одного устройства\n\n"
            f"Введите количество игроков (от 3 до 10):"
        )
    else:
        lobby = Lobby(host_id=query.from_user.id, theme=theme, single_device=False)
        lobby.add_player(query.from_user.id, query.from_user.username or "Игрок")
        LOBBIES[lobby.code] = lobby

        text = (
            f"✅ Лобби шпиона\n\n"
            f"📌 Код: <b>{lobby.code}</b>\n"
            f"🎯 Тема: {theme}\n"
            f"🌐 Режим: По сети\n"
            f"👥 Игроков: 1/10\n\n"
            f"📋 Список игроков:\n{lobby.get_players_list()}\n"
            f"Отправь код друзьям:\n<code>/join {lobby.code}</code>\n\n"
            f"Запусти игру:\n<code>/startgame {lobby.code}</code>"
        )
        await query.edit_message_text(text=text, parse_mode="HTML")
        lobby.lobby_message_ids[query.from_user.id] = query.message.message_id

async def mafia_mode_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выбор режима для мафии"""
    query = update.callback_query
    await query.answer()

    parts = query.data.split("_")
    mode = parts[2]

    user_id = query.from_user.id
    username = query.from_user.username or "Игрок"

    if mode == "single":
        WAITING_PLAYER_COUNT[user_id] = {
            "type": "mafia",
            "chat_id": query.message.chat_id
        }
        await query.edit_message_text(
            "🔪 МАФИЯ\n📱 Режим: С одного устройства\n\n"
            "Введите количество игроков (от 4 до 10):"
        )
    else:
        lobby = MafiaLobby(host_id=user_id, single_device=False)
        lobby.add_player(user_id, username)
        MAFIA_LOBBIES[lobby.code] = lobby

        text = (
            f"✅ Лобби МАФИИ создано!\n\n"
            f"📌 Код: <b>{lobby.code}</b>\n"
            f"🌐 Режим: По сети\n"
            f"👥 Игроков: 1/10\n\n"
            f"📋 Список игроков:\n{lobby.get_players_list()}\n"
            f"📍 Минимум 4 игрока\n\n"
            f"Отправь код друзьям:\n<code>/joinmafia {lobby.code}</code>\n\n"
            f"Запусти игру:\n<code>/startmafia {lobby.code}</code>"
        )
        await query.edit_message_text(text=text, parse_mode="HTML")
        lobby.lobby_message_ids[user_id] = query.message.message_id

async def handle_player_count_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ввода количества игроков"""
    user_id = update.effective_user.id

        # Проверяем угадывание в крокодиле (сетевой режим)
    for code, is_active in list(CROCODILE_GUESSING.items()):
        if code in CROCODILE_LOBBIES and is_active:
            lobby = CROCODILE_LOBBIES[code]
            if user_id in lobby.players:
                explainer_id = lobby.get_current_explainer_id()
                if user_id != explainer_id:
                    guess = update.message.text.strip().lower()
                    correct = lobby.current_word.lower() if lobby.current_word else ""
                    if guess == correct:
                        guesser_name = lobby.players[user_id].username
                        lobby.scores[user_id] = lobby.scores.get(user_id, 0) + 1
                        for pid in lobby.players:
                            try:
                                await context.bot.send_message(
                                    chat_id=pid,
                                    text=f"🎉 <b>{guesser_name}</b> угадал слово <b>{lobby.current_word}</b>!\n+1 очко!\n\n{lobby.get_scoreboard()}",
                                    parse_mode="HTML"
                                )
                            except Exception:
                                pass
                        await asyncio.sleep(2)
                        lobby.words_explained_this_turn += 1
                        if lobby.words_explained_this_turn >= lobby.words_per_turn:
                            CROCODILE_GUESSING[code] = False
                            await croc_next_turn_network(context, code)
                        else:
                            word = lobby.get_next_word()
                            explainer = lobby.players[explainer_id]
                            try:
                                keyboard = [
                                    [InlineKeyboardButton("✅ Угадали!", callback_data=f"croc_correct_{code}")],
                                    [InlineKeyboardButton("⏭️ Пропустить слово", callback_data=f"croc_skip_{code}")]
                                ]
                                reply_markup = InlineKeyboardMarkup(keyboard)
                                remaining = lobby.words_per_turn - lobby.words_explained_this_turn
                                await context.bot.send_message(
                                    chat_id=explainer_id,
                                    text=(f"🔤 СЛЕДУЮЩЕЕ СЛОВО:\n\n<b>「 {word.upper()} 」</b>\n\n"
                                          f"📝 Осталось: {remaining}"),
                                    reply_markup=reply_markup,
                                    parse_mode="HTML"
                                )
                            except Exception:
                                pass
                    else:
                        await update.message.reply_text(f"❌ Не угадал! Попробуй ещё раз")
                return

    if user_id not in WAITING_PLAYER_COUNT:
        return

    state = WAITING_PLAYER_COUNT[user_id]
    text = update.message.text.strip()

    try:
        count = int(text)
    except ValueError:
        await update.message.reply_text("❌ Введите число!")
        return

    game_type = state["type"]

    if game_type == "spy":
        if count < 3 or count > 10:
            await update.message.reply_text("❌ Количество игроков: от 3 до 10. Попробуйте снова:")
            return

        del WAITING_PLAYER_COUNT[user_id]

        theme = state["theme"]
        lobby = Lobby(host_id=user_id, theme=theme, single_device=True)

        for i in range(1, count + 1):
            fake_id = user_id * 1000 + i
            lobby.add_player(fake_id, f"Игрок {i}")

        LOBBIES[lobby.code] = lobby
        lobby.start_game()

        keyboard = [[InlineKeyboardButton("✅ Готов", callback_data=f"spy_ready_{lobby.code}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        sent_message = await update.message.reply_text(
            f"🎮 ИГРА НАЧАЛАСЬ!\n\n🎯 Тема: {theme}\n👥 Игроков: {count}\n📱 Режим: С одного устройства\n\n"
            f"👤 Передайте телефон Игроку 1\nНажмите «Готов» чтобы узнать роль",
            reply_markup=reply_markup
        )
        lobby.last_message_id = sent_message.message_id

    elif game_type == "mafia":
        if count < 4 or count > 10:
            await update.message.reply_text("❌ Количество игроков: от 4 до 10. Попробуйте снова:")
            return

        del WAITING_PLAYER_COUNT[user_id]

        lobby = MafiaLobby(host_id=user_id, single_device=True)

        for i in range(1, count + 1):
            fake_id = user_id * 1000 + i
            lobby.add_player(fake_id, f"Игрок {i}")

        MAFIA_LOBBIES[lobby.code] = lobby
        lobby.start_game()

        keyboard = [[InlineKeyboardButton("✅ Готов", callback_data=f"mafia_ready_{lobby.code}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        sent_message = await update.message.reply_text(
            f"🎮 МАФИЯ НАЧАЛАСЬ!\n\n👥 Игроков: {count}\n📱 Режим: С одного устройства\n\n"
            f"👤 Передайте телефон Игроку 1\nНажмите «Готов» чтобы узнать роль",
            reply_markup=reply_markup
        )
        lobby.last_message_id = sent_message.message_id

    elif game_type == "crocodile":
        if count < 2 or count > 10:
            await update.message.reply_text("❌ Количество игроков: от 2 до 10. Попробуйте снова:")
            return

        del WAITING_PLAYER_COUNT[user_id]

        difficulty = state["difficulty"]
        lobby = CrocodileLobby(host_id=user_id, difficulty=difficulty, single_device=True)

        for i in range(1, count + 1):
            fake_id = user_id * 1000 + i
            lobby.add_player(fake_id, f"Игрок {i}")

        CROCODILE_LOBBIES[lobby.code] = lobby
        lobby.started = True
        lobby.player_order = list(lobby.players.keys())
        random.shuffle(lobby.player_order)

        chat_id = state["chat_id"]
        await update.message.reply_text(
            f"🐊 КРОКОДИЛ НАЧАЛСЯ!\n\n"
            f"🎯 Сложность: {difficulty}\n"
            f"👥 Игроков: {count}\n"
            f"🔄 Раундов: {lobby.max_rounds}\n"
            f"📝 Слов за ход: {lobby.words_per_turn}\n\n"
            f"Каждый по очереди объясняет слово!\n\n"
            f"Начинает Игрок 1!"
        )
        await asyncio.sleep(2)
        await croc_start_single_device(context, lobby.code, chat_id)

# ============= ПРАВДА ИЛИ ДЕЙСТВИЕ - ФУНКЦИИ =============

async def tod_mode_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = [
        [InlineKeyboardButton("😊 Обычный режим", callback_data="tod_rating_normal")],
        [InlineKeyboardButton("🔞 Режим 18+", callback_data="tod_rating_18plus")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        "🎭 ПРАВДА ИЛИ ДЕЙСТВИЕ\n\nВыберите режим игры:\n\n"
        "😊 Обычный — весёлые вопросы для любой компании\n"
        "🔞 18+ — более смелые вопросы для взрослых",
        reply_markup=reply_markup
    )

async def tod_rating_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    rating = query.data.split("tod_rating_")[1]
    rating_label = "😊 Обычный" if rating == "normal" else "🔞 18+"
    keyboard = [
        [InlineKeyboardButton("🌐 Игра по сети", callback_data=f"tod_device_network_{rating}")],
        [InlineKeyboardButton("📱 С одного устройства", callback_data=f"tod_device_single_{rating}")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        f"🎭 ПРАВДА ИЛИ ДЕЙСТВИЕ\n🎮 Режим: {rating_label}\n\nВыберите тип игры:",
        reply_markup=reply_markup
    )

async def tod_device_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    parts = query.data.split("_")
    device = parts[2]
    rating = parts[3]
    user_id = query.from_user.id
    username = query.from_user.username or "Игрок"
    rating_label = "😊 Обычный" if rating == "normal" else "🔞 18+"

    if device == "single":
        WAITING_PLAYER_COUNT[user_id] = {
            "type": "tod",
            "mode": rating,
            "chat_id": query.message.chat_id
        }
        await query.edit_message_text(
            f"🎭 ПРАВДА ИЛИ ДЕЙСТВИЕ\n"
            f"🎮 Режим: {rating_label}\n"
            f"📱 Тип: С одного устройства\n\n"
            f"Введите количество игроков (от 2 до 15):"
        )
    else:
        lobby = TODLobby(host_id=user_id, mode=rating, single_device=False)
        lobby.add_player(user_id, username)
        TOD_LOBBIES[lobby.code] = lobby
        text = (
            f"✅ Лобби «Правда или Действие» создано!\n\n"
            f"📌 Код: <b>{lobby.code}</b>\n"
            f"🎮 Режим: {rating_label}\n"
            f"🌐 Тип: По сети\n"
            f"👥 Игроков: 1/15\n\n"
            f"📋 Игроки:\n{lobby.get_players_list()}\n"
            f"📍 Минимум 2 игрока\n\n"
            f"Отправь код друзьям:\n<code>/jointod {lobby.code}</code>\n\n"
            f"Запусти игру:\n<code>/starttod {lobby.code}</code>"
        )
        await query.edit_message_text(text=text, parse_mode="HTML")
        lobby.lobby_message_ids[user_id] = query.message.message_id

async def join_tod(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if len(context.args) != 1:
        await update.message.reply_text("❌ Использование: /jointod <код>")
        return
    code = context.args[0].upper()
    if code not in TOD_LOBBIES:
        await update.message.reply_text(f"❌ Лобби {code} не найдено.")
        return
    lobby = TOD_LOBBIES[code]
    if lobby.single_device:
        await update.message.reply_text("❌ Это лобби для одного устройства.")
        return
    if lobby.started:
        await update.message.reply_text("❌ Игра уже началась.")
        return
    if user.id in lobby.players:
        await update.message.reply_text("❌ Ты уже в лобби.")
        return
    if not lobby.add_player(user.id, user.username or "Игрок"):
        await update.message.reply_text("❌ Лобби переполнено.")
        return
    rating_label = "😊 Обычный" if lobby.mode == "normal" else "🔞 18+"

    def lobby_text():
        return (
            f"✅ Лобби «Правда или Действие»\n\n"
            f"📌 Код: <b>{lobby.code}</b>\n"
            f"🎮 Режим: {rating_label}\n"
            f"🌐 Тип: По сети\n"
            f"👥 Игроков: {len(lobby.players)}/15\n\n"
            f"📋 Игроки:\n{lobby.get_players_list()}\n"
            f"Запусти игру:\n<code>/starttod {code}</code>"
        )

    sent = await update.message.reply_text(lobby_text(), parse_mode="HTML")
    lobby.lobby_message_ids[user.id] = sent.message_id
    for player_id in lobby.players:
        if player_id != user.id:
            await update_lobby_message(context, player_id, lobby, lobby_text())

async def start_tod_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if len(context.args) != 1:
        await update.message.reply_text("❌ Использование: /starttod <код>")
        return
    code = context.args[0].upper()
    if code not in TOD_LOBBIES:
        await update.message.reply_text("❌ Лобби не найдено.")
        return
    lobby = TOD_LOBBIES[code]
    if lobby.host_id != user.id:
        await update.message.reply_text("❌ Только хост может начать.")
        return
    if lobby.started:
        await update.message.reply_text("❌ Игра уже запущена.")
        return
    if len(lobby.players) < 2:
        await update.message.reply_text("❌ Минимум 2 игрока.")
        return

    lobby.started = True
    lobby.player_order = list(lobby.players.keys())
    random.shuffle(lobby.player_order)
    rating_label = "😊 Обычный" if lobby.mode == "normal" else "🔞 18+"

    for player_id in lobby.players:
        try:
            await context.bot.send_message(
                chat_id=player_id,
                text=(
                    f"🎭 ПРАВДА ИЛИ ДЕЙСТВИЕ НАЧАЛАСЬ!\n\n"
                    f"🎮 Режим: {rating_label}\n"
                    f"🔄 Раундов: {lobby.max_rounds}\n\n"
                    f"По очереди каждый выбирает:\n"
                    f"🤔 ПРАВДА — ответь честно на вопрос\n"
                    f"💪 ДЕЙСТВИЕ — выполни задание\n\n"
                    f"Когда придёт твоя очередь — получишь уведомление!"
                )
            )
        except Exception as e:
            logger.error(f"Ошибка: {e}")

    await update.message.reply_text("✅ ИГРА НАЧАЛАСЬ!")
    await asyncio.sleep(2)
    await tod_start_turn_network(context, code)

async def tod_start_turn_network(context: ContextTypes.DEFAULT_TYPE, code: str):
    if code not in TOD_LOBBIES:
        return
    lobby = TOD_LOBBIES[code]
    if lobby.is_game_over():
        await tod_end_game_network(context, code)
        return

    current_id = lobby.get_current_player_id()
    current_player = lobby.players[current_id]
    round_info = f"🔄 Раунд {lobby.round_number}/{lobby.max_rounds}"

    for player_id in lobby.players:
        if player_id != current_id:
            try:
                await context.bot.send_message(
                    chat_id=player_id,
                    text=f"🎭 {round_info}\n\n👤 Ход: <b>{current_player.username}</b>\n\nЖдём его выбора...",
                    parse_mode="HTML"
                )
            except Exception as e:
                logger.error(f"Ошибка: {e}")

    keyboard = [
        [InlineKeyboardButton("🤔 ПРАВДА", callback_data=f"tod_choose_truth_{code}")],
        [InlineKeyboardButton("💪 ДЕЙСТВИЕ", callback_data=f"tod_choose_dare_{code}")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    try:
        await context.bot.send_message(
            chat_id=current_id,
            text=f"🎭 ТВОЙ ХОД!\n\n{round_info}\n\nВыбирай:",
            reply_markup=reply_markup,
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Ошибка: {e}")

async def tod_choose_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    parts = query.data.split("_")
    choice = parts[2]
    code = parts[3]

    if code not in TOD_LOBBIES:
        await query.edit_message_text("❌ Игра не найдена.")
        return

    lobby = TOD_LOBBIES[code]
    current_id = lobby.get_current_player_id()

    if query.from_user.id != current_id:
        await query.answer("❌ Сейчас не твой ход!", show_alert=True)
        return

    if choice == "truth":
        content = lobby.get_random_truth()
        emoji = "🤔"
        label = "ПРАВДА"
        prefix = "❓"
    else:
        content = lobby.get_random_dare()
        emoji = "💪"
        label = "ДЕЙСТВИЕ"
        prefix = "🎯"

    keyboard = [
        [InlineKeyboardButton("✅ Выполнено / Ответил", callback_data=f"tod_done_{code}")],
        [InlineKeyboardButton("❌ Отказываюсь (пропуск)", callback_data=f"tod_skip_{code}")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        f"{emoji} <b>{label}!</b>\n\n{prefix} <b>{content}</b>\n\nВыполни и нажми «Выполнено»!",
        reply_markup=reply_markup,
        parse_mode="HTML"
    )

    for player_id in lobby.players:
        if player_id != current_id:
            try:
                await context.bot.send_message(
                    chat_id=player_id,
                    text=f"{emoji} <b>{lobby.players[current_id].username}</b> выбрал(а): <b>{label}</b>\n\n{prefix} {content}",
                    parse_mode="HTML"
                )
            except Exception as e:
                logger.error(f"Ошибка: {e}")

async def tod_done_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("✅ Отлично!")
    code = query.data.split("tod_done_")[1]
    if code not in TOD_LOBBIES:
        await query.edit_message_text("❌ Игра не найдена.")
        return
    lobby = TOD_LOBBIES[code]
    current_id = lobby.get_current_player_id()
    if query.from_user.id != current_id:
        await query.answer("❌ Не твой ход!", show_alert=True)
        return

    player_name = lobby.players[current_id].username
    await query.edit_message_text(f"✅ {player_name} выполнил(а)!")

    for player_id in lobby.players:
        if player_id != current_id:
            try:
                await context.bot.send_message(
                    chat_id=player_id,
                    text=f"✅ <b>{player_name}</b> выполнил(а) задание!",
                    parse_mode="HTML"
                )
            except Exception as e:
                logger.error(f"Ошибка: {e}")

    await asyncio.sleep(2)
    lobby.next_turn()
    if lobby.is_game_over():
        await tod_end_game_network(context, code)
    else:
        await tod_start_turn_network(context, code)

async def tod_skip_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("❌ Пропущено")
    code = query.data.split("tod_skip_")[1]
    if code not in TOD_LOBBIES:
        await query.edit_message_text("❌ Игра не найдена.")
        return
    lobby = TOD_LOBBIES[code]
    current_id = lobby.get_current_player_id()
    if query.from_user.id != current_id:
        await query.answer("❌ Не твой ход!", show_alert=True)
        return

    player_name = lobby.players[current_id].username
    await query.edit_message_text(f"❌ {player_name} отказался(ась)!")

    for player_id in lobby.players:
        if player_id != current_id:
            try:
                await context.bot.send_message(
                    chat_id=player_id,
                    text=f"❌ <b>{player_name}</b> отказался(ась) выполнять!",
                    parse_mode="HTML"
                )
            except Exception as e:
                logger.error(f"Ошибка: {e}")

    await asyncio.sleep(2)
    lobby.next_turn()
    if lobby.is_game_over():
        await tod_end_game_network(context, code)
    else:
        await tod_start_turn_network(context, code)

async def tod_end_game_network(context: ContextTypes.DEFAULT_TYPE, code: str):
    if code not in TOD_LOBBIES:
        return
    lobby = TOD_LOBBIES[code]
    result_text = "🎭 ИГРА «ПРАВДА ИЛИ ДЕЙСТВИЕ» ОКОНЧЕНА!\n\nСпасибо всем за игру! 🎉"
    for player_id in lobby.players:
        try:
            await context.bot.send_message(chat_id=player_id, text=result_text

# ============= КРОКОДИЛ - ВСЕ ФУНКЦИИ =============

async def croc_difficulty_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выбор сложности крокодила"""
    query = update.callback_query
    await query.answer()
    difficulty = query.data.split("croc_diff_")[1]
    keyboard = [
        [InlineKeyboardButton("🌐 Игра по сети", callback_data=f"croc_mode_network_{difficulty}")],
        [InlineKeyboardButton("📱 С одного устройства", callback_data=f"croc_mode_single_{difficulty}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        f"🐊 КРОКОДИЛ\n🎯 Сложность: {difficulty}\n\nВыберите режим:",
        reply_markup=reply_markup
    )

async def croc_mode_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выбор режима крокодила"""
    query = update.callback_query
    await query.answer()

    parts = query.data.split("_")
    mode = parts[2]
    difficulty = "_".join(parts[3:])

    user_id = query.from_user.id
    username = query.from_user.username or "Игрок"

    if mode == "single":
        WAITING_PLAYER_COUNT[user_id] = {
            "type": "crocodile",
            "difficulty": difficulty,
            "chat_id": query.message.chat_id
        }
        await query.edit_message_text(
            f"🐊 КРОКОДИЛ\n📱 Режим: С одного устройства\n🎯 Сложность: {difficulty}\n\n"
            f"Введите количество игроков (от 2 до 10):"
        )
    else:
        lobby = CrocodileLobby(host_id=user_id, difficulty=difficulty, single_device=False)
        lobby.add_player(user_id, username)
        CROCODILE_LOBBIES[lobby.code] = lobby

        text = (
            f"✅ Лобби КРОКОДИЛА создано!\n\n"
            f"📌 Код: <b>{lobby.code}</b>\n"
            f"🎯 Сложность: {difficulty}\n"
            f"🌐 Режим: По сети\n"
            f"👥 Игроков: 1/10\n\n"
            f"📋 Список игроков:\n{lobby.get_players_list()}\n"
            f"📍 Минимум 2 игрока\n\n"
            f"Отправь код друзьям:\n<code>/joincrocodile {lobby.code}</code>\n\n"
            f"Запусти игру:\n<code>/startcrocodile {lobby.code}</code>"
        )
        await query.edit_message_text(text=text, parse_mode="HTML")
        lobby.lobby_message_ids[user_id] = query.message.message_id

# ── Сетевые команды ──────────────────────────────────────────────

async def join_crocodile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Присоединиться к лобби крокодила"""
    user = update.effective_user
    if len(context.args) != 1:
        await update.message.reply_text("❌ Использование: /joincrocodile <код>")
        return
    code = context.args[0].upper()
    if code not in CROCODILE_LOBBIES:
        await update.message.reply_text(f"❌ Лобби {code} не найдено.")
        return
    lobby = CROCODILE_LOBBIES[code]

    if lobby.single_device:
        await update.message.reply_text("❌ Это лобби для игры с одного устройства.")
        return
    if lobby.started:
        await update.message.reply_text("❌ Игра уже началась.")
        return
    if user.id in lobby.players:
        await update.message.reply_text("❌ Ты уже в лобби.")
        return
    if not lobby.add_player(user.id, user.username or "Игрок"):
        await update.message.reply_text("❌ Лобби переполнено.")
        return

    def lobby_text():
        return (
            f"✅ Лобби крокодила\n\n"
            f"📌 Код: <b>{lobby.code}</b>\n"
            f"🎯 Сложность: {lobby.difficulty}\n"
            f"🌐 Режим: По сети\n"
            f"👥 Игроков: {len(lobby.players)}/10\n\n"
            f"📋 Список игроков:\n{lobby.get_players_list()}\n"
            f"📍 Минимум 2 игрока\n\n"
            f"Запусти игру:\n<code>/startcrocodile {code}</code>"
        )

    sent = await update.message.reply_text(lobby_text(), parse_mode="HTML")
    lobby.lobby_message_ids[user.id] = sent.message_id

    for player_id in lobby.players:
        if player_id != user.id:
            await update_lobby_message(context, player_id, lobby, lobby_text())

async def start_crocodile_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начать игру крокодил (сетевой режим)"""
    user = update.effective_user
    if len(context.args) != 1:
        await update.message.reply_text("❌ Использование: /startcrocodile <код>")
        return
    code = context.args[0].upper()
    if code not in CROCODILE_LOBBIES:
        await update.message.reply_text("❌ Лобби не найдено.")
        return
    lobby = CROCODILE_LOBBIES[code]
    if lobby.host_id != user.id:
        await update.message.reply_text("❌ Только хост может начать.")
        return
    if lobby.started:
        await update.message.reply_text("❌ Игра уже запущена.")
        return
    if len(lobby.players) < 2:
        await update.message.reply_text("❌ Минимум 2 игрока.")
        return

    lobby.started = True
    lobby.player_order = list(lobby.players.keys())
    random.shuffle(lobby.player_order)

    # Сообщаем всем что игра началась
    for player_id, player in lobby.players.items():
        try:
            await context.bot.send_message(
                chat_id=player_id,
                text=(f"🐊 КРОКОДИЛ НАЧАЛСЯ!\n\n🎯 Сложность: {lobby.difficulty}\n"
                      f"🔄 Раундов: {lobby.max_rounds}\n📝 Слов за ход: {lobby.words_per_turn}\n\n"
                      f"Когда придёт твой черёд объяснять — ты получишь слово.\n"
                      f"Остальные отправляют боту свои варианты!")
            )
        except Exception as e:
            logger.error(f"Ошибка отправки сообщения игроку {player_id}: {e}")

    await update.message.reply_text("✅ КРОКОДИЛ НАЧАЛСЯ!")
    await asyncio.sleep(2)
    await croc_start_turn_network(context, code)

async def croc_start_turn_network(context: ContextTypes.DEFAULT_TYPE, code: str):
    """Начало хода в сетевом режиме"""
    if code not in CROCODILE_LOBBIES:
        return
    lobby = CROCODILE_LOBBIES[code]

    if lobby.is_game_over():
        await croc_end_game_network(context, code)
        return

    explainer_id = lobby.get_current_explainer_id()
    explainer = lobby.players[explainer_id]
    word = lobby.get_next_word()
    lobby.words_explained_this_turn = 0
    lobby.waiting_guess = True
    CROCODILE_GUESSING[code] = True

    round_info = f"🔄 Раунд {lobby.round_number}/{lobby.max_rounds}"
    turn_info = (f"🎤 Объясняет: <b>{explainer.username}</b>\n"
                 f"📝 Слов осталось в ходе: {lobby.words_per_turn - lobby.words_explained_this_turn}")

    # Объясняющему — слово
    try:
        keyboard = [
            [InlineKeyboardButton("✅ Угадали!", callback_data=f"croc_correct_{code}")],
            [InlineKeyboardButton("⏭️ Пропустить слово", callback_data=f"croc_skip_{code}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await context.bot.send_message(
            chat_id=explainer_id,
            text=(f"🐊 ТВОЙ ХОД!\n\n{round_info}\n\n"
                  f"🔤 ТВОЁ СЛОВО:\n\n<b>「 {word.upper()} 」</b>\n\n"
                  f"Объясняй — не называй само слово!\nКогда угадают — нажми «Угадали!»"),
            reply_markup=reply_markup,
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Ошибка отправки слова объясняющему: {e}")

    # Остальным — ждать
    for player_id, player in lobby.players.items():
        if player_id == explainer_id:
            continue
        try:
            await context.bot.send_message(
                chat_id=player_id,
                text=(f"🐊 {round_info}\n\n"
                      f"🎤 Объясняет: <b>{explainer.username}</b>\n\n"
                      f"Пиши мне свои варианты ответа!"),
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Ошибка отправки уведомления игроку {player_id}: {e}")

async def croc_correct_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Слово угадано (нажал объясняющий)"""
    query = update.callback_query
    await query.answer("✅ Слово угадано!")

    code = query.data.split("croc_correct_")[1]
    if code not in CROCODILE_LOBBIES:
        await query.edit_message_text("❌ Игра не найдена.")
        return

    lobby = CROCODILE_LOBBIES[code]
    explainer_id = lobby.get_current_explainer_id()

    # Начисляем очко объясняющему
    lobby.scores[explainer_id] = lobby.scores.get(explainer_id, 0) + 1
    lobby.words_explained_this_turn += 1
    lobby.correct_this_turn += 1

    guessed_word = lobby.current_word
    explainer_name = lobby.players[explainer_id].username

    await query.edit_message_text(
        f"✅ Угадано!\n\nСлово было: <b>{guessed_word}</b>\n\n{lobby.get_scoreboard()}",
        parse_mode="HTML"
    )

    # Уведомляем остальных
    for player_id, player in lobby.players.items():
        if player_id == explainer_id:
            continue
        try:
            await context.bot.send_message(
                chat_id=player_id,
                text=f"✅ Слово угадано!\n\nСлово было: <b>{guessed_word}</b>\n+1 очко → {explainer_name}\n\n{lobby.get_scoreboard()}",
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Ошибка уведомления: {e}")

    await asyncio.sleep(2)

    # Следующее слово или конец хода
    if lobby.words_explained_this_turn >= lobby.words_per_turn:
        CROCODILE_GUESSING[code] = False
        await croc_next_turn_network(context, code)
    else:
        # Следующее слово того же объясняющего
        word = lobby.get_next_word()
        try:
            keyboard = [
                [InlineKeyboardButton("✅ Угадали!", callback_data=f"croc_correct_{code}")],
                [InlineKeyboardButton("⏭️ Пропустить слово", callback_data=f"croc_skip_{code}")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            remaining = lobby.words_per_turn - lobby.words_explained_this_turn
            await context.bot.send_message(
                chat_id=explainer_id,
                text=(f"🔤 СЛЕДУЮЩЕЕ СЛОВО:\n\n<b>「 {word.upper()} 」</b>\n\n"
                      f"📝 Слов осталось: {remaining}"),
                reply_markup=reply_markup,
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Ошибка отправки следующего слова: {e}")

async def croc_skip_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Пропустить слово (нажал объясняющий)"""
    query = update.callback_query
    await query.answer("⏭️ Слово пропущено")

    code = query.data.split("croc_skip_")[1]
    if code not in CROCODILE_LOBBIES:
        await query.edit_message_text("❌ Игра не найдена.")
        return

    lobby = CROCODILE_LOBBIES[code]
    explainer_id = lobby.get_current_explainer_id()
    skipped_word = lobby.current_word
    lobby.words_explained_this_turn += 1

    await query.edit_message_text(f"⏭️ Пропущено!\n\nСлово было: <b>{skipped_word}</b>", parse_mode="HTML")

    for player_id in lobby.players:
        if player_id == explainer_id:
            continue
        try:
            await context.bot.send_message(
                chat_id=player_id,
                text=f"⏭️ Слово пропущено!\n\nСлово было: <b>{skipped_word}</b>",
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Ошибка уведомления: {e}")

    await asyncio.sleep(1)

    if lobby.words_explained_this_turn >= lobby.words_per_turn:
        CROCODILE_GUESSING[code] = False
        await croc_next_turn_network(context, code)
    else:
        word = lobby.get_next_word()
        try:
            keyboard = [
                [InlineKeyboardButton("✅ Угадали!", callback_data=f"croc_correct_{code}")],
                [InlineKeyboardButton("⏭️ Пропустить слово", callback_data=f"croc_skip_{code}")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            remaining = lobby.words_per_turn - lobby.words_explained_this_turn
            await context.bot.send_message(
                chat_id=explainer_id,
                text=(f"🔤 СЛЕДУЮЩЕЕ СЛОВО:\n\n<b>「 {word.upper()} 」</b>\n\n"
                      f"📝 Слов осталось: {remaining}"),
                reply_markup=reply_markup,
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Ошибка отправки следующего слова: {e}")

async def croc_next_turn_network(context: ContextTypes.DEFAULT_TYPE, code: str):
    """Переход к следующему игроку (сетевой)"""
    if code not in CROCODILE_LOBBIES:
        return
    lobby = CROCODILE_LOBBIES[code]
    lobby.next_turn()

    if lobby.is_game_over():
        await croc_end_game_network(context, code)
        return

    next_id = lobby.get_current_explainer_id()
    next_name = lobby.players[next_id].username

    for player_id in lobby.players:
        try:
            await context.bot.send_message(
                chat_id=player_id,
                text=f"➡️ Следующий объясняет: <b>{next_name}</b>\n\n{lobby.get_scoreboard()}",
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Ошибка: {e}")

    await asyncio.sleep(3)
    await croc_start_turn_network(context, code)

async def croc_end_game_network(context: ContextTypes.DEFAULT_TYPE, code: str):
    """Конец игры крокодил (сетевой)"""
    if code not in CROCODILE_LOBBIES:
        return
    lobby = CROCODILE_LOBBIES[code]
    CROCODILE_GUESSING.pop(code, None)

    sorted_scores = sorted(lobby.scores.items(), key=lambda x: x[1], reverse=True)
    winner_id, winner_score = sorted_scores[0]
    winner_name = lobby.players[winner_id].username

    result_text = f"🎉 ИГРА ОКОНЧЕНА!\n\n🏆 ПОБЕДИТЕЛЬ: {winner_name} ({winner_score} очков)!\n\n"
    result_text += lobby.get_scoreboard()

    # Статистика
    for player_id, player in lobby.players.items():
        if player_id == winner_id:
            add_win(player_id, player.username)
        else:
            add_loss(player_id, player.username)

    for player_id in lobby.players:
        try:
            await context.bot.send_message(chat_id=player_id, text=result_text)
        except Exception as e:
            logger.error(f"Ошибка отправки результата: {e}")

    del CROCODILE_LOBBIES[code]

# ── Одно устройство ──────────────────────────────────────────────

async def croc_start_single_device(context: ContextTypes.DEFAULT_TYPE, code: str, chat_id: int):
    """Начало хода (одно устройство)"""
    if code not in CROCODILE_LOBBIES:
        return
    lobby = CROCODILE_LOBBIES[code]

    if lobby.is_game_over():
        await croc_end_game_single(context, code, chat_id)
        return

    explainer_id = lobby.get_current_explainer_id()
    explainer = lobby.players[explainer_id]
    word = lobby.get_next_word()
    lobby.words_explained_this_turn = 0
    lobby.correct_this_turn = 0

    round_info = f"🔄 Раунд {lobby.round_number}/{lobby.max_rounds}"

    keyboard = [
        [InlineKeyboardButton("✅ Угадали!", callback_data=f"croc_single_correct_{code}")],
        [InlineKeyboardButton("⏭️ Пропустить", callback_data=f"croc_single_skip_{code}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    sent = await context.bot.send_message(
        chat_id=chat_id,
        text=(f"🐊 {round_info}\n\n"
              f"🎤 Объясняет: <b>{explainer.username}</b>\n"
              f"📝 Слово {lobby.words_explained_this_turn + 1}/{lobby.words_per_turn}\n\n"
              f"🔤 СЛОВО:\n\n<b>「 {word.upper()} 」</b>\n\n"
              f"Объясняй жестами и словами (не называй само слово!)"),
        reply_markup=reply_markup,
        parse_mode="HTML"
    )
    lobby.last_message_id = sent.message_id

async def croc_single_correct(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Угадали слово (одно устройство)"""
    query = update.callback_query
    await query.answer("✅ Отлично!")

    code = query.data.split("croc_single_correct_")[1]
    if code not in CROCODILE_LOBBIES:
        await query.edit_message_text("❌ Игра не найдена.")
        return

    lobby = CROCODILE_LOBBIES[code]
    explainer_id = lobby.get_current_explainer_id()
    lobby.scores[explainer_id] = lobby.scores.get(explainer_id, 0) + 1
    lobby.words_explained_this_turn += 1
    lobby.correct_this_turn += 1
    guessed_word = lobby.current_word

    await query.edit_message_text(
        f"✅ Угадано!\n\nСлово было: <b>{guessed_word}</b>\n+1 очко!\n\n{lobby.get_scoreboard()}",
        parse_mode="HTML"
    )
    await asyncio.sleep(2)

    try:
        await query.message.delete()
    except Exception:
        pass

    if lobby.words_explained_this_turn >= lobby.words_per_turn:
        lobby.next_turn()
        if lobby.is_game_over():
            await croc_end_game_single(context, code, query.message.chat_id)
        else:
            next_id = lobby.get_current_explainer_id()
            next_name = lobby.players[next_id].username
            keyboard = [[InlineKeyboardButton("▶️ Следующий игрок", callback_data=f"croc_single_next_{code}")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            sent = await context.bot.send_message(
                chat_id=query.message.chat_id,
                text=f"➡️ Следующий объясняет: <b>{next_name}</b>\n\n{lobby.get_scoreboard()}\n\nПередайте телефон!",
                reply_markup=reply_markup,
                parse_mode="HTML"
            )
            lobby.last_message_id = sent.message_id
    else:
        # Следующее слово того же игрока
        word = lobby.get_next_word()
        explainer = lobby.players[explainer_id]
        keyboard = [
            [InlineKeyboardButton("✅ Угадали!", callback_data=f"croc_single_correct_{code}")],
            [InlineKeyboardButton("⏭️ Пропустить", callback_data=f"croc_single_skip_{code}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        remaining = lobby.words_per_turn - lobby.words_explained_this_turn
        sent = await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=(f"🎤 {explainer.username} — слово {lobby.words_explained_this_turn + 1}/{lobby.words_per_turn}\n\n"
                  f"🔤 СЛОВО:\n\n<b>「 {word.upper()} 」</b>\n\n📝 Осталось слов: {remaining}"),
            reply_markup=reply_markup,
            parse_mode="HTML"
        )
        lobby.last_message_id = sent.message_id

async def croc_single_skip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Пропустить слово (одно устройство)"""
    query = update.callback_query
    await query.answer("⏭️ Пропущено")

    code = query.data.split("croc_single_skip_")[1]
    if code not in CROCODILE_LOBBIES:
        await query.edit_message_text("❌ Игра не найдена.")
        return

    lobby = CROCODILE_LOBBIES[code]
    skipped_word = lobby.current_word
    explainer_id = lobby.get_current_explainer_id()
    lobby.words_explained_this_turn += 1

    await query.edit_message_text(
        f"⏭️ Пропущено!\n\nСлово было: <b>{skipped_word}</b>",
        parse_mode="HTML"
    )
    await asyncio.sleep(1)

    try:
        await query.message.delete()
    except Exception:
        pass

    if lobby.words_explained_this_turn >= lobby.words_per_turn:
        lobby.next_turn()
        if lobby.is_game_over():
            await croc_end_game_single(context, code, query.message.chat_id)
        else:
            next_id = lobby.get_current_explainer_id()
            next_name = lobby.players[next_id].username
            keyboard = [[InlineKeyboardButton("▶️ Следующий игрок", callback_data=f"croc_single_next_{code}")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            sent = await context.bot.send_message(
                chat_id=query.message.chat_id,
                text=f"➡️ Следующий объясняет: <b>{next_name}</b>\n\n{lobby.get_scoreboard()}\n\nПередайте телефон!",
                reply_markup=reply_markup,
                parse_mode="HTML"
            )
            lobby.last_message_id = sent.message_id
    else:
        word = lobby.get_next_word()
        explainer = lobby.players[explainer_id]
        keyboard = [
            [InlineKeyboardButton("✅ Угадали!", callback_data=f"croc_single_correct_{code}")],
            [InlineKeyboardButton("⏭️ Пропустить", callback_data=f"croc_single_skip_{code}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        sent = await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=(f"🎤 {explainer.username} — слово {lobby.words_explained_this_turn + 1}/{lobby.words_per_turn}\n\n"
                  f"🔤 СЛОВО:\n\n<b>「 {word.upper()} 」</b>"),
            reply_markup=reply_markup,
            parse_mode="HTML"
        )
        lobby.last_message_id = sent.message_id

async def croc_single_next(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Переход к следующему игроку (одно устройство)"""
    query = update.callback_query
    await query.answer()

    code = query.data.split("croc_single_next_")[1]
    if code not in CROCODILE_LOBBIES:
        await query.edit_message_text("❌ Игра не найдена.")
        return

    try:
        await query.message.delete()
    except Exception:
        pass

    await croc_start_single_device(context, code, query.message.chat_id)

async def croc_end_game_single(context: ContextTypes.DEFAULT_TYPE, code: str, chat_id: int):
    """Конец игры крокодил (одно устройство)"""
    if code not in CROCODILE_LOBBIES:
        return
    lobby = CROCODILE_LOBBIES[code]

    sorted_scores = sorted(lobby.scores.items(), key=lambda x: x[1], reverse=True)
    winner_id, winner_score = sorted_scores[0]
    winner_name = lobby.players[winner_id].username

    result_text = f"🎉 ИГРА ОКОНЧЕНА!\n\n🏆 ПОБЕДИТЕЛЬ: {winner_name} ({winner_score} очков)!\n\n"
    result_text += lobby.get_scoreboard()

    await context.bot.send_message(chat_id=chat_id, text=result_text)
    del CROCODILE_LOBBIES[code]

# ============= КОМАНДЫ ШПИОНА (сетевой режим) =============

async def join_lobby(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Присоединиться к лобби шпиона"""
    user = update.effective_user
    if len(context.args) != 1:
        await update.message.reply_text("❌ Использование: /join <код>")
        return
    code = context.args[0].upper()
    if code not in LOBBIES:
        await update.message.reply_text(f"❌ Лобби {code} не найдено.")
        return
    lobby = LOBBIES[code]

    if lobby.single_device:
        await update.message.reply_text("❌ Это лобби для игры с одного устройства")
        return
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

    def lobby_text():
        return (
            f"✅ Лобби шпиона\n\n"
            f"📌 Код: <b>{lobby.code}</b>\n"
            f"🎯 Тема: {lobby.theme}\n"
            f"🌐 Режим: По сети\n"
            f"👥 Игроков: {len(lobby.players)}/10\n\n"
            f"📋 Список игроков:\n{lobby.get_players_list()}\n"
            f"Запусти игру:\n<code>/startgame {code}</code>"
        )

    sent = await update.message.reply_text(lobby_text(), parse_mode="HTML")
    lobby.lobby_message_ids[user.id] = sent.message_id

    for player_id in lobby.players:
        if player_id != user.id:
            await update_lobby_message(context, player_id, lobby, lobby_text())

async def players_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Список игроков в лобби"""
    if len(context.args) != 1:
        await update.message.reply_text("❌ Использование: /players <код>")
        return
    code = context.args[0].upper()
    if code not in LOBBIES:
        await update.message.reply_text("❌ Лобби не найдено.")
        return
    lobby = LOBBIES[code]
    players_list = lobby.get_players_list()
    text = f"👥 Игроки в лобби {code}:\n\n{players_list}Всего: {len(lobby.players)}/10"
    await update.message.reply_text(text)

async def leave_lobby(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выйти из лобби"""
    user = update.effective_user
    if len(context.args) != 1:
        await update.message.reply_text("❌ Использование: /leave <код>")
        return
    code = context.args[0].upper()
    if code not in LOBBIES:
        await update.message.reply_text("❌ Лобби не найдено.")
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
    """Начать игру шпион (сетевой режим)"""
    user = update.effective_user
    if len(context.args) != 1:
        await update.message.reply_text("❌ Использование: /startgame <код>")
        return
    code = context.args[0].upper()
    if code not in LOBBIES:
        await update.message.reply_text("❌ Лобби не найдено.")
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
            logger.error(f"Ошибка отправки роли игроку {player_id}: {e}")

    await update.message.reply_text("✅ ИГРА НАЧАЛАСЬ!\n\n📨 Все получили роли!\n\nГолосование через 120 секунд...")

    async def start_voting_task():
        await asyncio.sleep(120)
        await start_voting(context, code)

    context.application.create_task(start_voting_task())

# ============= ШПИОН - ОДНО УСТРОЙСТВО =============

async def spy_ready_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик готовности игрока (шпион одно устройство)"""
    query = update.callback_query
    await query.answer()

    code = query.data.split("_")[2]

    if code not in LOBBIES:
        await query.edit_message_text("❌ Лобби не найдено.")
        return

    lobby = LOBBIES[code]

    if lobby.current_reveal_index >= len(lobby.player_order):
        try:
            await context.bot.delete_message(
                chat_id=query.message.chat_id,
                message_id=lobby.last_message_id
            )
        except Exception as e:
            logger.warning(f"Не удалось удалить сообщение: {e}")

        keyboard = [[InlineKeyboardButton("🗳️ Начать голосование", callback_data=f"spy_vote_start_{lobby.code}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        sent_message = await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="✅ Все игроки узнали роли!\n\n⏰ Обсудите и начните голосование когда будете готовы:",
            reply_markup=reply_markup
        )
        lobby.last_message_id = sent_message.message_id
        return

    player_id = lobby.player_order[lobby.current_reveal_index]
    player = lobby.players[player_id]

    if player_id in lobby.spy_ids:
        role_text = (f"👤 Игрок {lobby.current_reveal_index + 1}: {player.username}\n\n"
                     f"🕵️ ТЫ - ШПИОН!\n\nУзнай локацию, не выдав себя!")
    else:
        role_text = (f"👤 Игрок {lobby.current_reveal_index + 1}: {player.username}\n\n"
                     f"🎯 ЛОКАЦИЯ: <b>{lobby.location}</b>\n\nНайди шпиона!")

    lobby.current_reveal_index += 1

    if lobby.current_reveal_index < len(lobby.player_order):
        keyboard = [[InlineKeyboardButton("➡️ Следующий игрок", callback_data=f"spy_next_{code}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(role_text, reply_markup=reply_markup, parse_mode="HTML")
    else:
        await query.edit_message_text(role_text + "\n\n✅ Это был последний игрок!", parse_mode="HTML")
        await asyncio.sleep(3)
        
        try:
            await context.bot.delete_message(
                chat_id=query.message.chat_id,
                message_id=lobby.last_message_id
            )
        except Exception as e:
            logger.warning(f"Не удалось удалить сообщение: {e}")
        
        keyboard = [[InlineKeyboardButton("🗳️ Начать голосование", callback_data=f"spy_vote_start_{code}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        sent_message = await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="⏰ Обсудите между собой!\n\nКогда будете готовы, начните голосование:",
            reply_markup=reply_markup
        )
        lobby.last_message_id = sent_message.message_id

async def spy_next_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Переход к следующему игроку"""
    query = update.callback_query
    await query.answer()

    code = query.data.split("_")[2]

    if code not in LOBBIES:
        await query.edit_message_text("❌ Лобби не найдено.")
        return

    lobby = LOBBIES[code]

    try:
        await query.message.delete()
    except Exception as e:
        logger.warning(f"Не удалось удалить сообщение: {e}")

    keyboard = [[InlineKeyboardButton("✅ Готов", callback_data=f"spy_ready_{code}")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    text = (f"👤 Передайте телефон Игроку {lobby.current_reveal_index + 1}\n\n"
            f"Нажмите «Готов» чтобы узнать роль")
    sent_message = await context.bot.send_message(chat_id=query.message.chat_id, text=text, reply_markup=reply_markup)
    lobby.last_message_id = sent_message.message_id

async def spy_vote_start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало голосования (одно устройство)"""
    query = update.callback_query
    await query.answer()
    code = query.data.split("_")[3]
    await start_voting_single_device(context, code, query.message.chat_id)

async def start_voting_single_device(context: ContextTypes.DEFAULT_TYPE, code: str, chat_id=None):
    """Начать голосование для одного устройства"""
    if code not in LOBBIES:
        return
    lobby = LOBBIES[code]
    lobby.voting = True

    keyboard = [[InlineKeyboardButton(f"🗳️ {player.username}", callback_data=f"vote_single_{code}_{player_id}")]
                for player_id, player in lobby.players.items()]
    reply_markup = InlineKeyboardMarkup(keyboard)
    text = "⏰ ГОЛОСОВАНИЕ!\n\nКто шпион?\n\nПередавайте телефон по кругу и голосуйте:"

    target_chat = chat_id or lobby.host_id
    await context.bot.send_message(chat_id=target_chat, text=text, reply_markup=reply_markup)

async def start_voting(context: ContextTypes.DEFAULT_TYPE, code: str):
    """Начать голосование для сетевого режима"""
    if code not in LOBBIES:
        return
    lobby = LOBBIES[code]
    lobby.voting = True
    keyboard = [[InlineKeyboardButton(f"🗳️ {player.username}", callback_data=f"vote_{code}_{player_id}")]
                for player_id, player in lobby.players.items()]
    reply_markup = InlineKeyboardMarkup(keyboard)
    text = "⏰ ГОЛОСОВАНИЕ!\n\nКто шпион?"
    for player_id in lobby.players:
        try:
            await context.bot.send_message(chat_id=player_id, text=text, reply_markup=reply_markup)
        except Exception as e:
            logger.error(f"Ошибка отправки голосования игроку {player_id}: {e}")

# ============= ГОЛОСОВАНИЕ ШПИОН =============

async def vote_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик голосования"""
    query = update.callback_query
    await query.answer()
    parts = query.data.split("_")

    if parts[1] == "single":
        # Голосование с одного устройства
        code = parts[2]
        votee_id = int(parts[3])

        if code not in LOBBIES:
            await query.edit_message_text("❌ Лобби не найдено.")
            return
        lobby = LOBBIES[code]

        votee_name = lobby.players[votee_id].username

        if votee_id not in lobby.votes:
            lobby.votes[votee_id] = 0
        lobby.votes[votee_id] += 1

        await query.answer(f"✅ Голос за {votee_name}", show_alert=True)

        total_votes = sum(lobby.votes.values())
        if total_votes >= len(lobby.players):
            await finish_voting_single_device(context, code, query.message.chat_id)
    else:
        # Сетевое голосование
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

async def finish_voting_single_device(context: ContextTypes.DEFAULT_TYPE, code: str, chat_id):
    """Завершение голосования (одно устройство)"""
    if code not in LOBBIES:
        return
    lobby = LOBBIES[code]

    if not lobby.votes:
        result_text = "🤝 НИЧЬЯ!\n\nШпион выжил! 🕵️"
    else:
        max_votes = max(lobby.votes.values())
        players_with_max = [uid for uid, count in lobby.votes.items() if count == max_votes]

        if len(players_with_max) > 1:
            result_text = "🤝 НИЧЬЯ!\n\nШпион выжил! 🕵️"
        else:
            expelled_id = players_with_max[0]
            expelled_name = lobby.players[expelled_id].username

            if expelled_id in lobby.spy_ids:
                result_text = f"🎉 ПОЙМАЛИ ШПИОНА!\n\n{expelled_name} БЫЛ ШПИОН!"
            else:
                result_text = f"❌ ОШИБКА!\n\n{expelled_name} — обычный игрок!\n\nШпион выжил!"

    result_text += "\n\n👥 РОЛИ:\n"
    for player_id, player in lobby.players.items():
        role = "🕵️ ШПИОН" if player_id in lobby.spy_ids else "👤 МИРНЫЙ"
        result_text += f"{player.username} — {role}\n"

    await context.bot.send_message(chat_id=chat_id, text=result_text)

    if code in LOBBIES:
        del LOBBIES[code]

async def finish_voting(context: ContextTypes.DEFAULT_TYPE, code: str):
    """Завершение голосования (сетевой режим)"""
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
            result_text = f"❌ ОШИБКА!\n\n{expelled_name} — обычный игрок!\n\nШпион выжил!"
            for spy_id in lobby.spy_ids:
                add_win(spy_id, lobby.players[spy_id].username)
            for player_id in lobby.players:
                if player_id not in lobby.spy_ids:
                    add_loss(player_id, lobby.players[player_id].username)

    for player_id in lobby.players:
        try:
            await context.bot.send_message(chat_id=player_id, text=result_text)
        except Exception as e:
            logger.error(f"Ошибка отправки результата игроку {player_id}: {e}")

    if code in LOBBIES:
        del LOBBIES[code]

# ============= КОМАНДЫ ДЛЯ МАФИИ (сетевой режим) =============

async def join_mafia(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Присоединиться к мафии"""
    user = update.effective_user
    if len(context.args) != 1:
        await update.message.reply_text("❌ Использование: /joinmafia <код>")
        return
    code = context.args[0].upper()
    if code not in MAFIA_LOBBIES:
        await update.message.reply_text(f"❌ Лобби {code} не найдено.")
        return
    lobby = MAFIA_LOBBIES[code]

    if lobby.single_device:
        await update.message.reply_text("❌ Это лобби для игры с одного устройства")
        return
    if lobby.started:
        await update.message.reply_text("❌ Игра уже началась.")
        return
    if user.id in lobby.players:
        await update.message.reply_text("❌ Ты уже в лобби.")
        return
    if not lobby.add_player(user.id, user.username or "Игрок"):
        await update.message.reply_text("❌ Лобби переполнено.")
        return

    def lobby_text():
        return (
            f"✅ Лобби мафии\n\n"
            f"📌 Код: <b>{lobby.code}</b>\n"
            f"🌐 Режим: По сети\n"
            f"👥 Игроков: {len(lobby.players)}/10\n\n"
            f"📋 Список игроков:\n{lobby.get_players_list()}\n"
            f"📍 Минимум 4 игрока\n\n"
            f"Запусти игру:\n<code>/startmafia {code}</code>"
        )

    sent = await update.message.reply_text(lobby_text(), parse_mode="HTML")
    lobby.lobby_message_ids[user.id] = sent.message_id

    for player_id in lobby.players:
        if player_id != user.id:
            await update_lobby_message(context, player_id, lobby, lobby_text())

async def mafia_players(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Список игроков мафии"""
    if len(context.args) != 1:
        await update.message.reply_text("❌ Использование: /mafiapl <код>")
        return
    code = context.args[0].upper()
    if code not in MAFIA_LOBBIES:
        await update.message.reply_text("❌ Лобби не найдено.")
        return
    lobby = MAFIA_LOBBIES[code]
    players_list = lobby.get_players_list(show_status=lobby.started)
    status_text = f"Фаза: {lobby.phase}\n" if lobby.started else ""
    text = f"👥 Игроки в лобби {code}:\n\n{players_list}{status_text}Всего: {len(lobby.players)}/10"
    await update.message.reply_text(text)

async def leave_mafia(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выйти из мафии"""
    user = update.effective_user
    if len(context.args) != 1:
        await update.message.reply_text("❌ Использование: /leavemafia <код>")
        return
    code = context.args[0].upper()
    if code not in MAFIA_LOBBIES:
        await update.message.reply_text("❌ Лобби не найдено.")
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
    """Начать игру мафия (сетевой режим)"""
    user = update.effective_user
    if len(context.args) != 1:
        await update.message.reply_text("❌ Использование: /startmafia <код>")
        return
    code = context.args[0].upper()
    if code not in MAFIA_LOBBIES:
        await update.message.reply_text("❌ Лобби не найдено.")
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
            logger.error(f"Ошибка отправки роли игроку {player_id}: {e}")

    await update.message.reply_text(f"✅ МАФИЯ НАЧАЛАСЬ!\n\n🌙 Ночь {lobby.day_number}\n📨 Все получили роли!")
    await asyncio.sleep(3)
    await start_night_phase(context, code)

# ============= МАФИЯ - ОДНО УСТРОЙСТВО =============

async def mafia_ready_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик готовности игрока (мафия одно устройство)"""
    query = update.callback_query
    await query.answer()

    code = query.data.split("_")[2]

    if code not in MAFIA_LOBBIES:
        await query.edit_message_text("❌ Лобби не найдено.")
        return

    lobby = MAFIA_LOBBIES[code]

    if lobby.current_reveal_index >= len(lobby.player_order):
        try:
            await context.bot.delete_message(
                chat_id=query.message.chat_id,
                message_id=lobby.last_message_id
            )
        except Exception as e:
            logger.warning(f"Не удалось удалить сообщение: {e}")

        sent_message = await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="✅ Все игроки узнали роли!\n\n🌙 Начинается первая ночь..."
        )
        lobby.last_message_id = sent_message.message_id
        await asyncio.sleep(3)
        await start_night_phase_single_device(context, code, query.message.chat_id)
        return

    player_id = lobby.player_order[lobby.current_reveal_index]
    player = lobby.players[player_id]

    role_emoji = {"мафия": "🔪", "комиссар": "👮", "доктор": "👨‍⚕️", "мирный": "👤"}
    role_name = player.role.upper()
    emoji = role_emoji.get(player.role, "👤")

    role_text = f"👤 Игрок {lobby.current_reveal_index + 1}: {player.username}\n\n{emoji} ТВОЯ РОЛЬ: <b>{role_name}</b>\n\n"

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

    lobby.current_reveal_index += 1

    if lobby.current_reveal_index < len(lobby.player_order):
        keyboard = [[InlineKeyboardButton("➡️ Следующий игрок", callback_data=f"mafia_next_{code}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(role_text, reply_markup=reply_markup, parse_mode="HTML")
    else:
        await query.edit_message_text(role_text + "\n\n✅ Это был последний игрок!", parse_mode="HTML")
        await asyncio.sleep(3)
        
        try:
            await context.bot.delete_message(
                chat_id=query.message.chat_id,
                message_id=lobby.last_message_id
            )
        except Exception as e:
            logger.warning(f"Не удалось удалить сообщение: {e}")
        
        sent_message = await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="🌙 Начинается первая ночь..."
        )
        lobby.last_message_id = sent_message.message_id
        await asyncio.sleep(2)
        await start_night_phase_single_device(context, code, query.message.chat_id)

async def mafia_next_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Переход к следующему игроку (мафия)"""
    query = update.callback_query
    await query.answer()

    code = query.data.split("_")[2]

    if code not in MAFIA_LOBBIES:
        await query.edit_message_text("❌ Лобби не найдено.")
        return

    lobby = MAFIA_LOBBIES[code]

    try:
        await query.message.delete()
    except Exception as e:
        logger.warning(f"Не удалось удалить сообщение: {e}")

    keyboard = [[InlineKeyboardButton("✅ Готов", callback_data=f"mafia_ready_{code}")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    text = (f"👤 Передайте телефон Игроку {lobby.current_reveal_index + 1}\n\n"
            f"Нажмите «Готов» чтобы узнать роль")
    sent_message = await context.bot.send_message(chat_id=query.message.chat_id, text=text, reply_markup=reply_markup)
    lobby.last_message_id = sent_message.message_id

# ============= НОЧНЫЕ ДЕЙСТВИЯ (ОДНО УСТРОЙСТВО) - ПОЛНОСТЬЮ ИСПРАВЛЕНО! =============

async def mafia_night_action_single(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    ИСПРАВЛЕНО: Завершенная логика ночных действий для одного устройства
    """
    query = update.callback_query
    await query.answer()

    parts = query.data.split("_")
    # ИСПРАВЛЕНО: правильный разбор callback_data
    # Формат: mafia_ACTION_single_CODE_TARGETID
    action = parts[1]  # kill, heal, check
    # parts[2] это "single" - пропускаем
    code = parts[3]
    target_id = int(parts[4])

    if code not in MAFIA_LOBBIES:
        await query.edit_message_text("❌ Игра не найдена.")
        return

    lobby = MAFIA_LOBBIES[code]
    target_name = lobby.players[target_id].username

    if action == "kill":
        # Мафия выбрала жертву
        for mid in lobby.get_alive_mafia():
            lobby.add_night_action(mid, target_id)

        await query.edit_message_text(f"🔪 Мафия выбрала: {target_name}")
        await asyncio.sleep(2)

        # Удаляем предыдущее сообщение
        try:
            await query.message.delete()
        except Exception as e:
            logger.warning(f"Не удалось удалить сообщение: {e}")

        # Переход к доктору если жив
        if lobby.doctor_id and lobby.players[lobby.doctor_id].alive:
            keyboard = [[InlineKeyboardButton(f"💊 {p.username}", callback_data=f"mafia_heal_single_{code}_{pid}")]
                        for pid, p in lobby.get_alive_players().items()]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            doctor_name = lobby.players[lobby.doctor_id].username
            text = f"👨‍⚕️ ДОКТОР ({doctor_name})\nВыберите, кого лечить:"
            sent_message = await context.bot.send_message(chat_id=query.message.chat_id, text=text, reply_markup=reply_markup)
            lobby.last_message_id = sent_message.message_id
            return

        # Если доктора нет, переход к комиссару
        elif lobby.komissar_id and lobby.players[lobby.komissar_id].alive:
            await asyncio.sleep(1)
            keyboard = [[InlineKeyboardButton(f"🔍 {p.username}", callback_data=f"mafia_check_single_{code}_{pid}")]
                        for pid, p in lobby.get_alive_players().items() if pid != lobby.komissar_id]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            komissar_name = lobby.players[lobby.komissar_id].username
            text = f"👮 КОМИССАР ({komissar_name})\nВыберите, кого проверить:"
            sent_message = await context.bot.send_message(chat_id=query.message.chat_id, text=text, reply_markup=reply_markup)
            lobby.last_message_id = sent_message.message_id
            return
        else:
            # Нет ни доктора, ни комиссара - завершаем ночь
            await asyncio.sleep(1)
            await end_night_phase_single_device(context, code, query.message.chat_id)
            return

    elif action == "heal":
        # Доктор выбрал кого лечить
        if lobby.doctor_id:
            lobby.add_night_action(lobby.doctor_id, target_id)

        await query.edit_message_text(f"💊 Доктор лечит: {target_name}")
        await asyncio.sleep(2)

        # Удаляем предыдущее сообщение
        try:
            await query.message.delete()
        except Exception as e:
            logger.warning(f"Не удалось удалить сообщение: {e}")

        # Переход к комиссару если жив
        if lobby.komissar_id and lobby.players[lobby.komissar_id].alive:
            keyboard = [[InlineKeyboardButton(f"🔍 {p.username}", callback_data=f"mafia_check_single_{code}_{pid}")]
                        for pid, p in lobby.get_alive_players().items() if pid != lobby.komissar_id]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            komissar_name = lobby.players[lobby.komissar_id].username
            text = f"👮 КОМИССАР ({komissar_name})\nВыберите, кого проверить:"
            sent_message = await context.bot.send_message(chat_id=query.message.chat_id, text=text, reply_markup=reply_markup)
            lobby.last_message_id = sent_message.message_id
            return
        else:
            # Комиссара нет - завершаем ночь
            await asyncio.sleep(1)
            await end_night_phase_single_device(context, code, query.message.chat_id)
            return

    elif action == "check":
        # Комиссар проверил игрока
        if lobby.komissar_id:
            lobby.add_night_action(lobby.komissar_id, target_id)

        if target_id in lobby.mafia_ids:
            result = "🔴 МАФИЯ!"
        else:
            result = "🟢 Мирный житель"

        await query.edit_message_text(f"🔍 Комиссар проверил {target_name}:\n{result}")
        await asyncio.sleep(3)
        
        # Удаляем предыдущее сообщение
        try:
            await query.message.delete()
        except Exception as e:
            logger.warning(f"Не удалось удалить сообщение: {e}")
        
        # Все роли отработали - завершаем ночь
        await end_night_phase_single_device(context, code, query.message.chat_id)
        return

async def start_night_phase_single_device(context: ContextTypes.DEFAULT_TYPE, code: str, chat_id):
    """Начало ночной фазы (одно устройство)"""
    if code not in MAFIA_LOBBIES:
        return

    lobby = MAFIA_LOBBIES[code]

    # Проверяем есть ли живая мафия
    mafia_players_list = [lobby.players[mid] for mid in lobby.get_alive_mafia()]
    if mafia_players_list:
        mafia_names = ', '.join([p.username for p in mafia_players_list])
        
        keyboard = [[InlineKeyboardButton(f"🔪 {p.username}", callback_data=f"mafia_kill_single_{code}_{pid}")]
                    for pid, p in lobby.get_alive_players().items() if pid not in lobby.mafia_ids]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        text = f"🌙 НОЧЬ {lobby.day_number}\n\n🔪 МАФИЯ ({mafia_names})\nВыберите жертву:"
        sent_message = await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup)
        lobby.last_message_id = sent_message.message_id
        return

    # Мафии нет - сразу переходим к утру
    await end_night_phase_single_device(context, code, chat_id)

async def end_night_phase_single_device(context: ContextTypes.DEFAULT_TYPE, code: str, chat_id):
    """Завершение ночной фазы (одно устройство)"""
    if code not in MAFIA_LOBBIES:
        return

    lobby = MAFIA_LOBBIES[code]
    lobby.process_night()

    night_report = f"☀️ УТРО НАСТУПИЛО!\n\nДень {lobby.day_number}\n\n"

    if lobby.last_killed:
        killed_name = lobby.players[lobby.last_killed].username
        killed_role = lobby.players[lobby.last_killed].role
        role_emoji = {"мафия": "🔪", "комиссар": "👮", "доктор": "👨‍⚕️", "мирный": "👤"}
        emoji = role_emoji.get(killed_role, "👤")
        night_report += f"💀 Ночью погиб: {killed_name} {emoji} ({killed_role})\n"
    elif lobby.last_saved:
        night_report += "💊 Доктор спас жителя!\n"
    else:
        night_report += "✅ Ночь прошла спокойно\n"

    sent_message = await context.bot.send_message(chat_id=chat_id, text=night_report)
    lobby.last_message_id = sent_message.message_id

    win_condition = lobby.check_win_condition()
    if win_condition:
        await end_mafia_game_single_device(context, code, win_condition, chat_id)
        return

    await asyncio.sleep(3)
    await start_day_voting_single_device(context, code, chat_id)

async def start_day_voting_single_device(context: ContextTypes.DEFAULT_TYPE, code: str, chat_id):
    """Дневное голосование (одно устройство)"""
    if code not in MAFIA_LOBBIES:
        return

    lobby = MAFIA_LOBBIES[code]
    lobby.votes = {}
    for player in lobby.players.values():
        player.voted = False

    alive_players = list(lobby.get_alive_players().values())
    keyboard = [[InlineKeyboardButton(f"🗳️ {p.username}", callback_data=f"mafia_vote_single_{code}_{p.user_id}")]
                for p in alive_players]
    keyboard.append([InlineKeyboardButton("⏭️ Пропустить день", callback_data=f"mafia_vote_single_{code}_skip")])
    reply_markup = InlineKeyboardMarkup(keyboard)

    text = "☀️ ДНЕВНОЕ ГОЛОСОВАНИЕ!\n\nОбсудите и проголосуйте, кого выгнать из города:"
    sent_message = await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup)
    lobby.last_message_id = sent_message.message_id

async def mafia_day_vote_single(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Голосование днем (одно устройство)"""
    query = update.callback_query
    await query.answer()

    parts = query.data.split("_")
    code = parts[3]
    target = parts[4]

    if code not in MAFIA_LOBBIES:
        await query.edit_message_text("❌ Игра не найдена.")
        return

    lobby = MAFIA_LOBBIES[code]

    if target == "skip":
        await query.edit_message_text("⏭️ День пропущен")
        await asyncio.sleep(2)
        try:
            await query.message.delete()
        except Exception as e:
            logger.warning(f"Не удалось удалить сообщение: {e}")
        await end_day_voting_single_device(context, code, query.message.chat_id, skip=True)
    else:
        target_id = int(target)
        if target_id not in lobby.players or not lobby.players[target_id].alive:
            await query.edit_message_text("❌ Игрок не найден.")
            return

        target_name = lobby.players[target_id].username

        keyboard = [[InlineKeyboardButton("✅ Подтвердить", callback_data=f"mafia_confirm_single_{code}_{target_id}")],
                    [InlineKeyboardButton("🔄 Переголосовать", callback_data=f"mafia_revote_single_{code}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(f"Город решил выгнать: {target_name}\n\nПодтвердить?", reply_markup=reply_markup)

async def mafia_confirm_vote_single(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Подтверждение голосования"""
    query = update.callback_query
    await query.answer()

    parts = query.data.split("_")
    code = parts[3]
    target_id = int(parts[4])

    if code not in MAFIA_LOBBIES:
        await query.edit_message_text("❌ Игра не найдена.")
        return

    try:
        await query.message.delete()
    except Exception as e:
        logger.warning(f"Не удалось удалить сообщение: {e}")

    await end_day_voting_single_device(context, code, query.message.chat_id, expelled_id=target_id)

async def mafia_revote_single(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Переголосование"""
    query = update.callback_query
    await query.answer()

    code = query.data.split("_")[3]

    if code not in MAFIA_LOBBIES:
        await query.edit_message_text("❌ Игра не найдена.")
        return

    try:
        await query.message.delete()
    except Exception as e:
        logger.warning(f"Не удалось удалить сообщение: {e}")

    await start_day_voting_single_device(context, code, query.message.chat_id)

async def end_day_voting_single_device(context: ContextTypes.DEFAULT_TYPE, code: str, chat_id, skip=False, expelled_id=None):
    """Завершение дневного голосования (одно устройство)"""
    if code not in MAFIA_LOBBIES:
        return

    lobby = MAFIA_LOBBIES[code]

    day_result = "📊 РЕЗУЛЬТАТЫ ГОЛОСОВАНИЯ:\n\n"

    if skip or expelled_id is None:
        day_result += "🤝 Город не смог принять решение!\n"
    else:
        expelled_name = lobby.players[expelled_id].username
        expelled_role = lobby.players[expelled_id].role
        lobby.players[expelled_id].alive = False

        role_emoji = {"мафия": "🔪", "комиссар": "👮", "доктор": "👨‍⚕️", "мирный": "👤"}
        emoji = role_emoji.get(expelled_role, "👤")

        day_result += f"💀 Изгнан: {expelled_name}\n"
        day_result += f"{emoji} Роль: {expelled_role.upper()}\n"

    sent_message = await context.bot.send_message(chat_id=chat_id, text=day_result)
    lobby.last_message_id = sent_message.message_id

    win_condition = lobby.check_win_condition()
    if win_condition:
        await end_mafia_game_single_device(context, code, win_condition, chat_id)
        return

    lobby.day_number += 1
    lobby.phase = "night"

    await asyncio.sleep(3)
    
    try:
        await context.bot.delete_message(chat_id=chat_id, message_id=lobby.last_message_id)
    except Exception as e:
        logger.warning(f"Не удалось удалить сообщение: {e}")
    
    sent_message = await context.bot.send_message(chat_id=chat_id, text=f"🌙 Наступает ночь {lobby.day_number}...")
    lobby.last_message_id = sent_message.message_id
    await asyncio.sleep(2)
    await start_night_phase_single_device(context, code, chat_id)

async def end_mafia_game_single_device(context: ContextTypes.DEFAULT_TYPE, code: str, winner: str, chat_id):
    """Завершение игры мафия (одно устройство)"""
    if code not in MAFIA_LOBBIES:
        return

    lobby = MAFIA_LOBBIES[code]

    if winner == "civilians":
        result_text = "🎉 ПОБЕДА МИРНЫХ ЖИТЕЛЕЙ!\n\nВся мафия повержена!\n\n"
    else:
        result_text = "🔪 ПОБЕДА МАФИИ!\n\nМафия захватила город!\n\n"

    result_text += "👥 РОЛИ:\n"
    for player_id, player in lobby.players.items():
        role_emoji = {"мафия": "🔪", "комиссар": "👮", "доктор": "👨‍⚕️", "мирный": "👤"}
        emoji = role_emoji.get(player.role, "👤")
        status = "💀" if not player.alive else "✅"
        result_text += f"{emoji} {player.username} — {player.role} {status}\n"

    await context.bot.send_message(chat_id=chat_id, text=result_text)

    del MAFIA_LOBBIES[code]

# ============= НОЧНЫЕ ДЕЙСТВИЯ (СЕТЕВОЙ РЕЖИМ) =============

async def start_night_phase(context: ContextTypes.DEFAULT_TYPE, code: str):
    """Начало ночной фазы (сетевой режим)"""
    if code not in MAFIA_LOBBIES:
        return
    lobby = MAFIA_LOBBIES[code]

    # Мафия выбирает жертву
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
        except Exception as e:
            logger.error(f"Ошибка отправки ночного действия мафии {mafia_id}: {e}")

    # Доктор выбирает кого лечить
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
        except Exception as e:
            logger.error(f"Ошибка отправки ночного действия доктору: {e}")

    # Комиссар выбирает кого проверить
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
        except Exception as e:
            logger.error(f"Ошибка отправки ночного действия комиссару: {e}")

    # Проверка завершения ночи
    async def check_night_complete():
        for _ in range(60):  # 120 секунд таймаут
            await asyncio.sleep(2)
            if code not in MAFIA_LOBBIES:
                return
            if lobby.check_night_actions_complete():
                await end_night_phase(context, code)
                return

        # Таймаут - завершаем ночь принудительно
        if code in MAFIA_LOBBIES:
            await end_night_phase(context, code)

    context.application.create_task(check_night_complete())

async def mafia_night_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ночных действий (сетевой режим)"""
    query = update.callback_query
    await query.answer()

    parts = query.data.split("_")
    action = parts[1]  # kill, heal, check
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
    """Завершение ночной фазы (сетевой режим)"""
    if code not in MAFIA_LOBBIES:
        return

    lobby = MAFIA_LOBBIES[code]
    lobby.process_night()

    night_report = f"☀️ УТРО НАСТУПИЛО!\n\nДень {lobby.day_number}\n\n"

    if lobby.last_killed:
        killed_name = lobby.players[lobby.last_killed].username
        killed_role = lobby.players[lobby.last_killed].role
        role_emoji = {"мафия": "🔪", "комиссар": "👮", "доктор": "👨‍⚕️", "мирный": "👤"}
        emoji = role_emoji.get(killed_role, "👤")
        night_report += f"💀 Ночью погиб: {killed_name} {emoji} ({killed_role})\n"
    elif lobby.last_saved:
        night_report += "💊 Доктор спас жителя!\n"
    else:
        night_report += "✅ Ночь прошла спокойно\n"

    for player_id in lobby.players:
        try:
            await context.bot.send_message(chat_id=player_id, text=night_report)
        except Exception as e:
            logger.error(f"Ошибка отправки отчета о ночи игроку {player_id}: {e}")

    win_condition = lobby.check_win_condition()
    if win_condition:
        await end_mafia_game(context, code, win_condition)
        return

    await asyncio.sleep(3)
    await start_day_voting(context, code)

async def start_day_voting(context: ContextTypes.DEFAULT_TYPE, code: str):
    """Начало дневного голосования (сетевой режим)"""
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
        except Exception as e:
            logger.error(f"Ошибка отправки голосования игроку {player_id}: {e}")

    # Проверка завершения голосования
    async def check_votes_complete():
        for _ in range(60):  # 120 секунд таймаут
            await asyncio.sleep(2)
            if code not in MAFIA_LOBBIES:
                return
            alive_count = len(lobby.get_alive_players())
            if len(lobby.votes) >= alive_count:
                await end_day_voting(context, code)
                return

        # Таймаут
        if code in MAFIA_LOBBIES:
            await end_day_voting(context, code)

    context.application.create_task(check_votes_complete())

async def mafia_day_vote(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка дневного голосования (сетевой режим)"""
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
    """Завершение дневного голосования (сетевой режим)"""
    if code not in MAFIA_LOBBIES:
        return

    lobby = MAFIA_LOBBIES[code]
    expelled_id, max_votes = lobby.get_vote_results()

    day_result = "📊 РЕЗУЛЬТАТЫ ГОЛОСОВАНИЯ:\n\n"

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
        except Exception as e:
            logger.error(f"Ошибка отправки результата голосования игроку {player_id}: {e}")

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
        except Exception as e:
            logger.error(f"Ошибка отправки уведомления о ночи игроку {player_id}: {e}")

    await asyncio.sleep(2)
    await start_night_phase(context, code)

async def end_mafia_game(context: ContextTypes.DEFAULT_TYPE, code: str, winner: str):
    """Завершение игры мафия (сетевой режим)"""
    if code not in MAFIA_LOBBIES:
        return

    lobby = MAFIA_LOBBIES[code]

    if winner == "civilians":
        result_text = "🎉 ПОБЕДА МИРНЫХ ЖИТЕЛЕЙ!\n\nВся мафия повержена!\n\n"

        for player_id, player in lobby.players.items():
            if player_id not in lobby.mafia_ids:
                add_win(player_id, player.username)
            else:
                add_loss(player_id, player.username)

    else:
        result_text = "🔪 ПОБЕДА МАФИИ!\n\nМафия захватила город!\n\n"

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
        result_text += f"{emoji} {player.username} — {player.role} {status}\n"

    for player_id in lobby.players:
        try:
            await context.bot.send_message(chat_id=player_id, text=result_text)
        except Exception as e:
            logger.error(f"Ошибка отправки результата игры игроку {player_id}: {e}")

    del MAFIA_LOBBIES[code]

# ============= ОБРАБОТКА ОШИБОК =============

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    """Глобальный обработчик ошибок"""
    logger.error(f"Исключение при обработке обновления: {context.error}", exc_info=context.error)
    
    try:
        if isinstance(update, Update) and update.effective_message:
            await update.effective_message.reply_text(
                "❌ Произошла ошибка. Попробуйте позже или обратитесь к администратору."
            )
    except Exception as e:
        logger.error(f"Не удалось отправить сообщение об ошибке: {e}")

# ============= MAIN =============

def main():
    """Основная функция запуска бота"""
    try:
        # Инициализация БД
        init_db()
        logger.info("=" * 50)
        logger.info("✅ Бот запущен!")
        logger.info("=" * 50)

        # Создание приложения
        app = ApplicationBuilder().token(BOT_TOKEN).build()

        # Основные команды
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("help", help_command))
        app.add_handler(CommandHandler("stats", stats_command))
        app.add_handler(CommandHandler("top", top_command))

        # Команды для игры Шпион
        app.add_handler(CommandHandler("join", join_lobby))
        app.add_handler(CommandHandler("players", players_command))
        app.add_handler(CommandHandler("leave", leave_lobby))
        app.add_handler(CommandHandler("startgame", start_game))

        # Команды для игры Мафия
        app.add_handler(CommandHandler("joinmafia", join_mafia))
        app.add_handler(CommandHandler("mafiapl", mafia_players))
        app.add_handler(CommandHandler("leavemafia", leave_mafia))
        app.add_handler(CommandHandler("startmafia", start_mafia_game))
               
        # Команды для игры Крокодил
        app.add_handler(CommandHandler("joincrocodile", join_crocodile))
        app.add_handler(CommandHandler("startcrocodile", start_crocodile_game))

        app.add_handler(CommandHandler("jointod", join_tod))
        app.add_handler(CommandHandler("starttod", start_tod_game))

        # Обработчик текстовых сообщений
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_player_count_input))

        # Callback handlers - основные
        app.add_handler(CallbackQueryHandler(game_choice, pattern=r"^game_"))
        app.add_handler(CallbackQueryHandler(theme_selected, pattern=r"^theme_"))
        app.add_handler(CallbackQueryHandler(spy_mode_selected, pattern=r"^spy_mode_"))
        app.add_handler(CallbackQueryHandler(mafia_mode_selected, pattern=r"^mafia_mode_"))

        app.add_handler(CallbackQueryHandler(tod_rating_selected, pattern=r"^tod_rating_"))
        app.add_handler(CallbackQueryHandler(tod_device_selected, pattern=r"^tod_device_"))
        app.add_handler(CallbackQueryHandler(tod_choose_handler, pattern=r"^tod_choose_"))
        app.add_handler(CallbackQueryHandler(tod_done_handler, pattern=r"^tod_done_"))
        app.add_handler(CallbackQueryHandler(tod_skip_handler, pattern=r"^tod_skip_"))
               
        # Callback handlers - Крокодил
        app.add_handler(CallbackQueryHandler(croc_difficulty_selected, pattern=r"^croc_diff_"))
        app.add_handler(CallbackQueryHandler(croc_mode_selected, pattern=r"^croc_mode_"))
        app.add_handler(CallbackQueryHandler(croc_correct_handler, pattern=r"^croc_correct_"))
        app.add_handler(CallbackQueryHandler(croc_skip_handler, pattern=r"^croc_skip_"))
        app.add_handler(CallbackQueryHandler(croc_single_correct, pattern=r"^croc_single_correct_"))
        app.add_handler(CallbackQueryHandler(croc_single_skip, pattern=r"^croc_single_skip_"))
        app.add_handler(CallbackQueryHandler(croc_single_next, pattern=r"^croc_single_next_"))


        # Callback handlers - Шпион одно устройство
        app.add_handler(CallbackQueryHandler(spy_ready_handler, pattern=r"^spy_ready_"))
        app.add_handler(CallbackQueryHandler(spy_next_handler, pattern=r"^spy_next_"))
        app.add_handler(CallbackQueryHandler(spy_vote_start_handler, pattern=r"^spy_vote_start_"))

        # Callback handlers - Мафия одно устройство
        app.add_handler(CallbackQueryHandler(mafia_ready_handler, pattern=r"^mafia_ready_"))
        app.add_handler(CallbackQueryHandler(mafia_next_handler, pattern=r"^mafia_next_"))
        app.add_handler(CallbackQueryHandler(mafia_night_action_single, pattern=r"^mafia_(kill|heal|check)_single_"))
        app.add_handler(CallbackQueryHandler(mafia_day_vote_single, pattern=r"^mafia_vote_single_"))
        app.add_handler(CallbackQueryHandler(mafia_confirm_vote_single, pattern=r"^mafia_confirm_single_"))
        app.add_handler(CallbackQueryHandler(mafia_revote_single, pattern=r"^mafia_revote_single_"))

        # Callback handlers - голосование и действия
        app.add_handler(CallbackQueryHandler(vote_handler, pattern=r"^vote_"))
        app.add_handler(CallbackQueryHandler(mafia_night_action, pattern=r"^mafia_(kill|heal|check)_"))
        app.add_handler(CallbackQueryHandler(mafia_day_vote, pattern=r"^mafia_vote_"))

        # Обработчик ошибок
        app.add_error_handler(error_handler)

        # Запуск бота
        logger.info("🤖 Бот начинает получать обновления...")
        app.run_polling(allowed_updates=Update.ALL_TYPES)

    except Exception as e:
        logger.critical(f"❌ Критическая ошибка при запуске бота: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main()
