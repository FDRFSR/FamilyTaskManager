from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.constants import ParseMode
from telegram.ext import ContextTypes
import logging
from db import FamilyTaskDB
from main import send_and_track_message

db = FamilyTaskDB()
logger = logging.getLogger(__name__)

class FamilyTaskBot:
    async def start(self, update, context):
        user = update.effective_user
        chat_id = update.effective_chat.id
        try:
            db.add_family_member(chat_id, user.id, user.username, user.first_name)
        except Exception as e:
            logger.error(f"Errore add_family_member: {e}")
        text = (
            f"👋 Benvenuto, {user.first_name}!\n\n"
            "Sono il Family Task Manager. Usa il menu o i comandi per gestire le task della tua famiglia."
        )
        keyboard = [
            ["📋 Tasks", "📝 MyTasks"],
            ["🏆 Leaderboard", "📊 Stat"],
            ["ℹ️ Help"]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        if update.message:
            await send_and_track_message(update.message.reply_text, text, reply_markup=reply_markup)
        elif update.callback_query:
            await send_and_track_message(update.callback_query.message.reply_text, text, reply_markup=reply_markup)

    async def help_command(self, update, context):
        text = (
            "ℹ️ *Comandi disponibili:*\n"
            "/start - Avvia il bot\n"
            "/help - Mostra questo messaggio\n"
            "/leaderboard - Classifica famiglia\n"
            "/stats - Le tue statistiche\n"
            "/tasks - Elenco task disponibili\n"
            "/mytasks - Le tue task assegnate\n"
        )
        await send_and_track_message(update.message.reply_text, text, parse_mode=ParseMode.MARKDOWN)

    async def leaderboard(self, update, context):
        chat_id = update.effective_chat.id
        leaderboard = db.get_leaderboard(chat_id)
        if not leaderboard:
            await send_and_track_message(update.message.reply_text, "Nessuna classifica disponibile per questa famiglia.")
            return
        text = "🏆 *Classifica Famiglia*\n\n"
        for i, entry in enumerate(leaderboard, 1):
            pos = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}°"
            text += f"{pos} {entry['first_name']}: {entry['total_points']} punti (Lv.{entry['level']}, {entry['tasks_completed']} task)\n"
        await send_and_track_message(update.message.reply_text, text, parse_mode=ParseMode.MARKDOWN)

    async def stats(self, update, context):
        user = update.effective_user
        stats = db.get_user_stats(user.id)
        if not stats:
            await send_and_track_message(update.message.reply_text, "Nessuna statistica trovata. Completa una task per iniziare!")
            return
        text = (
            f"📊 *Le tue statistiche*\n\n"
            f"👤 {user.first_name}\n"
            f"⭐ Punti totali: {stats['total_points']}\n"
            f"✅ Task completate: {stats['tasks_completed']}\n"
            f"🏅 Livello: {stats['level']}\n"
            f"🔥 Streak: {stats['streak']}\n"
        )
        await send_and_track_message(update.message.reply_text, text, parse_mode=ParseMode.MARKDOWN)

    async def show_tasks(self, update, context):
        categories = [
            ("Pulizie", "🧹"),
            ("Cucina", "🍽️"),
            ("Spesa", "🛒"),
            ("Bucato", "🧺"),
            ("Giardino", "🌳"),
            ("Animali", "🐾"),
            ("Auto", "🚗"),
            ("Altro", "📦")
        ]
        keyboard = [
            [InlineKeyboardButton(f"{emoji} {cat}", callback_data=f"cat_{cat.lower()}")]
            for cat, emoji in categories
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await send_and_track_message(update.message.reply_text, "📋 *Scegli una categoria di task:*", parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)

    async def my_tasks(self, update, context):
        user = update.effective_user
        chat_id = update.effective_chat.id
        tasks = db.get_user_assigned_tasks(chat_id, user.id)
        if not tasks:
            await send_and_track_message(update.message.reply_text, "Non hai task assegnate!")
            return
        text = "📝 *Le tue task assegnate:*\n\n"
        keyboard = []
        for task in tasks:
            text += f"• {task['name']} ({task['points']} pt, ~{task['time_minutes']} min)\n"
            keyboard.append([
                InlineKeyboardButton(f"✅ Completa '{task['name']}'", callback_data=f"complete_{task['task_id']}")
            ])
        reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None
        await send_and_track_message(update.message.reply_text, text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)

    async def assign_task_menu(self, update, context):
        chat_id = update.effective_chat.id
        user = update.effective_user
        db.add_family_member(chat_id, user.id, user.username, user.first_name)
        tasks = db.get_all_tasks()
        keyboard = []
        for task in tasks:
            keyboard.append([
                InlineKeyboardButton(f"{task['name']} ({task['points']}pt)", callback_data=f"assign_{task['id']}")
            ])
        keyboard.append([InlineKeyboardButton("🔙 Indietro", callback_data="main_menu")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        if update.message:
            await update.message.reply_text("*Scegli una task da assegnare:*", parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
        else:
            await update.callback_query.edit_message_text("*Scegli una task da assegnare:*", parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)

    async def button_handler(self, update, context):
        query = update.callback_query
        data = query.data
        chat_id = query.message.chat.id
        user_id = query.from_user.id
        if data == "main_menu":
            await query.edit_message_text("Menu principale. Usa i comandi o il menu.")
        elif data.startswith("assign_"):
            task_id = data.replace("assign_", "")
            members = db.get_family_members(chat_id)
            if not members:
                await query.edit_message_text("Nessun membro famiglia trovato. Usa /start da ogni account!")
                return
            keyboard = []
            for m in members:
                keyboard.append([
                    InlineKeyboardButton(f"👤 {m['first_name']}", callback_data=f"doassign_{task_id}_{m['user_id']}")
                ])
            keyboard.append([InlineKeyboardButton("🔙 Indietro", callback_data="assign_menu")])
            reply_markup = InlineKeyboardMarkup(keyboard)
            task = db.get_task_by_id(task_id)
            await query.edit_message_text(
                f"*A chi vuoi assegnare:*\n\n📋 {task['name']} ({task['points']}pt)",
                parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
        elif data.startswith("doassign_"):
            _, task_id, target_id = data.split("_", 2)
            try:
                db.assign_task(chat_id, task_id, int(target_id), user_id)
                await query.edit_message_text("✅ Task assegnata con successo!")
            except ValueError:
                await query.edit_message_text("❌ Task già assegnata a questo utente!")
        elif data == "assign_menu":
            class DummyUpdate:
                message = query.message
                callback_query = None
            await self.assign_task_menu(DummyUpdate(), context)
        elif data == "show_my_tasks":
            await self.my_tasks(update, context)
        elif data.startswith("complete_"):
            task_id = data.replace("complete_", "")
            user_id = query.from_user.id
            chat_id = query.message.chat.id
            try:
                # Usa la logica reale di completamento
                ok = db.complete_task(chat_id, task_id, user_id)
                if ok:
                    await query.edit_message_text("🎉 Task completata! Ottimo lavoro.")
                else:
                    await query.edit_message_text("❌ Task non trovata o già completata.")
            except Exception as exc:
                await query.edit_message_text(f"❌ Errore nel completamento: {exc}")
        elif data.startswith("cat_"):
            cat = data.replace("cat_", "")
            tasks = db.get_all_tasks()
            # Raggruppa le task per categoria
            cat_map = {
                "pulizie": lambda n: "pulizia" in n,
                "cucina": lambda n: "cucina" in n or "cena" in n,
                "spesa": lambda n: "spesa" in n,
                "bucato": lambda n: "bucato" in n,
                "giardino": lambda n: "giardino" in n,
                "animali": lambda n: "animali" in n,
                "auto": lambda n: "auto" in n,
                "altro": lambda n: True
            }
            filtered = [t for t in tasks if cat_map.get(cat, lambda n: False)(t['name'].lower())]
            if not filtered:
                await query.edit_message_text(f"Nessuna task trovata per {cat.title()}.")
                return
            keyboard = [
                [InlineKeyboardButton(f"{t['name']}", callback_data=f"assign_{t['id']}")]
                for t in filtered
            ]
            keyboard.append([InlineKeyboardButton("🔙 Indietro", callback_data="tasks_menu")])
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(f"*{cat.title()}* - Scegli una task:", parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
        elif data == "tasks_menu":
            # Torna al menu categorie
            categories = [
                ("Pulizie", "🧹"),
                ("Cucina", "🍽️"),
                ("Spesa", "🛒"),
                ("Bucato", "🧺"),
                ("Giardino", "🌳"),
                ("Animali", "🐾"),
                ("Auto", "🚗"),
                ("Altro", "📦")
            ]
            keyboard = [
                [InlineKeyboardButton(f"{emoji} {cat}", callback_data=f"cat_{cat.lower()}")]
                for cat, emoji in categories
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text("📋 *Scegli una categoria di task:*", parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
        else:
            await query.answer("Funzione non ancora implementata.")

    async def handle_message(self, update, context):
        user = update.effective_user
        chat_id = update.effective_chat.id
        try:
            db.add_family_member(chat_id, user.id, user.username, user.first_name)
        except Exception as e:
            logger.error(f"Errore auto-add membro su messaggio: {e}")
        text = update.message.text.lower()
        # Supporta anche i bottoni con emoji
        if text in ["/tasks", "tasks", "📋 tasks"]:
            await self.show_tasks(update, context)
        elif text in ["/mytasks", "mytasks", "📝 mytasks"]:
            await self.my_tasks(update, context)
        elif text in ["/leaderboard", "leaderboard", "🏆 leaderboard"]:
            await self.leaderboard(update, context)
        elif text in ["/stats", "stats", "📊 stat", "stat"]:
            await self.stats(update, context)
        elif text in ["/help", "help", "ℹ️ help"]:
            await self.help_command(update, context)
        elif "assegna" in text:
            await self.assign_task_menu(update, context)
        elif "task" in text:
            await self.show_tasks(update, context)
        elif "classifica" in text or "leaderboard" in text:
            await self.leaderboard(update, context)
        elif "stat" in text:
            await self.stats(update, context)
        else:
            await update.message.reply_text("Messaggio ricevuto. Usa il menu o i comandi.")

    # async def assign_category_menu(self, query, catid):
    #     """Mostra le task della categoria scelta, indicando se già assegnate"""
    #     tasks = db.get_default_tasks()
    #     chat_id = query.message.chat.id
    #     assigned = db.get_assigned_tasks_for_chat(chat_id)
    #     members = {m['user_id']: m['first_name'] for m in db.get_family_members(chat_id)}
    #     assigned_map = {}
    #     for v in assigned:
    #         assigned_map.setdefault(v['task_id'], []).append(members.get(v['assigned_to'], str(v['assigned_to'])))
    #     # cat = self.TASK_CATEGORIES[catid]  # TASK_CATEGORIES non definito
    #     # keyboard = []
    #     # for task_id in cat['tasks']:
    #     #     task = tasks.get(task_id)
    #     #     if not task:
    #     #         continue
    #     #     if task_id in assigned_map and len(assigned_map[task_id]) >= len(members):
    #     #         # Task già assegnata a tutti
    #     #         button_text = f"{task['name']} (assegnata a tutti)"
    #     #         keyboard.append([InlineKeyboardButton(button_text, callback_data="none")])
    #     #     else:
    #     #         button_text = task['name']
    #     #         keyboard.append([InlineKeyboardButton(button_text, callback_data=f"choose_task_{task_id}")])
    #     # keyboard.append([InlineKeyboardButton("🔙 Indietro", callback_data="assign_menu")])
    #     # reply_markup = InlineKeyboardMarkup(keyboard)
    #     # await query.edit_message_text(
    #     #     f"*{cat['label']} - Task disponibili:*", parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup
    #     # )

    async def choose_assign_target(self, query, task_id):
        """Mostra i membri della famiglia per scegliere a chi assegnare la task"""
        chat_id = query.message.chat.id
        current_user = query.from_user.id
        members = db.get_family_members(chat_id)
        already_assigned = [a['assigned_to'] for a in db.get_assigned_tasks_for_chat(chat_id) if a['task_id'] == task_id]
        keyboard = []
        if current_user not in already_assigned:
            keyboard.append([InlineKeyboardButton("🫵 Assegna a me", callback_data=f"assign_self_{task_id}")])
        for m in members:
            if m['user_id'] != current_user and m['user_id'] not in already_assigned:
                keyboard.append([InlineKeyboardButton(f"👤 {m['first_name']}", callback_data=f"assign_{task_id}_{m['user_id']}")])
        for m in members:
            if m['user_id'] in already_assigned:
                keyboard.append([InlineKeyboardButton(f"✅ {m['first_name']} (già assegnata)", callback_data="none")])
        keyboard.append([InlineKeyboardButton("🔙 Indietro", callback_data="assign_menu")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        task = db.get_task_by_id(task_id)
        message_text = (
            f"*🎯 A chi vuoi assegnare:*\n\n"
            f"📋 **{task['name']}**\n"
            f"⭐ {task['points']} punti | ⏱️ ~{task['time_minutes']} minuti\n\n"
            f"👥 *Scegli un membro della famiglia:*"
        )
        await query.edit_message_text(
            message_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )

    async def handle_assign(self, query, task_id, target_user_id):
        """Gestisce l'assegnazione effettiva della task"""
        chat_id = query.message.chat.id
        assigned_by = query.from_user.id
        try:
            db.assign_task(chat_id, task_id, target_user_id, assigned_by)
            members = db.get_family_members(chat_id)
            target_member = next((m for m in members if m['user_id'] == target_user_id), None)
            if target_user_id == assigned_by:
                target_name = "te stesso"
            else:
                target_name = target_member['first_name'] if target_member else f"Utente {target_user_id}"
            keyboard = [
                [InlineKeyboardButton("📋 Le Mie Task", callback_data="show_my_tasks")],
                [InlineKeyboardButton("🎯 Assegna Altra Task", callback_data="assign_menu")],
                [InlineKeyboardButton("🔙 Menu Principale", callback_data="main_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            task = db.get_task_by_id(task_id)
            success_message = (
                f"✅ *Task Assegnata con Successo!*\n\n"
                f"📋 **{task['name']}**\n"
                f"👤 **Assegnata a:** {target_name}\n"
                f"⭐ **Punti:** {task['points']}\n"
                f"⏱️ **Tempo stimato:** ~{task['time_minutes']} minuti\n"
                f"📅 **Scadenza:** 3 giorni\n\n"
                f"💡 *La task è ora visibile nelle attività dell'utente!*"
            )
            await query.edit_message_text(
                success_message,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
        except ValueError:
            await query.edit_message_text("❌ Task già assegnata a questo utente!", parse_mode=ParseMode.MARKDOWN)
        except Exception as exc:
            await query.edit_message_text(f"❌ Errore nell'assegnazione: {exc}", parse_mode=ParseMode.MARKDOWN)
