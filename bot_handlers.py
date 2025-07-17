from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.constants import ParseMode
from telegram.ext import ContextTypes
import logging
from db import FamilyTaskDB
from utils import send_and_track_message

logger = logging.getLogger(__name__)

class FamilyTaskBot:
    def __init__(self):
        self.db = None
        
    def get_db(self):
        """Lazy initialization of database connection"""
        if self.db is None:
            self.db = FamilyTaskDB()
        return self.db
        
    def _is_uncategorized_task(self, task_name_lower):
        """Check if a task doesn't belong to any specific category"""
        # Check categories in priority order (same as CATEGORY_MAP)
        priority_categories = ["animali", "cucina", "spesa", "pulizie", "bucato", "giardino", "auto", "casa"]
        
        for cat_key in priority_categories:
            if cat_key in self.CATEGORY_MAP:
                if self.CATEGORY_MAP[cat_key](task_name_lower):
                    return False
        return True
        
    # Categories configuration with improved visual design
    CATEGORIES = [
        ("Pulizie", "🧹", "Mantieni la casa pulita e ordinata"),
        ("Cucina", "🍽️", "Gestisci cucina e pasti"),
        ("Spesa", "🛒", "Acquisti e rifornimenti"),
        ("Bucato", "🧺", "Lavaggio e cura vestiti"),
        ("Giardino", "🌳", "Cura di piante e spazi esterni"),
        ("Animali", "🐾", "Cura degli animali domestici"),
        ("Auto", "🚗", "Manutenzione e pulizia auto"),
        ("Casa", "🏠", "Organizzazione e manutenzione"),
        ("Altro", "📦", "Task varie e personalizzate")
    ]
    
    # Category mapping for filtering tasks - ordered by priority to avoid overlaps
    CATEGORY_MAP = {
        "animali": lambda n: "animali" in n or ("lettiera" in n and "gatto" in n),
        "cucina": lambda n: ("cucina" in n and "pulizia" not in n) or "cena" in n or ("forno" in n and "pulire" not in n) or ("frigorifero" in n and "pulire" not in n) or "lavastoviglie" in n or "tavola" in n,
        "spesa": lambda n: ("spesa" in n) or ("dispensa" in n and "organizzare" not in n),
        "pulizie": lambda n: "pulizia" in n or "pulire" in n or "spolverare" in n or "aspirapolvere" in n or ("scale" in n and "pulire" in n),
        "bucato": lambda n: "bucato" in n or "lenzuola" in n or "stendere" in n,
        "giardino": lambda n: "giardino" in n or "piante" in n or "foglie" in n,
        "auto": lambda n: "auto" in n,
        "casa": lambda n: "riordinare" in n or "organizzare" in n or "fare i letti" in n or "spazzatura" in n or "buttare" in n or "cambiare i filtri" in n or "rifiuti" in n,
        "altro": lambda n: self._is_uncategorized_task(n)
    }
    async def start(self, update, context):
        user = update.effective_user
        chat_id = update.effective_chat.id
        try:
            self.get_db().add_family_member(chat_id, user.id, user.username, user.first_name)
        except Exception as e:
            logger.error(f"Errore add_family_member: {e}")
        
        # Get user stats to personalize welcome message
        stats = self.get_db().get_user_stats(user.id)
        
        if stats and stats['tasks_completed'] > 0:
            text = (
                f"🎉 Bentornato, {user.first_name}!\n\n"
                f"📊 Il tuo progresso:\n"
                f"⭐ {stats['total_points']} punti • 🏅 Livello {stats['level']}\n"
                f"✅ {stats['tasks_completed']} task completate\n\n"
                "🏠 Gestisci le attività della tua famiglia con il menu qui sotto:"
            )
        else:
            text = (
                f"👋 Benvenuto, {user.first_name}!\n\n"
                "🏠 **Family Task Manager** ti aiuta a organizzare le attività domestiche in famiglia!\n\n"
                "🌟 **Funzionalità principali:**\n"
                "• 📋 Assegna e completa task\n"
                "• 🏆 Guadagna punti e livelli\n"
                "• 📊 Visualizza statistiche\n"
                "• 👥 Compete con la famiglia\n\n"
                "💡 Inizia esplorando le task disponibili!"
            )
        
        keyboard = [
            ["📋 Tutte le Task", "📝 Le Mie Task"],
            ["🏆 Classifica", "📊 Statistiche"],
            ["❓ Aiuto", "⚙️ Gestione"]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)
        if update.message:
            await send_and_track_message(update.message.reply_text, text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
        elif update.callback_query:
            await send_and_track_message(update.callback_query.message.reply_text, text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)

    async def help_command(self, update, context):
        text = (
            "📚 **Guida Family Task Manager**\n\n"
            "🎯 **Comandi principali:**\n"
            "• `/start` - Menu principale\n"
            "• `/tasks` - Elenco task per categoria\n"
            "• `/mytasks` - Le tue task assegnate\n"
            "• `/leaderboard` - Classifica famiglia\n"
            "• `/stats` - Le tue statistiche\n"
            "• `/help` - Questa guida\n\n"
            "🎮 **Come funziona:**\n"
            "1️⃣ Scegli una categoria di task\n"
            "2️⃣ Assegna task ai membri famiglia\n"
            "3️⃣ Completa le task per guadagnare punti\n"
            "4️⃣ Scala la classifica e aumenta il tuo livello!\n\n"
            "🏆 **Sistema punti:**\n"
            "• Ogni task ha un valore in punti\n"
            "• 50 punti = 1 livello in più\n"
            "• Le task completate vanno in archivio\n\n"
            "💡 **Suggerimento:** Usa i bottoni del menu per una navigazione più rapida!"
        )
        await send_and_track_message(update.message.reply_text, text, parse_mode=ParseMode.MARKDOWN)

    async def leaderboard(self, update, context):
        chat_id = update.effective_chat.id
        leaderboard = self.get_db().get_leaderboard(chat_id)
        if not leaderboard:
            text = (
                "📊 **Classifica Famiglia**\n\n"
                "🚫 Nessuna attività completata ancora!\n\n"
                "💡 **Per iniziare:**\n"
                "1️⃣ Vai su 📋 Tutte le Task\n"
                "2️⃣ Scegli una categoria\n"
                "3️⃣ Assegna una task a te stesso o ad altri\n"
                "4️⃣ Completa la task per apparire in classifica!\n\n"
                "🏆 La competizione ti aspetta!"
            )
            await send_and_track_message(update.message.reply_text, text, parse_mode=ParseMode.MARKDOWN)
            return
            
        text = "🏆 **Classifica Famiglia**\n\n"
        for i, entry in enumerate(leaderboard, 1):
            if i == 1:
                pos = "🥇"
                badge = "👑"
            elif i == 2:
                pos = "🥈"
                badge = "🌟"
            elif i == 3:
                pos = "🥉"
                badge = "⭐"
            else:
                pos = f"{i}°"
                badge = "🏃"
                
            # Calculate progress to next level
            current_level_points = (entry['level'] - 1) * 50
            next_level_points = entry['level'] * 50
            progress = entry['total_points'] - current_level_points
            needed = next_level_points - entry['total_points']
            
            text += (
                f"{pos} {badge} **{entry['first_name']}**\n"
                f"    ⭐ {entry['total_points']} punti • 🏅 Livello {entry['level']}\n"
                f"    ✅ {entry['tasks_completed']} task completate\n"
                f"    📈 {progress}/50 punti al prossimo livello\n\n"
            )
            
        text += "💡 Completa più task per scalare la classifica!"
        await send_and_track_message(update.message.reply_text, text, parse_mode=ParseMode.MARKDOWN)

    async def stats(self, update, context):
        user = update.effective_user
        stats = self.get_db().get_user_stats(user.id)
        if not stats:
            text = (
                f"📊 **Statistiche di {user.first_name}**\n\n"
                "🆕 **Benvenuto nel Family Task Manager!**\n\n"
                "📈 **I tuoi progressi:**\n"
                "⭐ Punti: 0\n"
                "✅ Task completate: 0\n"
                "🏅 Livello: 1\n"
                "🔥 Streak: 0\n\n"
                "🎯 **Prossimo obiettivo:**\n"
                "Completa la tua prima task per guadagnare punti!\n\n"
                "💡 Vai su 📋 Tutte le Task per iniziare!"
            )
            await send_and_track_message(update.message.reply_text, text, parse_mode=ParseMode.MARKDOWN)
            return
            
        # Calculate progress to next level
        current_level_points = (stats['level'] - 1) * 50
        next_level_points = stats['level'] * 50
        progress = stats['total_points'] - current_level_points
        needed = next_level_points - stats['total_points']
        progress_bar = "▓" * (progress // 5) + "░" * ((50 - progress) // 5)
        
        # Performance badge based on tasks completed
        if stats['tasks_completed'] >= 50:
            badge = "🏆 Task Master"
        elif stats['tasks_completed'] >= 25:
            badge = "🌟 Task Expert"
        elif stats['tasks_completed'] >= 10:
            badge = "⭐ Task Warrior"
        elif stats['tasks_completed'] >= 5:
            badge = "🏃 Task Runner"
        else:
            badge = "🌱 Task Beginner"
            
        text = (
            f"📊 **Statistiche di {user.first_name}**\n\n"
            f"🏅 **{badge}**\n\n"
            f"📈 **I tuoi progressi:**\n"
            f"⭐ **Punti totali:** {stats['total_points']}\n"
            f"✅ **Task completate:** {stats['tasks_completed']}\n"
            f"🏅 **Livello:** {stats['level']}\n"
            f"🔥 **Streak:** {stats['streak']}\n\n"
            f"📊 **Progresso livello:**\n"
            f"{progress_bar}\n"
            f"🎯 {progress}/50 punti • {needed} punti al livello {stats['level'] + 1}\n\n"
            f"💡 **Media punti per task:** {stats['total_points'] // max(stats['tasks_completed'], 1)}"
        )
        await send_and_track_message(update.message.reply_text, text, parse_mode=ParseMode.MARKDOWN)

    async def show_tasks(self, update, context):
        chat_id = update.effective_chat.id
        total_tasks = len(self.get_db().get_all_tasks())
        assigned_tasks = len(self.get_db().get_assigned_tasks_for_chat(chat_id))
        available_tasks = total_tasks - assigned_tasks
        
        text = (
            "📋 **Scegli una categoria di task:**\n\n"
            f"📊 **Stato attuale:**\n"
            f"• 📦 Task totali: {total_tasks}\n"
            f"• ✅ Task assegnate: {assigned_tasks}\n"
            f"• 🆓 Task disponibili: {available_tasks}\n\n"
            "👇 Seleziona una categoria per vedere le task disponibili:"
        )
        
        keyboard = []
        for cat, emoji, description in self.CATEGORIES:
            # Count tasks in this category
            tasks = self.get_db().get_all_tasks()
            assigned = self.get_db().get_assigned_tasks_for_chat(chat_id)
            assigned_task_ids = set(a['task_id'] for a in assigned)
            
            if cat.lower() == "altro":
                cat_tasks = [t for t in tasks if self._is_uncategorized_task(t['name'].lower())]
            else:
                cat_tasks = []
                for task in tasks:
                    task_name_lower = task['name'].lower()
                    priority_categories = ["animali", "cucina", "spesa", "pulizie", "bucato", "giardino", "auto", "casa"]
                    for pcat in priority_categories:
                        if pcat in self.CATEGORY_MAP and self.CATEGORY_MAP[pcat](task_name_lower):
                            if pcat == cat.lower():
                                cat_tasks.append(task)
                            break
            
            available_in_cat = len([t for t in cat_tasks if t['id'] not in assigned_task_ids])
            total_in_cat = len(cat_tasks)
            
            if available_in_cat > 0:
                status = f"({available_in_cat}/{total_in_cat} disponibili)"
            elif total_in_cat > 0:
                status = "(tutte assegnate)"
            else:
                status = "(vuota)"
                
            keyboard.append([InlineKeyboardButton(
                f"{emoji} {cat} {status}", 
                callback_data=f"cat_{cat.lower()}"
            )])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await send_and_track_message(update.message.reply_text, text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)

    async def my_tasks(self, update, context):
        user = update.effective_user
        chat_id = update.effective_chat.id
        tasks = self.get_db().get_user_assigned_tasks(chat_id, user.id)
        
        if not tasks:
            text = (
                "📝 **Le tue task assegnate**\n\n"
                "🤷‍♂️ Non hai task assegnate al momento!\n\n"
                "💡 **Per iniziare:**\n"
                "• Vai su 📋 Tutte le Task\n"
                "• Scegli una categoria\n"
                "• Assegnati una task\n\n"
                "🎯 Le task completate ti faranno guadagnare punti!"
            )
            await send_and_track_message(update.message.reply_text, text, parse_mode=ParseMode.MARKDOWN)
            return
            
        total_points = sum(task['points'] for task in tasks)
        total_time = sum(task['time_minutes'] for task in tasks)
        
        text = (
            f"📝 **Le tue task assegnate**\n\n"
            f"📊 **Riepilogo:**\n"
            f"• 📦 Task da completare: {len(tasks)}\n"
            f"• ⭐ Punti totali in palio: {total_points}\n"
            f"• ⏱️ Tempo stimato: ~{total_time} minuti\n\n"
            "👇 **Clicca per completare:**\n"
        )
        
        keyboard = []
        for i, task in enumerate(tasks, 1):
            # Add difficulty indicator based on time
            if task['time_minutes'] <= 10:
                difficulty = "🟢"  # Easy
            elif task['time_minutes'] <= 25:
                difficulty = "🟡"  # Medium
            else:
                difficulty = "🔴"  # Hard
                
            text += f"{i}. {difficulty} **{task['name']}**\n"
            text += f"   ⭐ {task['points']} pt • ⏱️ ~{task['time_minutes']} min\n\n"
            
            keyboard.append([
                InlineKeyboardButton(
                    f"✅ Completa: {task['name'][:25]}{'...' if len(task['name']) > 25 else ''}", 
                    callback_data=f"complete_{task['task_id']}"
                )
            ])
        
        keyboard.append([
            InlineKeyboardButton("🔙 Menu Principale", callback_data="main_menu")
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await send_and_track_message(update.message.reply_text, text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)

    async def assign_task_menu(self, update, context):
        chat_id = update.effective_chat.id
        user = update.effective_user
        self.get_db().add_family_member(chat_id, user.id, user.username, user.first_name)
        tasks = self.get_db().get_all_tasks()
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
            members = self.get_db().get_family_members(chat_id)
            if not members:
                text = (
                    "👥 **Nessun membro famiglia trovato!**\n\n"
                    "🚀 **Per aggiungere membri:**\n"
                    "1️⃣ Ogni persona deve usare /start nel gruppo\n"
                    "2️⃣ Il bot aggiungerà automaticamente tutti\n\n"
                    "💡 Solo i membri registrati possono ricevere task!"
                )
                keyboard = [[InlineKeyboardButton("🔙 Indietro", callback_data="tasks_menu")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
                return
                
            # Get task details
            task = self.get_db().get_task_by_id(task_id)
            if not task:
                await query.edit_message_text("❌ Task non trovata!")
                return
            
            # Check who already has this task assigned
            assigned_tasks = self.get_db().get_assigned_tasks_for_chat(chat_id)
            already_assigned_users = [a['assigned_to'] for a in assigned_tasks if a['task_id'] == task_id]
            
            # Add difficulty indicator
            if task['time_minutes'] <= 10:
                difficulty = "🟢 Facile"
            elif task['time_minutes'] <= 25:
                difficulty = "🟡 Medio"
            else:
                difficulty = "🔴 Difficile"
                
            text = (
                f"🎯 **Assegna Task**\n\n"
                f"📋 **{task['name']}**\n"
                f"⭐ **Punti:** {task['points']}\n"
                f"⏱️ **Tempo stimato:** ~{task['time_minutes']} minuti\n"
                f"📊 **Difficoltà:** {difficulty}\n\n"
                f"👥 **Scegli a chi assegnare questa task:**\n"
            )
            
            keyboard = []
            current_user = query.from_user.id
            
            # Add self-assignment option if not already assigned
            if current_user not in already_assigned_users:
                keyboard.append([InlineKeyboardButton(
                    "🫵 Assegna a me stesso", 
                    callback_data=f"doassign_{current_user}_{task_id}"
                )])
            
            # Add other family members
            for m in members:
                if m['user_id'] in already_assigned_users:
                    keyboard.append([InlineKeyboardButton(
                        f"✅ {m['first_name']} (già assegnata)", 
                        callback_data="none"
                    )])
                elif m['user_id'] != current_user:
                    keyboard.append([InlineKeyboardButton(
                        f"👤 Assegna a {m['first_name']}", 
                        callback_data=f"doassign_{m['user_id']}_{task_id}"
                    )])
            
            keyboard.append([InlineKeyboardButton("🔙 Indietro", callback_data="assign_menu")])
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
        elif data.startswith("doassign_"):
            try:
                _, assigned_to, task_id = data.split("_", 2)
                # Validazione robusta: assigned_to deve essere int
                if not assigned_to.isdigit():
                    await query.edit_message_text(f"❌ Errore: ID utente non valido ({assigned_to})")
                    return
                
                # Get task and assignee details
                task = self.get_db().get_task_by_id(task_id)
                members = self.get_db().get_family_members(chat_id)
                assignee = next((m for m in members if m['user_id'] == int(assigned_to)), None)
                
                # Assign the task
                self.get_db().assign_task(chat_id, task_id, int(assigned_to), user_id)
                
                # Create success message with enhanced feedback
                if int(assigned_to) == user_id:
                    assignee_name = "te stesso"
                    celebration = "💪"
                else:
                    assignee_name = assignee['first_name'] if assignee else f"Utente {assigned_to}"
                    celebration = "👏"
                
                keyboard = [
                    [InlineKeyboardButton("📝 Vedi Tutte le Mie Task", callback_data="show_my_tasks")],
                    [InlineKeyboardButton("🎯 Assegna Altra Task", callback_data="tasks_menu")],
                    [InlineKeyboardButton("🏆 Vedi Classifica", callback_data="show_leaderboard")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                success_message = (
                    f"{celebration} **Task Assegnata con Successo!**\n\n"
                    f"📋 **{task['name']}**\n"
                    f"👤 **Assegnata a:** {assignee_name}\n"
                    f"⭐ **Punti in palio:** {task['points']}\n"
                    f"⏱️ **Tempo stimato:** ~{task['time_minutes']} minuti\n\n"
                    f"💡 **Prossimi passi:**\n"
                    f"• La task appare ora nelle attività di {assignee_name}\n"
                    f"• Completa entro 3 giorni per ottimizzare il punteggio\n"
                    f"• Usa 📝 Le Mie Task per vedere tutte le tue attività"
                )
                
                await query.edit_message_text(
                    success_message,
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=reply_markup
                )
            except Exception as exc:
                await query.edit_message_text(
                    f"❌ **Errore nell'assegnazione**\n\n"
                    f"Dettagli: {exc}\n\n"
                    "💡 Riprova o contatta l'amministratore se il problema persiste."
                )
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
            
            # Get task details before completion
            task = self.get_db().get_task_by_id(task_id)
            if not task:
                await query.edit_message_text("❌ Task non trovata!")
                return
                
            try:
                # Show confirmation first
                keyboard = [
                    [InlineKeyboardButton("✅ Sì, completa!", callback_data=f"confirm_complete_{task_id}")],
                    [InlineKeyboardButton("❌ Annulla", callback_data="cancel_complete")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                text = (
                    f"🎯 **Conferma completamento**\n\n"
                    f"📋 **Task:** {task['name']}\n"
                    f"⭐ **Punti da guadagnare:** {task['points']}\n"
                    f"⏱️ **Tempo stimato:** ~{task['time_minutes']} minuti\n\n"
                    "🤔 Sei sicuro di aver completato questa task?"
                )
                
                await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
                
            except Exception as exc:
                await query.edit_message_text(f"❌ Errore nel caricamento task: {exc}")
        
        elif data.startswith("confirm_complete_"):
            task_id = data.replace("confirm_complete_", "")
            user_id = query.from_user.id
            chat_id = query.message.chat.id
            
            try:
                task = self.get_db().get_task_by_id(task_id)
                ok = self.get_db().complete_task(chat_id, task_id, user_id)
                
                if ok:
                    # Get updated user stats
                    user_stats = self.get_db().get_user_stats(user_id)
                    level_up = False
                    
                    # Check if user leveled up (basic check)
                    new_level = 1 + (user_stats['total_points'] // 50) if user_stats else 1
                    old_points = user_stats['total_points'] - task['points'] if user_stats else 0
                    old_level = 1 + (old_points // 50)
                    level_up = new_level > old_level
                    
                    keyboard = [
                        [InlineKeyboardButton("📝 Le Mie Task", callback_data="show_my_tasks")],
                        [InlineKeyboardButton("📊 Vedi Statistiche", callback_data="show_stats")],
                        [InlineKeyboardButton("🏆 Classifica", callback_data="show_leaderboard")]
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    
                    celebration = "🎉🎊" if level_up else "🎉"
                    level_msg = f"\n🆙 **LIVELLO AUMENTATO!** Ora sei livello {new_level}!" if level_up else ""
                    
                    success_text = (
                        f"{celebration} **Task Completata con Successo!**\n\n"
                        f"📋 **{task['name']}**\n"
                        f"⭐ **Punti guadagnati:** +{task['points']}\n"
                        f"📊 **Punti totali:** {user_stats['total_points'] if user_stats else task['points']}\n"
                        f"🏅 **Livello attuale:** {new_level}{level_msg}\n\n"
                        f"👏 Ottimo lavoro! La task è stata archiviata e può essere riassegnata."
                    )
                    
                    await query.edit_message_text(success_text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
                else:
                    await query.edit_message_text("❌ Task non trovata o già completata.")
            except Exception as exc:
                await query.edit_message_text(f"❌ Errore nel completamento: {exc}")
        
        elif data == "cancel_complete":
            await query.edit_message_text("❌ Completamento annullato.\n\n💡 Torna alle tue task quando hai finito!")
        
        elif data == "show_stats":
            # Create a dummy update object for stats
            class DummyUpdate:
                def __init__(self, user):
                    self.effective_user = user
                    self.message = query.message
            await self.stats(DummyUpdate(query.from_user), None)
            
        elif data == "show_leaderboard":
            # Create a dummy update object for leaderboard
            class DummyUpdate:
                def __init__(self, user, chat):
                    self.effective_user = user
                    self.effective_chat = chat
                    self.message = query.message
            await self.leaderboard(DummyUpdate(query.from_user, query.message.chat), None)
        elif data.startswith("cat_"):
            cat = data.replace("cat_", "")
            tasks = self.get_db().get_all_tasks()
            assigned = self.get_db().get_assigned_tasks_for_chat(chat_id)
            assigned_task_ids = set(a['task_id'] for a in assigned)
            
            # Find category info
            cat_info = next((c for c in self.CATEGORIES if c[0].lower() == cat), None)
            if not cat_info:
                await query.edit_message_text("❌ Categoria non trovata.")
                return
                
            cat_name, cat_emoji, cat_description = cat_info
            
            # Use priority-based filtering to avoid overlaps
            if cat == "altro":
                # Special handling for "Altro" category - only uncategorized tasks
                filtered = [t for t in tasks if self._is_uncategorized_task(t['name'].lower())]
            else:
                # For other categories, use priority order to avoid overlaps
                filtered = []
                priority_categories = ["animali", "cucina", "spesa", "pulizie", "bucato", "giardino", "auto", "casa"]
                for task in tasks:
                    task_name_lower = task['name'].lower()
                    assigned_category = None
                    for pcat in priority_categories:
                        if pcat in self.CATEGORY_MAP and self.CATEGORY_MAP[pcat](task_name_lower):
                            assigned_category = pcat
                            break
                    if assigned_category == cat:
                        filtered.append(task)
            
            if not filtered:
                text = (
                    f"{cat_emoji} **{cat_name}**\n\n"
                    f"📝 {cat_description}\n\n"
                    f"🚫 Nessuna task disponibile in questa categoria.\n\n"
                    "💡 Potrebbero essere tutte già assegnate!"
                )
                keyboard = [[InlineKeyboardButton("🔙 Tutte le Categorie", callback_data="tasks_menu")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
                return
            
            # Calculate statistics
            available_tasks = [t for t in filtered if t['id'] not in assigned_task_ids]
            assigned_tasks = [t for t in filtered if t['id'] in assigned_task_ids]
            total_points = sum(t['points'] for t in available_tasks)
            avg_time = sum(t['time_minutes'] for t in available_tasks) // max(len(available_tasks), 1)
            
            text = (
                f"{cat_emoji} **{cat_name}**\n\n"
                f"📝 {cat_description}\n\n"
                f"📊 **Statistiche categoria:**\n"
                f"• 📦 Task totali: {len(filtered)}\n"
                f"• 🆓 Disponibili: {len(available_tasks)}\n"
                f"• ✅ Già assegnate: {len(assigned_tasks)}\n"
                f"• ⭐ Punti disponibili: {total_points}\n"
                f"• ⏱️ Tempo medio: ~{avg_time} min\n\n"
                "👇 **Scegli una task da assegnare:**\n"
            )
            
            keyboard = []
            
            # Sort tasks by points (higher first) and then by time (shorter first)
            sorted_tasks = sorted(filtered, key=lambda x: (-x['points'], x['time_minutes']))
            
            for t in sorted_tasks:
                # Add difficulty indicator
                if t['time_minutes'] <= 10:
                    difficulty = "🟢"  # Easy
                elif t['time_minutes'] <= 25:
                    difficulty = "🟡"  # Medium
                else:
                    difficulty = "🔴"  # Hard
                
                if t['id'] in assigned_task_ids:
                    keyboard.append([InlineKeyboardButton(
                        f"✅ {t['name'][:30]}{'...' if len(t['name']) > 30 else ''} (assegnata)", 
                        callback_data="none"
                    )])
                else:
                    keyboard.append([InlineKeyboardButton(
                        f"{difficulty} {t['name'][:25]}{'...' if len(t['name']) > 25 else ''} ({t['points']}pt)", 
                        callback_data=f"assign_{t['id']}"
                    )])
            
            keyboard.append([InlineKeyboardButton("🔙 Tutte le Categorie", callback_data="tasks_menu")])
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
        elif data == "tasks_menu":
            # Return to categories menu with enhanced information
            chat_id = query.message.chat.id
            total_tasks = len(self.get_db().get_all_tasks())
            assigned_tasks = len(self.get_db().get_assigned_tasks_for_chat(chat_id))
            available_tasks = total_tasks - assigned_tasks
            
            text = (
                "📋 **Scegli una categoria di task:**\n\n"
                f"📊 **Stato attuale:**\n"
                f"• 📦 Task totali: {total_tasks}\n"
                f"• ✅ Task assegnate: {assigned_tasks}\n"
                f"• 🆓 Task disponibili: {available_tasks}\n\n"
                "👇 Seleziona una categoria per vedere le task disponibili:"
            )
            
            keyboard = []
            for cat, emoji, description in self.CATEGORIES:
                # Count tasks in this category (same logic as show_tasks)
                tasks = self.get_db().get_all_tasks()
                assigned = self.get_db().get_assigned_tasks_for_chat(chat_id)
                assigned_task_ids = set(a['task_id'] for a in assigned)
                
                if cat.lower() == "altro":
                    cat_tasks = [t for t in tasks if self._is_uncategorized_task(t['name'].lower())]
                else:
                    cat_tasks = []
                    for task in tasks:
                        task_name_lower = task['name'].lower()
                        priority_categories = ["animali", "cucina", "spesa", "pulizie", "bucato", "giardino", "auto", "casa"]
                        for pcat in priority_categories:
                            if pcat in self.CATEGORY_MAP and self.CATEGORY_MAP[pcat](task_name_lower):
                                if pcat == cat.lower():
                                    cat_tasks.append(task)
                                break
                
                available_in_cat = len([t for t in cat_tasks if t['id'] not in assigned_task_ids])
                total_in_cat = len(cat_tasks)
                
                if available_in_cat > 0:
                    status = f"({available_in_cat}/{total_in_cat})"
                elif total_in_cat > 0:
                    status = "(tutte assegnate)"
                else:
                    status = "(vuota)"
                    
                keyboard.append([InlineKeyboardButton(
                    f"{emoji} {cat} {status}", 
                    callback_data=f"cat_{cat.lower()}"
                )])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
        else:
            await query.answer("Funzione non ancora implementata.")

    async def handle_message(self, update, context):
        user = update.effective_user
        chat_id = update.effective_chat.id
        try:
            self.get_db().add_family_member(chat_id, user.id, user.username, user.first_name)
        except Exception as e:
            logger.error(f"Errore auto-add membro su messaggio: {e}")
        text = update.message.text.lower()
        
        # Enhanced message handling with new keyboard layout
        if text in ["/tasks", "tasks", "📋 tasks", "📋 tutte le task"]:
            await self.show_tasks(update, context)
        elif text in ["/mytasks", "mytasks", "📝 mytasks", "📝 le mie task"]:
            await self.my_tasks(update, context)
        elif text in ["/leaderboard", "leaderboard", "🏆 leaderboard", "🏆 classifica"]:
            await self.leaderboard(update, context)
        elif text in ["/stats", "stats", "📊 stat", "📊 statistiche"]:
            await self.stats(update, context)
        elif text in ["/help", "help", "❓ help", "❓ aiuto"]:
            await self.help_command(update, context)
        elif text in ["⚙️ gestione"]:
            # Management menu for future features
            await send_and_track_message(
                update.message.reply_text,
                "⚙️ **Menu Gestione**\n\nFunzionalità in arrivo:\n• Impostazioni famiglia\n• Task personalizzate\n• Notifiche\n\nUsa il menu principale per le funzioni disponibili.",
                parse_mode=ParseMode.MARKDOWN
            )
        elif "assegna" in text:
            await self.show_tasks(update, context)  # Changed to show categories first
        elif "task" in text:
            await self.show_tasks(update, context)
        elif "classifica" in text or "leaderboard" in text:
            await self.leaderboard(update, context)
        elif "stat" in text:
            await self.stats(update, context)
        else:
            # Friendly response for unrecognized messages
            keyboard = [
                ["📋 Tutte le Task", "📝 Le Mie Task"],
                ["🏆 Classifica", "📊 Statistiche"]
            ]
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            await send_and_track_message(
                update.message.reply_text,
                f"👋 Ciao {user.first_name}! Non ho capito il messaggio.\n\n💡 Usa il menu qui sotto o i comandi per navigare:",
                reply_markup=reply_markup
            )

    # async def assign_category_menu(self, query, catid):
    #     """Mostra le task della categoria scelta, indicando se già assegnate"""
    #     tasks = self.get_db().get_default_tasks()
    #     chat_id = query.message.chat.id
    #     assigned = self.get_db().get_assigned_tasks_for_chat(chat_id)
    #     members = {m['user_id']: m['first_name'] for m in self.get_db().get_family_members(chat_id)}
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
        members = self.get_db().get_family_members(chat_id)
        # Usa solo assegnazioni effettive (status='assigned')
        already_assigned = [a['assigned_to'] for a in self.get_db().get_assigned_tasks_for_chat(chat_id) if a['task_id'] == task_id]
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
        task = self.get_db().get_task_by_id(task_id)
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
            self.get_db().assign_task(chat_id, task_id, target_user_id, assigned_by)
            members = self.get_db().get_family_members(chat_id)
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
            task = self.get_db().get_task_by_id(task_id)
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
        except Exception as exc:
            await query.edit_message_text(f"❌ Errore nell'assegnazione: {exc}", parse_mode=ParseMode.MARKDOWN)
