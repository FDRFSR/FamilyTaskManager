import os
import logging
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from telegram.constants import ParseMode
import psycopg2
import psycopg2.extras

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

class FamilyTaskDB:
    def __init__(self):
        self.conn = psycopg2.connect(os.environ["DATABASE_URL"], cursor_factory=psycopg2.extras.RealDictCursor)
        self.ensure_tables()

    def ensure_tables(self):
        with self.conn, self.conn.cursor() as cur:
            with open(os.path.join(os.path.dirname(__file__), "schema.sql")) as f:
                cur.execute(f.read())

    def get_default_tasks(self):
        # Carica task di default solo se non esistono, poi restituisce dizionario indicizzato per id
        with self.conn, self.conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM tasks;")
            if cur.fetchone()[0] == 0:
                default = [
                    ("cucina_pulizia", "🍽️ Pulire la cucina", 15, 30),
                    ("bagno_pulizia", "🚿 Pulire il bagno", 20, 40),
                    ("aspirapolvere", "🧹 Passare l'aspirapolvere", 12, 25),
                    ("lavastoviglie", "🍴 Caricare/svuotare lavastoviglie", 8, 15),
                    ("bucato", "👕 Fare il bucato", 10, 20),
                    ("stirare", "👔 Stirare", 18, 35),
                    ("spazzatura", "🗑️ Portare fuori la spazzatura", 5, 10),
                    ("giardino", "🌱 Curare il giardino", 25, 50),
                    ("spesa", "🛒 Fare la spesa", 15, 30),
                    ("letti", "🛏️ Rifare i letti", 6, 12),
                    ("pavimenti", "🧽 Lavare i pavimenti", 20, 40),
                    ("finestre", "🪟 Pulire le finestre", 22, 45)
                ]
                cur.executemany("INSERT INTO tasks (id, name, points, time_minutes) VALUES (%s, %s, %s, %s)", default)
            cur.execute("SELECT * FROM tasks")
            return {row['id']: dict(row) for row in cur.fetchall()}

    def get_all_tasks(self):
        with self.conn, self.conn.cursor() as cur:
            cur.execute("SELECT * FROM tasks")
            return cur.fetchall()

    def get_task_by_id(self, task_id: str):
        with self.conn, self.conn.cursor() as cur:
            cur.execute("SELECT * FROM tasks WHERE id = %s", (task_id,))
            return cur.fetchone()

    def get_assigned_tasks_for_chat(self, chat_id: int):
        with self.conn, self.conn.cursor() as cur:
            cur.execute("SELECT * FROM assigned_tasks WHERE chat_id = %s", (chat_id,))
            return cur.fetchall()

    def get_user_assigned_tasks(self, chat_id: int, user_id: int):
        with self.conn, self.conn.cursor() as cur:
            cur.execute("""
                SELECT at.task_id, at.due_date, t.name, t.points, t.time_minutes
                FROM assigned_tasks at
                JOIN tasks t ON at.task_id = t.id
                WHERE at.chat_id = %s AND at.assigned_to = %s
            """, (chat_id, user_id))
            return cur.fetchall()

    def add_family_member(self, chat_id: int, user_id: int, username: str, first_name: str):
        with self.conn, self.conn.cursor() as cur:
            # Crea la famiglia se non esiste
            cur.execute("INSERT INTO families (chat_id) VALUES (%s) ON CONFLICT (chat_id) DO NOTHING", (chat_id,))
            
            # Aggiungi il membro della famiglia
            cur.execute("""
                INSERT INTO family_members (chat_id, user_id, username, first_name, joined_date) 
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (chat_id, user_id) DO UPDATE SET
                username = EXCLUDED.username,
                first_name = EXCLUDED.first_name
            """, (chat_id, user_id, username, first_name, datetime.now()))
            self.conn.commit()

    def get_family_members(self, chat_id: int):
        with self.conn, self.conn.cursor() as cur:
            cur.execute("SELECT * FROM family_members WHERE chat_id = %s", (chat_id,))
            return cur.fetchall()

    def assign_task(self, chat_id: int, task_id: str, assigned_to: int, assigned_by: int):
        with self.conn, self.conn.cursor() as cur:
            cur.execute(
                "INSERT INTO assigned_tasks (chat_id, task_id, assigned_to, assigned_by, assigned_date, status, due_date) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                (chat_id, task_id, assigned_to, assigned_by, datetime.now(), 'pending', datetime.now() + timedelta(days=3))
            )
            self.conn.commit()

    def check_and_assign_badges(self, user_id: int, stats: dict) -> list:
        badges = stats.get('badges', [])
        nuovi = []
        if stats['tasks_completed'] >= 10 and 'rookie' not in badges:
            badges.append('rookie')
            nuovi.append('rookie')
        if stats['tasks_completed'] >= 50 and 'expert' not in badges:
            badges.append('expert')
            nuovi.append('expert')
        if stats['tasks_completed'] >= 100 and 'master' not in badges:
            badges.append('master')
            nuovi.append('master')
        if stats['streak'] >= 7 and 'week_warrior' not in badges:
            badges.append('week_warrior')
            nuovi.append('week_warrior')
        if stats['streak'] >= 30 and 'month_champion' not in badges:
            badges.append('month_champion')
            nuovi.append('month_champion')
        if stats['total_points'] >= 500 and 'point_collector' not in badges:
            badges.append('point_collector')
            nuovi.append('point_collector')
        stats['badges'] = badges
        return nuovi

    def complete_task(self, chat_id: int, task_id: str, user_id: int):
        with self.conn, self.conn.cursor() as cur:
            # Verifica che la task sia assegnata all'utente
            cur.execute("SELECT * FROM assigned_tasks WHERE chat_id = %s AND task_id = %s AND assigned_to = %s", (chat_id, task_id, user_id))
            task_data = cur.fetchone()
            if not task_data:
                return 0, {"level_up": False, "new_level": None, "new_badges": []}
            
            # Ottieni informazioni della task
            cur.execute("SELECT * FROM tasks WHERE id = %s", (task_id,))
            task_info = cur.fetchone()
            if not task_info:
                return 0, {"level_up": False, "new_level": None, "new_badges": []}
                
            points = task_info['points']
            msg = {"level_up": False, "new_level": None, "new_badges": []}
            
            # Ottieni o crea statistiche utente
            cur.execute("SELECT * FROM user_stats WHERE user_id = %s", (user_id,))
            stats = cur.fetchone()
            
            if stats:
                old_level = stats['level']
                new_total_points = stats['total_points'] + points
                new_level = new_total_points // 100 + 1
                new_tasks_completed = stats['tasks_completed'] + 1
                
                # Calcola streak (semplificato per ora)
                new_streak = stats['streak'] + 1
                
                cur.execute("""
                    UPDATE user_stats 
                    SET total_points = %s, tasks_completed = %s, level = %s, 
                        streak = %s, last_task_date = %s 
                    WHERE user_id = %s
                """, (new_total_points, new_tasks_completed, new_level, new_streak, datetime.now(), user_id))
                
                if new_level > old_level:
                    msg["level_up"] = True
                    msg["new_level"] = new_level
                    
                # Controlla badge
                if new_tasks_completed >= 10:
                    cur.execute("SELECT * FROM badges WHERE user_id = %s AND name = %s", (user_id, 'rookie'))
                    if not cur.fetchone():
                        cur.execute("INSERT INTO badges (user_id, name) VALUES (%s, %s)", (user_id, 'rookie'))
                        msg["new_badges"].append('rookie')
                        
                if new_tasks_completed >= 50:
                    cur.execute("SELECT * FROM badges WHERE user_id = %s AND name = %s", (user_id, 'expert'))
                    if not cur.fetchone():
                        cur.execute("INSERT INTO badges (user_id, name) VALUES (%s, %s)", (user_id, 'expert'))
                        msg["new_badges"].append('expert')
                        
                if new_tasks_completed >= 100:
                    cur.execute("SELECT * FROM badges WHERE user_id = %s AND name = %s", (user_id, 'master'))
                    if not cur.fetchone():
                        cur.execute("INSERT INTO badges (user_id, name) VALUES (%s, %s)", (user_id, 'master'))
                        msg["new_badges"].append('master')
                        
                if new_streak >= 7:
                    cur.execute("SELECT * FROM badges WHERE user_id = %s AND name = %s", (user_id, 'week_warrior'))
                    if not cur.fetchone():
                        cur.execute("INSERT INTO badges (user_id, name) VALUES (%s, %s)", (user_id, 'week_warrior'))
                        msg["new_badges"].append('week_warrior')
                        
                if new_streak >= 30:
                    cur.execute("SELECT * FROM badges WHERE user_id = %s AND name = %s", (user_id, 'month_champion'))
                    if not cur.fetchone():
                        cur.execute("INSERT INTO badges (user_id, name) VALUES (%s, %s)", (user_id, 'month_champion'))
                        msg["new_badges"].append('month_champion')
                        
                if new_total_points >= 500:
                    cur.execute("SELECT * FROM badges WHERE user_id = %s AND name = %s", (user_id, 'point_collector'))
                    if not cur.fetchone():
                        cur.execute("INSERT INTO badges (user_id, name) VALUES (%s, %s)", (user_id, 'point_collector'))
                        msg["new_badges"].append('point_collector')
            else:
                # Crea nuove statistiche
                cur.execute("""
                    INSERT INTO user_stats (user_id, total_points, tasks_completed, level, streak, last_task_date)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (user_id, points, 1, 1, 1, datetime.now()))
                
                if points >= 10:
                    cur.execute("INSERT INTO badges (user_id, name) VALUES (%s, %s)", (user_id, 'rookie'))
                    msg["new_badges"].append('rookie')
            
            # Sposta la task da assigned a completed
            cur.execute("""
                INSERT INTO completed_tasks (chat_id, task_id, assigned_to, assigned_by, assigned_date, completed_date, points_earned)
                SELECT chat_id, task_id, assigned_to, assigned_by, assigned_date, %s, %s
                FROM assigned_tasks 
                WHERE chat_id = %s AND task_id = %s AND assigned_to = %s
            """, (datetime.now(), points, chat_id, task_id, user_id))
            
            cur.execute("DELETE FROM assigned_tasks WHERE chat_id = %s AND task_id = %s AND assigned_to = %s", (chat_id, task_id, user_id))
            self.conn.commit()
            return points, msg

    def get_leaderboard(self, chat_id: int):
        with self.conn, self.conn.cursor() as cur:
            cur.execute("""
                SELECT fm.user_id, fm.first_name, 
                       COALESCE(us.total_points, 0) as total_points, 
                       COALESCE(us.level, 1) as level, 
                       COALESCE(us.tasks_completed, 0) as tasks_completed, 
                       COALESCE(us.streak, 0) as streak
                FROM family_members fm
                LEFT JOIN user_stats us ON fm.user_id = us.user_id
                WHERE fm.chat_id = %s
                ORDER BY COALESCE(us.total_points, 0) DESC
            """, (chat_id,))
            return cur.fetchall()

    def get_user_stats(self, user_id: int):
        with self.conn, self.conn.cursor() as cur:
            cur.execute("SELECT * FROM user_stats WHERE user_id = %s", (user_id,))
            return cur.fetchone()

    def get_user_badges(self, user_id: int):
        with self.conn, self.conn.cursor() as cur:
            cur.execute("SELECT name FROM badges WHERE user_id = %s", (user_id,))
            return [row['name'] for row in cur.fetchall()]

db = FamilyTaskDB()

class FamilyTaskBot:
    def __init__(self):
        self.badge_emojis = {
            'rookie': '🥉',
            'expert': '🥈',
            'master': '🥇',
            'week_warrior': '⚡',
            'month_champion': '👑',
            'point_collector': '💎'
        }

    # Mappa categorie e task
    TASK_CATEGORIES = {
        "cucina": {
            "label": "🍽️ Cucina",
            "tasks": ["cucina_pulizia", "lavastoviglie"]
        },
        "pulizie": {
            "label": "🧹 Pulizie",
            "tasks": ["bagno_pulizia", "aspirapolvere", "pavimenti", "finestre"]
        },
        "bucato": {
            "label": "👕 Bucato",
            "tasks": ["bucato", "stirare", "letti"]
        },
        "esterni": {
            "label": "🌱 Esterni",
            "tasks": ["giardino", "spazzatura"]
        },
        "commissioni": {
            "label": "🛒 Commissioni",
            "tasks": ["spesa"]
        }
    }

    def get_main_menu_keyboard(self):
        keyboard = [
            [KeyboardButton("📋 Le Mie Task"), KeyboardButton("🎯 Assegna Task")],
            [KeyboardButton("🏆 Classifica"), KeyboardButton("📊 Statistiche")],
            [KeyboardButton("📚 Tutte le Task"), KeyboardButton("⚙️ Menu")]
        ]
        return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)

    def get_quick_actions_inline(self):
        keyboard = [
            [InlineKeyboardButton("🎯 Assegna Task", callback_data="assign_menu"),
             InlineKeyboardButton("✅ Completa Task", callback_data="complete_menu")],
            [InlineKeyboardButton("🏆 Classifica", callback_data="show_leaderboard"),
             InlineKeyboardButton("📊 Le Mie Stats", callback_data="show_my_stats")],
            [InlineKeyboardButton("🔄 Aggiorna Menu", callback_data="refresh_menu")]
        ]
        return InlineKeyboardMarkup(keyboard)

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.message:
            return
        user = update.effective_user
        chat_id = update.effective_chat.id
        db.add_family_member(chat_id, user.id, user.username or '', user.first_name)
        welcome_text = f"""
🏠 *Benvenuto nel Family Task Manager!*

Ciao {user.first_name}! 👋

Questo bot ti aiuta a gestire le faccende domestiche in modo divertente con la tua famiglia!

*🎮 Come funziona:*
• Assegna compiti ai membri della famiglia
• Guadagna punti completando le attività
• Scala la classifica familiare
• Sblocca badge speciali
• Mantieni streak giornaliere

*🚀 Usa i bottoni qui sotto per navigare facilmente!*
        """
        keyboard = self.get_main_menu_keyboard()
        inline_keyboard = self.get_quick_actions_inline()
        await update.message.reply_text(
            welcome_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=keyboard
        )
        await update.message.reply_text(
            "*🚀 Menu Rapido - Azioni Principali:*",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=inline_keyboard
        )

    async def my_tasks(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.message:
            return
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        my_tasks = db.get_user_assigned_tasks(chat_id, user_id)
        if not my_tasks:
            keyboard = [
                [InlineKeyboardButton("🎯 Assegna Nuova Task", callback_data="assign_menu")],
                [InlineKeyboardButton("📋 Vedi Tutte le Task", callback_data="show_all_tasks")],
                [InlineKeyboardButton("🔙 Menu Principale", callback_data="main_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                "📝 *Non hai attività assegnate al momento!*\n\nVuoi assegnarne una a te stesso o vedere tutte le task disponibili?",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
            return
        tasks_text = f"*📋 Le Tue Attività ({len(my_tasks)}):*\n\n"
        keyboard = []
        for i, task in enumerate(my_tasks, 1):
            due_str = task['due_date'].strftime("%d/%m") if task['due_date'] else "-"
            days_left = (task['due_date'] - datetime.now()).days if task['due_date'] else 99
            urgency = "🔴" if days_left <= 1 else "🟡" if days_left <= 2 else "🟢"
            tasks_text += f"*{i}. {task['name']}*\n"
            tasks_text += f"⭐ {task['points']} punti | 📅 Scadenza: {due_str} {urgency}\n"
            tasks_text += f"⏱️ Tempo stimato: ~{task['time_minutes']} minuti\n\n"
            button_text = f"✅ {task['name'][:15]}..."
            keyboard.append([InlineKeyboardButton(
                button_text,
                callback_data=f"complete_{task['task_id']}"
            )])
        keyboard.extend([
            [InlineKeyboardButton("🎯 Assegna Altra Task", callback_data="assign_menu")],
            [InlineKeyboardButton("📊 Mie Statistiche", callback_data="show_my_stats")],
            [InlineKeyboardButton("🔙 Menu Principale", callback_data="main_menu")]
        ])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(tasks_text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)

    async def show_tasks(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.message:
            return
        tasks = db.get_all_tasks()
        # Organizza le task per categoria
        cat_map = {k: [] for k in self.TASK_CATEGORIES.keys()}
        for task in tasks:
            for catid, cat in self.TASK_CATEGORIES.items():
                if task['id'] in cat['tasks']:
                    cat_map[catid].append(task)
        tasks_text = "*📋 Attività Disponibili:*\n\n"
        for catid, cat in self.TASK_CATEGORIES.items():
            tasks_text += f"*{cat['label']}*\n"
            for task in cat_map[catid]:
                tasks_text += f"  {task['name']}\n"
                tasks_text += f"  ⭐ {task['points']} punti | ⏱️ ~{task['time_minutes']} min\n"
            tasks_text += "\n"
        keyboard = [
            [InlineKeyboardButton("🎯 Assegna Attività", callback_data="assign_menu")],
            [InlineKeyboardButton("✅ Completa Attività", callback_data="complete_menu")],
            [InlineKeyboardButton("🔙 Menu Principale", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(tasks_text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)

    async def leaderboard(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.message:
            return
        chat_id = update.effective_chat.id
        leaderboard = db.get_leaderboard(chat_id)
        if not leaderboard:
            keyboard = [
                [InlineKeyboardButton("👥 Invita Famiglia", callback_data="invite_info")],
                [InlineKeyboardButton("🔙 Menu Principale", callback_data="main_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                "👥 *Nessun membro registrato nella famiglia!*\n\nInvita i tuoi familiari a usare il bot con `/start`",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
            return
        leaderboard_text = f"*🏆 CLASSIFICA FAMIGLIA ({len(leaderboard)} membri)*\n\n"
        positions = ["🥇", "🥈", "🥉"]
        for i, member in enumerate(leaderboard):
            position = positions[i] if i < 3 else f"{i+1}°"
            badges = db.get_user_badges(member['user_id'])
            badges_str = " ".join([self.badge_emojis.get(badge, "🏅") for badge in badges])
            leaderboard_text += f"{position} *{member['first_name']}*\n"
            leaderboard_text += f"⭐ {member['total_points']} punti | 📊 Livello {member['level']}\n"
            leaderboard_text += f"✅ {member['tasks_completed']} task | 🔥 Streak: {member['streak']}\n"
            if badges_str:
                leaderboard_text += f"🏅 {badges_str}\n"
            leaderboard_text += "\n"
        keyboard = [
            [InlineKeyboardButton("📊 Mie Statistiche", callback_data="show_my_stats")],
            [InlineKeyboardButton("🎯 Assegna Task", callback_data="assign_menu")],
            [InlineKeyboardButton("🔄 Aggiorna", callback_data="show_leaderboard")],
            [InlineKeyboardButton("🔙 Menu Principale", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(leaderboard_text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)

    async def stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.message:
            return
        user_id = update.effective_user.id
        stats = db.get_user_stats(user_id)
        if not stats:
            keyboard = [
                [InlineKeyboardButton("🎯 Assegna Prima Task", callback_data="assign_menu")],
                [InlineKeyboardButton("📋 Vedi Task Disponibili", callback_data="show_all_tasks")],
                [InlineKeyboardButton("🔙 Menu Principale", callback_data="main_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                "📊 *Non hai ancora statistiche!*\n\nCompleta la prima attività per iniziare a guadagnare punti e vedere le tue stats.",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
            return
        badges = db.get_user_badges(user_id)
        badges_str = " ".join([self.badge_emojis.get(b, "🏅") for b in badges])
        current_level_points = stats['total_points'] % 100
        points_to_next_level = 100 - current_level_points
        progress_bar = "▓" * (current_level_points // 10) + "░" * (10 - (current_level_points // 10))
        stats_text = f"""
*📊 Le Tue Statistiche*

👤 *Livello:* {stats['level']} 
⭐ *Punti Totali:* {stats['total_points']}
✅ *Task Completate:* {stats['tasks_completed']}
🔥 *Streak Attuale:* {stats['streak']} giorni

*📈 Progresso Livello {stats['level']} → {stats['level'] + 1}:*
{progress_bar} {current_level_points}/100
({points_to_next_level} punti al prossimo livello)

🏅 *Badge Ottenuti:*
{badges_str if badges_str else 'Nessun badge ancora 😢'}
        """
        keyboard = [
            [InlineKeyboardButton("📋 Le Mie Task", callback_data="show_my_tasks")],
            [InlineKeyboardButton("🏆 Classifica", callback_data="show_leaderboard")],
            [InlineKeyboardButton("🎯 Assegna Task", callback_data="assign_menu")],
            [InlineKeyboardButton("🔙 Menu Principale", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(stats_text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.message:
            return
        help_text = """
*🏠 FAMILY TASK MANAGER - GUIDA*

*🎮 Gamification:*
• Guadagna punti completando attività
• Sali di livello ogni 100 punti
• Mantieni streak giornaliere
• Sblocca badge speciali
• Competi con la famiglia

*📋 Comandi:*
/start - Inizia e unisciti alla famiglia
/tasks - Vedi tutte le attività
/mytasks - Le tue attività assegnate
/leaderboard - Classifica famiglia
/stats - Le tue statistiche personali

*🏅 Badge Disponibili:*
🥉 Rookie - 10 task completate
🥈 Expert - 50 task completate  
🥇 Master - 100 task completate
⚡ Week Warrior - 7 giorni di streak
👑 Month Champion - 30 giorni di streak
💎 Point Collector - 500 punti totali
        """
        await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)

    async def assign_task_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        # Mostra solo le categorie come bottoni
        keyboard = []
        for catid, cat in self.TASK_CATEGORIES.items():
            keyboard.append([
                InlineKeyboardButton(cat["label"], callback_data=f"assign_category_{catid}")
            ])
        keyboard.append([InlineKeyboardButton("🔙 Indietro", callback_data="main_menu")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        if update.callback_query:
            await update.callback_query.edit_message_text(
                "*Scegli una categoria di task da assegnare:*", parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup
            )
        else:
            await update.message.reply_text(
                "*Scegli una categoria di task da assegnare:*", parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup
            )

    async def assign_category_menu(self, query, catid):
        tasks = db.get_default_tasks()
        chat_id = query.message.chat.id
        assigned = db.get_assigned_tasks_for_chat(chat_id)
        members = {m['user_id']: m['first_name'] for m in db.get_family_members(chat_id)}
        assigned_map = {}
        for v in assigned:
            assigned_map.setdefault(v['task_id'], []).append(members.get(v['assigned_to'], str(v['assigned_to'])))
        cat = self.TASK_CATEGORIES[catid]
        keyboard = []
        for task_id in cat['tasks']:
            if task_id in assigned_map:
                who = ', '.join(assigned_map[task_id])
                label = f"{tasks[task_id]['name']} ({tasks[task_id]['points']} pt) - ASSEGNATA a {who}"
                keyboard.append([
                    InlineKeyboardButton(label, callback_data="none")
                ])
            else:
                keyboard.append([
                    InlineKeyboardButton(f"{tasks[task_id]['name']} ({tasks[task_id]['points']} pt)", callback_data=f"choose_task_{task_id}")
                ])
        keyboard.append([InlineKeyboardButton("🔙 Indietro", callback_data="assign_menu")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            f"*{cat['label']} - Task disponibili:*", parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup
        )

    async def button_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        try:
            logger.info(f"Ricevuto callback_query: {query.data} da utente {query.from_user.id}")
            await query.answer()
            data = query.data
            if data == "assign_menu":
                await self.assign_task_menu(update, context)
            elif data.startswith("assign_category_"):
                catid = data.replace("assign_category_", "")
                await self.assign_category_menu(query, catid)
            elif data.startswith("choose_task_"):
                task_id = data.replace("choose_task_", "")
                await self.choose_assign_target(query, task_id)
            elif data.startswith("assign_self_"):
                task_id = data.replace("assign_self_", "")
                await self.handle_assign(query, task_id, query.from_user.id)
            elif data.startswith("assign_"):
                parts = data.split("_")
                if len(parts) >= 3:
                    task_id = parts[1]
                    target_user_id = int(parts[2])
                    await self.handle_assign(query, task_id, target_user_id)
            elif data == "none":
                await query.answer("Task già assegnata", show_alert=True)
            elif data.startswith("complete_"):
                task_id = data.replace("complete_", "")
                logger.info(f"Chiamo complete_task per task_id: {task_id}")
                await self.complete_task(query, task_id)
            elif data == "show_my_stats":
                await self.show_my_stats(None, None, query=query)
            elif data == "show_my_tasks":
                await self.show_my_tasks_inline(query)
            elif data == "show_leaderboard":
                await self.show_leaderboard_inline(query)
            elif data == "show_all_tasks":
                await self.show_all_tasks_inline(query)
            elif data == "main_menu":
                inline_keyboard = self.get_quick_actions_inline()
                await query.edit_message_text(
                    "*🏠 Menu Principale*\n\nSeleziona un'azione:",
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=inline_keyboard
                )
            elif data == "refresh_menu":
                inline_keyboard = self.get_quick_actions_inline()
                await query.edit_message_text(
                    "*🏠 Menu Aggiornato*\n\nSeleziona un'azione:",
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=inline_keyboard
                )
            else:
                logger.info(f"Callback non gestito: {data}")
                await query.edit_message_text("❓ Azione non ancora implementata")
        except Exception as e:
            logger.error(f"Errore in button_handler: {e}")
            try:
                await query.edit_message_text(
                    "❌ *Errore temporaneo*\n\nRiprova o usa /start per ricominciare.",
                    parse_mode=ParseMode.MARKDOWN
                )
            except Exception as e2:
                logger.error(f"Errore secondario nel button handler: {e2}")

    async def complete_task(self, query, task_id):
        user_id = query.from_user.id
        chat_id = query.message.chat.id  # Funziona per gruppi e privati
        points, msg = db.complete_task(chat_id, task_id, user_id)
        if points > 0:
            task = db.get_task_by_id(task_id)
            stats = db.get_user_stats(user_id)
            level_up_text = ""
            if msg["level_up"]:
                level_up_text = f"\n🎉 *LEVEL UP!* Ora sei livello {msg['new_level']}!"
            badge_text = ""
            if msg["new_badges"]:
                badge_text = f"\n🏅 *Nuovo Badge:* {' '.join([self.badge_emojis.get(b, b) for b in msg['new_badges']])}"
            keyboard = [
                [InlineKeyboardButton("📊 Mie Statistiche", callback_data="show_my_stats")],
                [InlineKeyboardButton("🏆 Classifica", callback_data="show_leaderboard")],
                [InlineKeyboardButton("📋 Altre Mie Task", callback_data="show_my_tasks")],
                [InlineKeyboardButton("🔙 Menu", callback_data="main_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                f"🎉 *Attività Completata!*\n\n"
                f"📋 {task['name']}\n"
                f"⭐ +{points} punti\n"
                f"🔥 Streak: {stats['streak']} giorni"
                f"{level_up_text}"
                f"{badge_text}",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
        else:
            await query.edit_message_text("❌ Attività non trovata o già completata.")

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.message:
            return
        text = update.message.text
        if text == "📋 Le Mie Task":
            await self.my_tasks(update, context)
        elif text == "🎯 Assegna Task":
            await self.assign_task_menu(update, context)
        elif text == "🏆 Classifica":
            await self.leaderboard(update, context)
        elif text == "📊 Statistiche":
            await self.stats(update, context)
        elif text == "📚 Tutte le Task":
            await self.show_tasks(update, context)
        elif text == "⚙️ Menu":
            inline_keyboard = self.get_quick_actions_inline()
            await update.message.reply_text(
                "*🏠 Menu Principale*\n\nSeleziona un'azione:",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=inline_keyboard
            )
        else:
            await update.message.reply_text(
                "❓ Non ho capito. Usa i bottoni del menu o digita /help per l'aiuto!"
            )

    async def show_my_stats(self, update, context, query=None):
        if query:
            user_id = query.from_user.id
            send_func = query.edit_message_text
        else:
            user_id = update.effective_user.id
            send_func = update.message.reply_text
        stats = db.get_user_stats(user_id)
        if not stats:
            keyboard = [
                [InlineKeyboardButton("🎯 Assegna Prima Task", callback_data="assign_menu")],
                [InlineKeyboardButton("📋 Vedi Task Disponibili", callback_data="show_all_tasks")],
                [InlineKeyboardButton("🔙 Menu Principale", callback_data="main_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await send_func(
                "📊 *Non hai ancora statistiche!*\n\nCompleta la prima attività per iniziare a guadagnare punti e vedere le tue stats.",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
            return
        badges = db.get_user_badges(user_id)
        badges_str = " ".join([self.badge_emojis.get(b, "🏅") for b in badges])
        current_level_points = stats['total_points'] % 100
        points_to_next_level = 100 - current_level_points
        progress_bar = "▓" * (current_level_points // 10) + "░" * (10 - (current_level_points // 10))
        stats_text = f"""
*📊 Le Tue Statistiche*

👤 *Livello:* {stats['level']} 
⭐ *Punti Totali:* {stats['total_points']}
✅ *Task Completate:* {stats['tasks_completed']}
🔥 *Streak Attuale:* {stats['streak']} giorni

*📈 Progresso Livello {stats['level']} → {stats['level'] + 1}:*
{progress_bar} {current_level_points}/100
({points_to_next_level} punti al prossimo livello)

🏅 *Badge Ottenuti:*
{badges_str if badges_str else 'Nessun badge ancora 😢'}
        """
        keyboard = [
            [InlineKeyboardButton("📋 Le Mie Task", callback_data="show_my_tasks")],
            [InlineKeyboardButton("🏆 Classifica", callback_data="show_leaderboard")],
            [InlineKeyboardButton("🎯 Assegna Task", callback_data="assign_menu")],
            [InlineKeyboardButton("🔙 Menu Principale", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await send_func(stats_text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)

    async def choose_assign_target(self, query, task_id):
        """Mostra i membri della famiglia per scegliere a chi assegnare la task"""
        chat_id = query.message.chat.id
        members = db.get_family_members(chat_id)
        task = db.get_task_by_id(task_id)
        
        if not task:
            await query.edit_message_text("❌ Task non trovata!")
            return
            
        keyboard = []
        # Opzione per assegnare a se stesso
        keyboard.append([
            InlineKeyboardButton(f"🫵 Assegna a me", callback_data=f"assign_self_{task_id}")
        ])
        
        # Opzioni per assegnare ad altri membri
        for member in members:
            if member['user_id'] != query.from_user.id:  # Escludi se stesso
                keyboard.append([
                    InlineKeyboardButton(
                        f"👤 {member['first_name']}", 
                        callback_data=f"assign_{task_id}_{member['user_id']}"
                    )
                ])
        
        keyboard.append([InlineKeyboardButton("🔙 Indietro", callback_data="assign_menu")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"*A chi vuoi assegnare:*\n\n📋 {task['name']}\n⭐ {task['points']} punti | ⏱️ ~{task['time_minutes']} min",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )

    async def handle_assign(self, query, task_id, target_user_id):
        """Gestisce l'assegnazione effettiva della task"""
        chat_id = query.message.chat.id
        assigned_by = query.from_user.id
        
        try:
            # Verifica se la task è già assegnata
            existing = db.get_assigned_tasks_for_chat(chat_id)
            for assigned in existing:
                if assigned['task_id'] == task_id and assigned['assigned_to'] == target_user_id:
                    await query.edit_message_text("❌ Questa task è già assegnata a questo utente!")
                    return
            
            # Assegna la task
            db.assign_task(chat_id, task_id, target_user_id, assigned_by)
            
            # Ottieni informazioni per la conferma
            task = db.get_task_by_id(task_id)
            target_name = "te stesso" if target_user_id == assigned_by else "un membro della famiglia"
            
            # Cerca il nome del target se diverso dall'assegnante
            if target_user_id != assigned_by:
                members = db.get_family_members(chat_id)
                for member in members:
                    if member['user_id'] == target_user_id:
                        target_name = member['first_name']
                        break
            
            keyboard = [
                [InlineKeyboardButton("📋 Le Mie Task", callback_data="show_my_tasks")],
                [InlineKeyboardButton("🎯 Assegna Altra Task", callback_data="assign_menu")],
                [InlineKeyboardButton("🔙 Menu Principale", callback_data="main_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                f"✅ *Task Assegnata!*\n\n"
                f"📋 {task['name']}\n"
                f"👤 Assegnata a: {target_name}\n"
                f"⭐ {task['points']} punti | ⏱️ ~{task['time_minutes']} min\n"
                f"📅 Scadenza: 3 giorni",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
            
        except Exception as e:
            logger.error(f"Errore nell'assegnazione task: {e}")
            await query.edit_message_text("❌ Errore nell'assegnazione della task. Riprova.")

    async def send_task_reminders(self, application):
        """Invia promemoria per le task in scadenza"""
        try:
            # TODO: Implementare logica di promemoria
            # Per ora lasciamo vuoto per non causare errori
            pass
        except Exception as e:
            logger.error(f"Errore nei promemoria: {e}")

    async def show_my_tasks_inline(self, query):
        """Versione inline di my_tasks per i callback"""
        user_id = query.from_user.id
        chat_id = query.message.chat.id
        my_tasks = db.get_user_assigned_tasks(chat_id, user_id)
        
        if not my_tasks:
            keyboard = [
                [InlineKeyboardButton("🎯 Assegna Nuova Task", callback_data="assign_menu")],
                [InlineKeyboardButton("📋 Vedi Tutte le Task", callback_data="show_all_tasks")],
                [InlineKeyboardButton("🔙 Menu Principale", callback_data="main_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                "📝 *Non hai attività assegnate al momento!*\n\nVuoi assegnarne una a te stesso o vedere tutte le task disponibili?",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
            return
            
        tasks_text = f"*📋 Le Tue Attività ({len(my_tasks)}):*\n\n"
        keyboard = []
        
        for i, task in enumerate(my_tasks, 1):
            due_str = task['due_date'].strftime("%d/%m") if task['due_date'] else "-"
            days_left = (task['due_date'] - datetime.now()).days if task['due_date'] else 99
            urgency = "🔴" if days_left <= 1 else "🟡" if days_left <= 2 else "🟢"
            
            tasks_text += f"*{i}. {task['name']}*\n"
            tasks_text += f"⭐ {task['points']} punti | 📅 Scadenza: {due_str} {urgency}\n"
            tasks_text += f"⏱️ Tempo stimato: ~{task['time_minutes']} minuti\n\n"
            
            button_text = f"✅ {task['name'][:15]}..."
            keyboard.append([InlineKeyboardButton(
                button_text,
                callback_data=f"complete_{task['task_id']}"
            )])
            
        keyboard.extend([
            [InlineKeyboardButton("🎯 Assegna Altra Task", callback_data="assign_menu")],
            [InlineKeyboardButton("📊 Mie Statistiche", callback_data="show_my_stats")],
            [InlineKeyboardButton("🔙 Menu Principale", callback_data="main_menu")]
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(tasks_text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)

    async def show_leaderboard_inline(self, query):
        """Versione inline di leaderboard per i callback"""
        chat_id = query.message.chat.id
        leaderboard = db.get_leaderboard(chat_id)
        
        if not leaderboard:
            keyboard = [
                [InlineKeyboardButton("👥 Invita Famiglia", callback_data="invite_info")],
                [InlineKeyboardButton("🔙 Menu Principale", callback_data="main_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                "👥 *Nessun membro registrato nella famiglia!*\n\nInvita i tuoi familiari a usare il bot con `/start`",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
            return
            
        leaderboard_text = f"*🏆 CLASSIFICA FAMIGLIA ({len(leaderboard)} membri)*\n\n"
        positions = ["🥇", "🥈", "🥉"]
        
        for i, member in enumerate(leaderboard):
            position = positions[i] if i < 3 else f"{i+1}°"
            badges = db.get_user_badges(member['user_id'])
            badges_str = " ".join([self.badge_emojis.get(badge, "🏅") for badge in badges])
            
            leaderboard_text += f"{position} *{member['first_name']}*\n"
            leaderboard_text += f"⭐ {member['total_points']} punti | 📊 Livello {member['level']}\n"
            leaderboard_text += f"✅ {member['tasks_completed']} task | 🔥 Streak: {member['streak']}\n"
            if badges_str:
                leaderboard_text += f"🏅 {badges_str}\n"
            leaderboard_text += "\n"
            
        keyboard = [
            [InlineKeyboardButton("📊 Mie Statistiche", callback_data="show_my_stats")],
            [InlineKeyboardButton("🎯 Assegna Task", callback_data="assign_menu")],
            [InlineKeyboardButton("🔄 Aggiorna", callback_data="show_leaderboard")],
            [InlineKeyboardButton("🔙 Menu Principale", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(leaderboard_text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)

    async def show_all_tasks_inline(self, query):
        """Versione inline di show_tasks per i callback"""
        tasks = db.get_all_tasks()
        
        # Organizza le task per categoria
        cat_map = {k: [] for k in self.TASK_CATEGORIES.keys()}
        for task in tasks:
            for catid, cat in self.TASK_CATEGORIES.items():
                if task['id'] in cat['tasks']:
                    cat_map[catid].append(task)
                    
        tasks_text = "*📋 Attività Disponibili:*\n\n"
        for catid, cat in self.TASK_CATEGORIES.items():
            tasks_text += f"*{cat['label']}*\n"
            for task in cat_map[catid]:
                tasks_text += f"  {task['name']}\n"
                tasks_text += f"  ⭐ {task['points']} punti | ⏱️ ~{task['time_minutes']} min\n"
            tasks_text += "\n"
            
        keyboard = [
            [InlineKeyboardButton("🎯 Assegna Attività", callback_data="assign_menu")],
            [InlineKeyboardButton("✅ Completa Attività", callback_data="complete_menu")],
            [InlineKeyboardButton("🔙 Menu Principale", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(tasks_text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)

def main():
    TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    if not TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN non trovato!")
        return
    application = Application.builder().token(TOKEN).build()
    bot = FamilyTaskBot()
    
    async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
        logger.error("Exception while handling an update:", exc_info=context.error)
        if update and hasattr(update, 'effective_chat') and update.effective_chat:
            try:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text="❌ Si è verificato un errore. Riprova con /start"
                )
            except Exception as e:
                logger.error(f"Errore nell'invio del messaggio di errore: {e}")
    
    async def reminder_job(context):
        await bot.send_task_reminders(context.application)
    
    application.add_error_handler(error_handler)
    application.add_handler(CommandHandler("start", bot.start))
    application.add_handler(CommandHandler("tasks", bot.show_tasks))
    application.add_handler(CommandHandler("mytasks", bot.my_tasks))
    application.add_handler(CommandHandler("leaderboard", bot.leaderboard))
    application.add_handler(CommandHandler("stats", bot.stats))
    application.add_handler(CommandHandler("help", bot.help_command))
    application.add_handler(CallbackQueryHandler(bot.button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, bot.handle_message))
    
    # Aggiungi job per i promemoria (ogni ora)
    application.job_queue.run_repeating(reminder_job, interval=3600, first=10)
    
    logger.info("🏠 Family Task Bot avviato!")
    application.run_polling()

if __name__ == '__main__':
    main()
