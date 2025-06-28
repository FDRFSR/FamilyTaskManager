import os
import logging
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from telegram.constants import ParseMode

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

class FamilyTaskDB:
    def __init__(self):
        self.data = {
            'families': {},
            'tasks': self.get_default_tasks(),
            'user_stats': {},
            'assigned_tasks': {},
            'completed_tasks': []
        }

    def get_default_tasks(self):
        return {
            'cucina_pulizia': {'name': '🍽️ Pulire la cucina', 'points': 15, 'time_minutes': 30},
            'bagno_pulizia': {'name': '🚿 Pulire il bagno', 'points': 20, 'time_minutes': 40},
            'aspirapolvere': {'name': '🧹 Passare l\'aspirapolvere', 'points': 12, 'time_minutes': 25},
            'lavastoviglie': {'name': '🍴 Caricare/svuotare lavastoviglie', 'points': 8, 'time_minutes': 15},
            'bucato': {'name': '👕 Fare il bucato', 'points': 10, 'time_minutes': 20},
            'stirare': {'name': '👔 Stirare', 'points': 18, 'time_minutes': 35},
            'spazzatura': {'name': '🗑️ Portare fuori la spazzatura', 'points': 5, 'time_minutes': 10},
            'giardino': {'name': '🌱 Curare il giardino', 'points': 25, 'time_minutes': 50},
            'spesa': {'name': '🛒 Fare la spesa', 'points': 15, 'time_minutes': 30},
            'letti': {'name': '🛏️ Rifare i letti', 'points': 6, 'time_minutes': 12},
            'pavimenti': {'name': '🧽 Lavare i pavimenti', 'points': 20, 'time_minutes': 40},
            'finestre': {'name': '🪟 Pulire le finestre', 'points': 22, 'time_minutes': 45},
        }

    def add_family_member(self, chat_id: int, user_id: int, username: str, first_name: str):
        if chat_id not in self.data['families']:
            self.data['families'][chat_id] = []
        for member in self.data['families'][chat_id]:
            if member['user_id'] == user_id:
                return False
        self.data['families'][chat_id].append({
            'user_id': user_id,
            'username': username,
            'first_name': first_name,
            'joined_date': datetime.now().isoformat()
        })
        if user_id not in self.data['user_stats']:
            self.data['user_stats'][user_id] = {
                'total_points': 0,
                'tasks_completed': 0,
                'level': 1,
                'badges': [],
                'streak': 0,
                'last_task_date': None
            }
        return True

    def get_family_members(self, chat_id: int):
        return self.data['families'].get(chat_id, [])

    def assign_task(self, chat_id: int, task_id: str, assigned_to: int, assigned_by: int):
        task_key = f"{chat_id}_{task_id}_{assigned_to}"
        self.data['assigned_tasks'][task_key] = {
            'chat_id': chat_id,
            'task_id': task_id,
            'assigned_to': assigned_to,
            'assigned_by': assigned_by,
            'assigned_date': datetime.now().isoformat(),
            'status': 'pending',
            'due_date': (datetime.now() + timedelta(days=3)).isoformat()
        }

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
        task_key = f"{chat_id}_{task_id}_{user_id}"
        if task_key in self.data['assigned_tasks']:
            task_data = self.data['assigned_tasks'][task_key]
            points = self.data['tasks'][task_id]['points']
            msg = {"level_up": False, "new_level": None, "new_badges": []}
            if user_id in self.data['user_stats']:
                stats = self.data['user_stats'][user_id]
                old_level = stats['level']
                stats['total_points'] += points
                stats['tasks_completed'] += 1
                stats['level'] = (stats['total_points'] // 100) + 1
                if stats['level'] > old_level:
                    msg["level_up"] = True
                    msg["new_level"] = stats['level']
                last_date = stats.get('last_task_date')
                if last_date:
                    last_date = datetime.fromisoformat(last_date)
                    if (datetime.now() - last_date).days == 1:
                        stats['streak'] += 1
                    elif (datetime.now() - last_date).days > 1:
                        stats['streak'] = 1
                else:
                    stats['streak'] = 1
                stats['last_task_date'] = datetime.now().isoformat()
                msg["new_badges"] = self.check_and_assign_badges(user_id, stats)
            self.data['completed_tasks'].append({
                **task_data,
                'completed_date': datetime.now().isoformat(),
                'points_earned': points
            })
            del self.data['assigned_tasks'][task_key]
            return points, msg
        return 0, {"level_up": False, "new_level": None, "new_badges": []}

    def get_leaderboard(self, chat_id: int):
        family_members = self.get_family_members(chat_id)
        leaderboard = []
        for member in family_members:
            user_id = member['user_id']
            if user_id in self.data['user_stats']:
                stats = self.data['user_stats'][user_id]
                leaderboard.append({
                    'user_id': user_id,
                    'first_name': member['first_name'],
                    'points': stats['total_points'],
                    'level': stats['level'],
                    'tasks_completed': stats['tasks_completed'],
                    'streak': stats['streak'],
                    'badges': stats['badges']
                })
        return sorted(leaderboard, key=lambda x: x['points'], reverse=True)

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
        my_tasks = []
        for task_key, task_data in db.data['assigned_tasks'].items():
            if task_data['assigned_to'] == user_id and task_data['chat_id'] == chat_id:
                task_id = task_data['task_id']
                if task_id in db.data['tasks']:
                    task_info = db.data['tasks'][task_id]
                    due_date = datetime.fromisoformat(task_data['due_date'])
                    my_tasks.append({
                        'task_key': task_key,
                        'task_info': task_info,
                        'due_date': due_date,
                        'task_id': task_id
                    })
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
            due_str = task['due_date'].strftime("%d/%m")
            days_left = (task['due_date'] - datetime.now()).days
            urgency = "🔴" if days_left <= 1 else "🟡" if days_left <= 2 else "🟢"
            tasks_text += f"*{i}. {task['task_info']['name']}*\n"
            tasks_text += f"⭐ {task['task_info']['points']} punti | 📅 Scadenza: {due_str} {urgency}\n"
            tasks_text += f"⏱️ Tempo stimato: ~{task['task_info']['time_minutes']} minuti\n\n"
            button_text = f"✅ {task['task_info']['name'][:15]}..."
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
        tasks_text = "*📋 Attività Disponibili:*\n\n"
        categories = {
            "🍽️ Cucina": ['cucina_pulizia', 'lavastoviglie'],
            "🧹 Pulizie": ['bagno_pulizia', 'aspirapolvere', 'pavimenti', 'finestre'],
            "👕 Bucato": ['bucato', 'stirare', 'letti'],
            "🌱 Esterni": ['giardino', 'spazzatura'],
            "🛒 Commissioni": ['spesa']
        }
        for category, task_ids in categories.items():
            tasks_text += f"*{category}*\n"
            for task_id in task_ids:
                if task_id in db.data['tasks']:
                    task_data = db.data['tasks'][task_id]
                    tasks_text += f"  {task_data['name']}\n"
                    tasks_text += f"  ⭐ {task_data['points']} punti | ⏱️ ~{task_data['time_minutes']} min\n"
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
            badges_str = " ".join([self.badge_emojis.get(badge, "🏅") for badge in member['badges']])
            leaderboard_text += f"{position} *{member['first_name']}*\n"
            leaderboard_text += f"⭐ {member['points']} punti | 📊 Livello {member['level']}\n"
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
        if user_id not in db.data['user_stats']:
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
        stats = db.data['user_stats'][user_id]
        badges_str = " ".join([self.badge_emojis.get(badge, "🏅") for badge in stats['badges']])
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
        chat_id = update.effective_chat.id
        tasks = db.data['tasks']
        assigned = db.data['assigned_tasks']
        members = {m['user_id']: m['first_name'] for m in db.get_family_members(chat_id)}
        assigned_map = {}
        for v in assigned.values():
            if v['chat_id'] == chat_id:
                assigned_map.setdefault(v['task_id'], []).append(members.get(v['assigned_to'], str(v['assigned_to'])))
        keyboard = []
        for task_id, task in tasks.items():
            if task_id in assigned_map:
                who = ', '.join(assigned_map[task_id])
                label = f"{task['name']} ({task['points']} pt) - ASSEGNATA a {who}"
                keyboard.append([
                    InlineKeyboardButton(label, callback_data="none")
                ])
            else:
                keyboard.append([
                    InlineKeyboardButton(f"{task['name']} ({task['points']} pt)", callback_data=f"choose_task_{task_id}")
                ])
        keyboard.append([InlineKeyboardButton("🔙 Indietro", callback_data="main_menu")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        if update.callback_query:
            await update.callback_query.edit_message_text(
                "*Seleziona una task da assegnare:*", parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup
            )
        else:
            await update.message.reply_text(
                "*Seleziona una task da assegnare:*", parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup
            )

    async def choose_assign_target(self, query, task_id):
        user_id = query.from_user.id
        chat_id = query.message.chat.id
        members = db.get_family_members(chat_id)
        # Ottimizzazione: ordina membri alfabeticamente e metti "A me stesso" in cima
        keyboard = [[InlineKeyboardButton("A me stesso", callback_data=f"assign_self_{task_id}")]]
        for member in sorted(members, key=lambda m: m['first_name']):
            if member['user_id'] != user_id:
                keyboard.append([
                    InlineKeyboardButton(f"A {member['first_name']}", callback_data=f"assign_{task_id}_{member['user_id']}")
                ])
        keyboard.append([InlineKeyboardButton("🔙 Indietro", callback_data="assign_menu")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            f"*A chi vuoi assegnare la task?*", parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup
        )

    async def handle_assign(self, query, task_id, target_user_id):
        chat_id = query.message.chat.id
        assigned_by = query.from_user.id
        if any(v['chat_id']==chat_id and v['task_id']==task_id and v['assigned_to']==target_user_id for v in db.data['assigned_tasks'].values()):
            await query.edit_message_text(
                f"⚠️ Task già assegnata a questo utente!", parse_mode=ParseMode.MARKDOWN
            )
            return
        db.assign_task(chat_id, task_id, target_user_id, assigned_by)
        members = db.get_family_members(chat_id)
        target_name = next((m['first_name'] for m in members if m['user_id'] == target_user_id), "")
        keyboard = [
            [InlineKeyboardButton("Assegna un'altra task", callback_data="assign_menu")],
            [InlineKeyboardButton("🔙 Menu", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            f"✅ Task assegnata a {target_name}!", parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup
        )

    # 5. Notifiche automatiche: promemoria task in scadenza o in ritardo
    async def send_task_reminders(self, application):
        now = datetime.now()
        for chat_id, members in db.data['families'].items():
            for task_key, task_data in db.data['assigned_tasks'].items():
                if task_data['chat_id'] != chat_id:
                    continue
                due = datetime.fromisoformat(task_data['due_date'])
                user_id = task_data['assigned_to']
                if (due - now).days == 0:
                    try:
                        await application.bot.send_message(
                            chat_id=chat_id,
                            text=f"⏰ Promemoria: la task '{db.data['tasks'][task_data['task_id']]['name']}' assegnata a {user_id} scade oggi!"
                        )
                    except Exception as e:
                        logger.error(f"Errore invio promemoria: {e}")
                elif (due - now).days < 0:
                    try:
                        await application.bot.send_message(
                            chat_id=chat_id,
                            text=f"⚠️ La task '{db.data['tasks'][task_data['task_id']]['name']}' assegnata a {user_id} è in ritardo!"
                        )
                    except Exception as e:
                        logger.error(f"Errore invio promemoria: {e}")

    # 6. Storico delle task completate da ciascun membro
    async def show_completed_tasks(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        completed = [t for t in db.data['completed_tasks'] if t['assigned_to'] == user_id]
        if not completed:
            await update.message.reply_text("Non hai ancora completato nessuna task.")
            return
        text = "*Storico task completate:*\n"
        for t in sorted(completed, key=lambda x: x['completed_date'], reverse=True)[:10]:
            name = db.data['tasks'][t['task_id']]['name']
            date = datetime.fromisoformat(t['completed_date']).strftime('%d/%m/%Y')
            text += f"- {name} ({date})\n"
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

    # 7. Filtro/ricerca task per nome
    async def search_tasks(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.message or not context.args:
            await update.message.reply_text("Usa: /search <parola chiave>")
            return
        query = ' '.join(context.args).lower()
        tasks = db.data['tasks']
        found = [t for t in tasks.values() if query in t['name'].lower()]
        if not found:
            await update.message.reply_text("Nessuna task trovata.")
            return
        text = "*Risultati ricerca:*\n"
        for t in found:
            text += f"- {t['name']} ({t['points']} pt)\n"
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

    # Aggiorna button_handler per gestire i nuovi callback
    async def button_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        try:
            logger.info(f"Ricevuto callback_query: {query.data} da utente {query.from_user.id}")
            await query.answer()
            data = query.data
            if data == "assign_menu":
                await self.assign_task_menu(update, context)
            elif data.startswith("choose_task_"):
                task_id = data.replace("choose_task_", "")
                await self.choose_assign_target(query, task_id)
            elif data.startswith("assign_self_"):
                task_id = data.replace("assign_self_", "")
                await self.handle_assign(query, task_id, query.from_user.id)
            elif data.startswith("assign_"):
                parts = data.split("_")
                task_id = parts[1]
                target_user_id = int(parts[2])
                await self.handle_assign(query, task_id, target_user_id)
            elif data == "none":
                await query.answer("Task già assegnata", show_alert=True)
            elif data.startswith("complete_"):
                task_id = data.replace("complete_", "")
                logger.info(f"Chiamo complete_task per task_id: {task_id}")
                await self.complete_task(query, task_id)
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
            task_name = db.data['tasks'][task_id]['name']
            stats = db.data['user_stats'][user_id]
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
                f"📋 {task_name}\n"
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
    application.add_error_handler(error_handler)
    application.add_handler(CommandHandler("start", bot.start))
    application.add_handler(CommandHandler("tasks", bot.show_tasks))
    application.add_handler(CommandHandler("mytasks", bot.my_tasks))
    application.add_handler(CommandHandler("leaderboard", bot.leaderboard))
    application.add_handler(CommandHandler("stats", bot.stats))
    application.add_handler(CommandHandler("help", bot.help_command))
    application.add_handler(CallbackQueryHandler(bot.button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, bot.handle_message))
    application.add_handler(CommandHandler("completed", bot.show_completed_tasks))
    application.add_handler(CommandHandler("search", bot.search_tasks))
    logger.info("🏠 Family Task Bot avviato!")
    application.run_polling()
    async def reminder_job():
        await bot.send_task_reminders(application)
    application.job_queue.run_repeating(lambda ctx: reminder_job(), interval=3600, first=10)

if __name__ == '__main__':
    main()
