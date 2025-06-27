import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from telegram.constants import ParseMode

# Configurazione logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Database simulato (in produzione usa un vero database)
class FamilyTaskDB:
    def __init__(self):
        self.data = {
            'families': {},
            'tasks': self.get_default_tasks(),
            'user_stats': {},
            'assigned_tasks': {},
            'completed_tasks': []
        }
        self.load_data()
    
    def get_default_tasks(self):
        """Task predefinite con punteggi basati sul tempo medio"""
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
    
    def save_data(self):
        """Salva i dati (in produzione salva su database)"""
        # In un'app reale, salveresti su database
        pass
    
    def load_data(self):
        """Carica i dati (in produzione carica da database)"""
        # In un'app reale, caricheresti da database
        pass
    
    def add_family_member(self, chat_id: int, user_id: int, username: str, first_name: str):
        """Aggiunge un membro alla famiglia"""
        if chat_id not in self.data['families']:
            self.data['families'][chat_id] = []
        
        # Controlla se l'utente è già nella famiglia
        for member in self.data['families'][chat_id]:
            if member['user_id'] == user_id:
                return False
        
        self.data['families'][chat_id].append({
            'user_id': user_id,
            'username': username,
            'first_name': first_name,
            'joined_date': datetime.now().isoformat()
        })
        
        # Inizializza le statistiche dell'utente
        if user_id not in self.data['user_stats']:
            self.data['user_stats'][user_id] = {
                'total_points': 0,
                'tasks_completed': 0,
                'level': 1,
                'badges': [],
                'streak': 0,
                'last_task_date': None
            }
        
        self.save_data()
        return True
    
    def get_family_members(self, chat_id: int):
        """Ottiene i membri della famiglia"""
        return self.data['families'].get(chat_id, [])
    
    def assign_task(self, chat_id: int, task_id: str, assigned_to: int, assigned_by: int):
        """Assegna una task"""
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
        self.save_data()
        print(f"DEBUG: Task assegnata - {task_key}")  # Debug log
    
    def complete_task(self, chat_id: int, task_id: str, user_id: int):
        """Completa una task"""
        task_key = f"{chat_id}_{task_id}_{user_id}"
        if task_key in self.data['assigned_tasks']:
            task_data = self.data['assigned_tasks'][task_key]
            points = self.data['tasks'][task_id]['points']
            
            # Aggiorna statistiche utente
            if user_id in self.data['user_stats']:
                stats = self.data['user_stats'][user_id]
                stats['total_points'] += points
                stats['tasks_completed'] += 1
                
                # Calcola livello (ogni 100 punti = 1 livello)
                stats['level'] = (stats['total_points'] // 100) + 1
                
                # Gestisci streak
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
                
                # Assegna badge
                self.check_and_assign_badges(user_id, stats)
            
            # Segna come completata
            self.data['completed_tasks'].append({
                **task_data,
                'completed_date': datetime.now().isoformat(),
                'points_earned': points
            })
            
            # Rimuovi dalle task assegnate
            del self.data['assigned_tasks'][task_key]
            self.save_data()
            return points
        return 0
    
    def check_and_assign_badges(self, user_id: int, stats: dict):
        """Controlla e assegna badge"""
        badges = stats.get('badges', [])
        
        # Badge per task completate
        if stats['tasks_completed'] >= 10 and 'rookie' not in badges:
            badges.append('rookie')
        if stats['tasks_completed'] >= 50 and 'expert' not in badges:
            badges.append('expert')
        if stats['tasks_completed'] >= 100 and 'master' not in badges:
            badges.append('master')
        
        # Badge per streak
        if stats['streak'] >= 7 and 'week_warrior' not in badges:
            badges.append('week_warrior')
        if stats['streak'] >= 30 and 'month_champion' not in badges:
            badges.append('month_champion')
        
        # Badge per punti
        if stats['total_points'] >= 500 and 'point_collector' not in badges:
            badges.append('point_collector')
        
        stats['badges'] = badges
    
    def get_leaderboard(self, chat_id: int):
        """Ottiene la classifica della famiglia"""
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

# Inizializza database
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
        """Crea la tastiera del menu principale"""
        keyboard = [
            [KeyboardButton("📋 Le Mie Task"), KeyboardButton("🎯 Assegna Task")],
            [KeyboardButton("🏆 Classifica"), KeyboardButton("📊 Statistiche")],
            [KeyboardButton("📚 Tutte le Task"), KeyboardButton("⚙️ Menu")]
        ]
        return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)
    
    def get_quick_actions_inline(self):
        """Crea bottoni inline per azioni rapide"""
        keyboard = [
            [InlineKeyboardButton("🎯 Assegna Task", callback_data="assign_menu"),
             InlineKeyboardButton("✅ Completa Task", callback_data="complete_menu")],
            [InlineKeyboardButton("🏆 Classifica", callback_data="show_leaderboard"),
             InlineKeyboardButton("📊 Le Mie Stats", callback_data="show_my_stats")],
            [InlineKeyboardButton("🔄 Aggiorna Menu", callback_data="refresh_menu")]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /start"""
        user = update.effective_user
        chat_id = update.effective_chat.id
        
        # Aggiungi utente alla famiglia
        added = db.add_family_member(chat_id, user.id, user.username or '', user.first_name)
        
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
        
        # Invia anche il menu inline per azioni rapide
        await update.message.reply_text(
            "*🚀 Menu Rapido - Azioni Principali:*",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=inline_keyboard
        )
    
    async def show_tasks(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Mostra tutte le attività disponibili"""
        tasks_text = "*📋 Attività Disponibili:*\n\n"
        
        # Raggruppa le task per categoria
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
            [InlineKeyboardButton("📊 Statistiche Task", callback_data="task_stats")],
            [InlineKeyboardButton("🔙 Menu Principale", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(tasks_text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
    
    async def my_tasks(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Mostra le attività assegnate all'utente"""
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        
        print(f"DEBUG: Cercando task per user_id: {user_id}, chat_id: {chat_id}")
        print(f"DEBUG: Task assegnate nel database: {list(db.data['assigned_tasks'].keys())}")
        
        my_tasks = []
        for task_key, task_data in db.data['assigned_tasks'].items():
            print(f"DEBUG: Controllando task_key: {task_key}, assigned_to: {task_data.get('assigned_to')}, chat_id: {task_data.get('chat_id')}")
            if task_data['assigned_to'] == user_id and task_data['chat_id'] == chat_id:
                task_id = task_data['task_id']
                if task_id in db.data['tasks']:  # Verifica che la task esista ancora
                    task_info = db.data['tasks'][task_id]
                    due_date = datetime.fromisoformat(task_data['due_date'])
                    
                    my_tasks.append({
                        'task_key': task_key,
                        'task_info': task_info,
                        'due_date': due_date,
                        'task_id': task_id
                    })
        
        print(f"DEBUG: Task trovate per l'utente: {len(my_tasks)}")
        
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
            
            # Bottone per completare ogni task
            button_text = f"✅ {task['task_info']['name'][:15]}..."
            keyboard.append([InlineKeyboardButton(
                button_text, 
                callback_data=f"complete_{task['task_id']}"
            )])
        
        # Bottoni azioni aggiuntive
        keyboard.extend([
            [InlineKeyboardButton("🎯 Assegna Altra Task", callback_data="assign_menu")],
            [InlineKeyboardButton("📊 Mie Statistiche", callback_data="show_my_stats")],
            [InlineKeyboardButton("🔙 Menu Principale", callback_data="main_menu")]
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(tasks_text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
    
    async def leaderboard(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Mostra la classifica famiglia"""
        chat_id = update.effective_chat.id
        leaderboard = db.get_leaderboard(chat_id)
        
        if not leaderboard:
            keyboard = [
                [InlineKeyboardButton("👥 Invita Famiglia", callback_data="invite_family")],
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
        """Mostra le statistiche dell'utente"""
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
        
        # Calcola progressi verso prossimo livello
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

*🎯 Prossimi Obiettivi:*
"""
        
        # Aggiungi obiettivi dinamici
        objectives = []
        if stats['tasks_completed'] < 10:
            objectives.append(f"• Badge Rookie: {10 - stats['tasks_completed']} task")
        elif stats['tasks_completed'] < 50:
            objectives.append(f"• Badge Expert: {50 - stats['tasks_completed']} task")
        elif stats['tasks_completed'] < 100:
            objectives.append(f"• Badge Master: {100 - stats['tasks_completed']} task")
        
        if stats['streak'] < 7:
            objectives.append(f"• Badge Week Warrior: {7 - stats['streak']} giorni streak")
        elif stats['streak'] < 30:
            objectives.append(f"• Badge Month Champion: {30 - stats['streak']} giorni streak")
        
        if stats['total_points'] < 500:
            objectives.append(f"• Badge Point Collector: {500 - stats['total_points']} punti")
        
        if not objectives:
            objectives.append("• 🎉 Hai completato tutti gli obiettivi!")
        
        stats_text += "\n".join(objectives)
        
        keyboard = [
            [InlineKeyboardButton("📋 Le Mie Task", callback_data="show_my_tasks")],
            [InlineKeyboardButton("🏆 Classifica", callback_data="show_leaderboard")],
            [InlineKeyboardButton("🎯 Assegna Task", callback_data="assign_menu")],
            [InlineKeyboardButton("🔙 Menu Principale", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(stats_text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando help"""
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
/assign - Assegna attività a qualcuno
/complete - Completa un'attività
/leaderboard - Classifica famiglia
/stats - Le tue statistiche personali

*🏅 Badge Disponibili:*
🥉 Rookie - 10 task completate
🥈 Expert - 50 task completate  
🥇 Master - 100 task completate
⚡ Week Warrior - 7 giorni di streak
👑 Month Champion - 30 giorni di streak
💎 Point Collector - 500 punti totali

*💡 Suggerimenti:*
• Completa attività ogni giorno per mantenere lo streak
• Le attività più lunghe danno più punti
• Assegna attività ai membri meno attivi
• Controlla la classifica per vedere chi è in testa!
        """
        
        await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)
    
    async def button_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Gestisce i callback dei bottoni"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        
        if data == "main_menu":
            await self.show_main_menu(query)
        elif data == "assign_menu":
            await self.show_assign_menu(query)
        elif data == "complete_menu":
            await self.show_complete_menu(query)
        elif data == "show_leaderboard":
            await self.show_leaderboard_inline(query)
        elif data == "show_my_stats":
            await self.show_stats_inline(query)
        elif data == "show_my_tasks":
            await self.show_my_tasks_inline(query)
        elif data == "show_all_tasks":
            await self.show_all_tasks_inline(query)
        elif data == "refresh_menu":
            await self.refresh_main_menu(query)
        elif data.startswith("category_"):
            category = data.replace("category_", "")
            await self.show_category_tasks(query, category)
        elif data == "assign_all_tasks":
            await self.show_all_tasks_for_assignment(query)
        elif data.startswith("assign_"):
            task_id = data.replace("assign_", "")
            await self.show_family_members_for_assignment(query, task_id)
        elif data.startswith("assign_to_"):
            parts = data.split("_")
            if len(parts) >= 4:
                task_id = parts[2]
                user_id = int(parts[3])
                await self.assign_task_to_user(query, task_id, user_id)
            else:
                await query.edit_message_text("❌ Errore nell'assegnazione task")
        elif data == "invite_info":
            await self.show_invite_info(query)
        elif data.startswith("complete_"):
            task_id = data.replace("complete_", "")
            await self.complete_task(query, task_id)
    
    async def show_main_menu(self, query):
        """Mostra il menu principale"""
        user = query.from_user
        quick_stats = ""
        
        if user.id in db.data['user_stats']:
            stats = db.data['user_stats'][user.id]
            quick_stats = f"\n*📊 I tuoi numeri:* Livello {stats['level']} • {stats['total_points']} punti • {stats['streak']} 🔥"
        
        main_text = f"""
🏠 *Family Task Manager*

Benvenuto {user.first_name}! {quick_stats}

Usa i bottoni qui sotto per navigare rapidamente:
        """
        
        inline_keyboard = self.get_quick_actions_inline()
        
        await query.edit_message_text(
            main_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=inline_keyboard
        )
    
    async def refresh_main_menu(self, query):
        """Aggiorna il menu principale"""
        await self.show_main_menu(query)
    
    async def show_leaderboard_inline(self, query):
        """Mostra classifica tramite inline"""
        chat_id = query.message.chat_id
        leaderboard = db.get_leaderboard(chat_id)
        
        if not leaderboard:
            keyboard = [[InlineKeyboardButton("🔙 Menu Principale", callback_data="main_menu")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                "👥 *Nessun membro registrato nella famiglia!*",
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
            leaderboard_text += f"⭐ {member['points']} | 📊 Lv.{member['level']} | 🔥 {member['streak']}\n"
            if badges_str:
                leaderboard_text += f"🏅 {badges_str}\n"
            leaderboard_text += "\n"
        
        keyboard = [
            [InlineKeyboardButton("📊 Mie Stats", callback_data="show_my_stats")],
            [InlineKeyboardButton("🎯 Assegna Task", callback_data="assign_menu")],
            [InlineKeyboardButton("🔄 Aggiorna", callback_data="show_leaderboard")],
            [InlineKeyboardButton("🔙 Menu", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(leaderboard_text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
    
    async def show_stats_inline(self, query):
        """Mostra statistiche tramite inline"""
        user_id = query.from_user.id
        
        if user_id not in db.data['user_stats']:
            keyboard = [
                [InlineKeyboardButton("🎯 Assegna Prima Task", callback_data="assign_menu")],
                [InlineKeyboardButton("🔙 Menu", callback_data="main_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                "📊 *Non hai ancora statistiche!*\n\nCompleta la prima attività per iniziare.",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
            return
        
        stats = db.data['user_stats'][user_id]
        badges_str = " ".join([self.badge_emojis.get(badge, "🏅") for badge in stats['badges']])
        
        # Progress bar per livello
        current_level_points = stats['total_points'] % 100
        points_to_next_level = 100 - current_level_points
        progress_bar = "▓" * (current_level_points // 10) + "░" * (10 - (current_level_points // 10))
        
        stats_text = f"""
*📊 Le Tue Statistiche*

👤 *Livello:* {stats['level']} 
⭐ *Punti:* {stats['total_points']} | ✅ *Task:* {stats['tasks_completed']}
🔥 *Streak:* {stats['streak']} giorni

*📈 Progresso al Livello {stats['level'] + 1}:*
{progress_bar} {current_level_points}/100

🏅 *Badge:* {badges_str if badges_str else 'Nessuno ancora 😢'}

*🎯 Prossimo obiettivo:* {points_to_next_level} punti al livello successivo
        """
        
        keyboard = [
            [InlineKeyboardButton("📋 Mie Task", callback_data="show_my_tasks")],
            [InlineKeyboardButton("🏆 Classifica", callback_data="show_leaderboard")],
            [InlineKeyboardButton("🔙 Menu", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(stats_text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
    
    async def show_my_tasks_inline(self, query):
        """Mostra le mie task tramite inline"""
        user_id = query.from_user.id
        chat_id = query.message.chat_id
        
        my_tasks = []
        for task_key, task_data in db.data['assigned_tasks'].items():
            if task_data['assigned_to'] == user_id and task_data['chat_id'] == chat_id:
                task_id = task_data['task_id']
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
                [InlineKeyboardButton("🎯 Assegna Task", callback_data="assign_menu")],
                [InlineKeyboardButton("🔙 Menu", callback_data="main_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                "📝 *Non hai task assegnate!*\n\nVuoi assegnarne una?",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
            return
        
        tasks_text = f"*📋 Le Tue Task ({len(my_tasks)}):*\n\n"
        keyboard = []
        
        for i, task in enumerate(my_tasks, 1):
            due_str = task['due_date'].strftime("%d/%m")
            days_left = (task['due_date'] - datetime.now()).days
            urgency = "🔴" if days_left <= 1 else "🟡" if days_left <= 2 else "🟢"
            
            tasks_text += f"*{i}.* {task['task_info']['name']}\n"
            tasks_text += f"⭐ {task['task_info']['points']} punti | 📅 {due_str} {urgency}\n\n"
            
            # Bottone per completare ogni task
            keyboard.append([InlineKeyboardButton(
                f"✅ Completa #{i}", 
                callback_data=f"complete_{task['task_id']}"
            )])
        
        keyboard.extend([
            [InlineKeyboardButton("🎯 Assegna Altra", callback_data="assign_menu")],
            [InlineKeyboardButton("🔙 Menu", callback_data="main_menu")]
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(tasks_text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
    
    async def show_all_tasks_inline(self, query):
        """Mostra tutte le task tramite inline"""
        tasks_text = "*📋 Attività Disponibili:*\n\n"
        
        # Raggruppa le task per categoria (versione compatta per inline)
        categories = {
            "🍽️ Cucina": ['cucina_pulizia', 'lavastoviglie'],
            "🧹 Pulizie": ['bagno_pulizia', 'aspirapolvere', 'pavimenti'],
            "👕 Bucato": ['bucato', 'stirare', 'letti'],
            "🌱 Altri": ['giardino', 'spazzatura', 'spesa', 'finestre']
        }
        
        for category, task_ids in categories.items():
            tasks_text += f"*{category}*\n"
            for task_id in task_ids:
                if task_id in db.data['tasks']:
                    task_data = db.data['tasks'][task_id]
                    tasks_text += f"  {task_data['name']} (⭐{task_data['points']})\n"
            tasks_text += "\n"
        
        keyboard = [
            [InlineKeyboardButton("🎯 Assegna Task", callback_data="assign_menu")],
            [InlineKeyboardButton("✅ Completa Task", callback_data="complete_menu")],
            [InlineKeyboardButton("🔙 Menu", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(tasks_text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
    
    async def show_complete_menu(self, query):
        """Mostra menu per completare task"""
        user_id = query.from_user.id
        chat_id = query.message.chat_id
        
        # Trova le task dell'utente
        my_tasks = []
        for task_key, task_data in db.data['assigned_tasks'].items():
            if task_data['assigned_to'] == user_id and task_data['chat_id'] == chat_id:
                task_id = task_data['task_id']
                task_info = db.data['tasks'][task_id]
                my_tasks.append({
                    'task_id': task_id,
                    'task_info': task_info
                })
        
        if not my_tasks:
            keyboard = [
                [InlineKeyboardButton("🎯 Assegna Task", callback_data="assign_menu")],
                [InlineKeyboardButton("🔙 Menu", callback_data="main_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                "📝 *Non hai task da completare!*\n\nVuoi assegnarne una?",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
            return
        
        keyboard = []
        for task in my_tasks:
            keyboard.append([InlineKeyboardButton(
                f"✅ {task['task_info']['name']} (⭐{task['task_info']['points']})",
                callback_data=f"complete_{task['task_id']}"
            )])
        
        keyboard.append([InlineKeyboardButton("🔙 Menu", callback_data="main_menu")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"*✅ Seleziona task da completare ({len(my_tasks)} disponibili):*",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
    
    async def show_assign_menu(self, query):
        """Mostra il menu per assegnare attività"""
        # Raggruppa task per categoria con bottoni
        keyboard = [
            [InlineKeyboardButton("🍽️ Cucina", callback_data="category_cucina")],
            [InlineKeyboardButton("🧹 Pulizie", callback_data="category_pulizie")],
            [InlineKeyboardButton("👕 Bucato & Casa", callback_data="category_bucato")],
            [InlineKeyboardButton("🌱 Esterni & Altro", callback_data="category_esterni")],
            [InlineKeyboardButton("📋 Tutte le Task", callback_data="assign_all_tasks")],
            [InlineKeyboardButton("🔙 Menu", callback_data="main_menu")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "*🎯 Seleziona Categoria per Assegnare Task:*\n\n"
            "Scegli una categoria o visualizza tutte le task disponibili:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
    
    async def show_category_tasks(self, query, category):
        """Mostra le task di una categoria specifica per assegnazione"""
        categories_map = {
            "cucina": {
                "name": "🍽️ Cucina",
                "tasks": ['cucina_pulizia', 'lavastoviglie']
            },
            "pulizie": {
                "name": "🧹 Pulizie", 
                "tasks": ['bagno_pulizia', 'aspirapolvere', 'pavimenti', 'finestre']
            },
            "bucato": {
                "name": "👕 Bucato & Casa",
                "tasks": ['bucato', 'stirare', 'letti']
            },
            "esterni": {
                "name": "🌱 Esterni & Altro",
                "tasks": ['giardino', 'spazzatura', 'spesa']
            }
        }
        
        if category not in categories_map:
            await query.edit_message_text("❌ Categoria non trovata")
            return
        
        cat_info = categories_map[category]
        tasks_text = f"*{cat_info['name']} - Seleziona Task:*\n\n"
        
        keyboard = []
        for task_id in cat_info['tasks']:
            if task_id in db.data['tasks']:
                task_data = db.data['tasks'][task_id]
                tasks_text += f"{task_data['name']}\n⭐ {task_data['points']} punti | ⏱️ ~{task_data['time_minutes']} min\n\n"
                
                keyboard.append([InlineKeyboardButton(
                    f"{task_data['name']} (⭐{task_data['points']})",
                    callback_data=f"assign_{task_id}"
                )])
        
        keyboard.extend([
            [InlineKeyboardButton("🔙 Categorie", callback_data="assign_menu")],
            [InlineKeyboardButton("🏠 Menu", callback_data="main_menu")]
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(tasks_text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
    
    async def show_all_tasks_for_assignment(self, query):
        """Mostra tutte le task per assegnazione"""
        tasks_text = "*📋 Tutte le Task - Seleziona da Assegnare:*\n\n"
        
        keyboard = []
        
        # Organizza per categoria
        categories = {
            "🍽️ Cucina": ['cucina_pulizia', 'lavastoviglie'],
            "🧹 Pulizie": ['bagno_pulizia', 'aspirapolvere', 'pavimenti', 'finestre'],
            "👕 Bucato": ['bucato', 'stirare', 'letti'],
            "🌱 Altri": ['giardino', 'spazzatura', 'spesa']
        }
        
        for category_name, task_ids in categories.items():
            tasks_text += f"*{category_name}*\n"
            for task_id in task_ids:
                if task_id in db.data['tasks']:
                    task_data = db.data['tasks'][task_id]
                    tasks_text += f"  {task_data['name']} (⭐{task_data['points']})\n"
                    
                    # Aggiungi bottone per ogni task
                    keyboard.append([InlineKeyboardButton(
                        f"{task_data['name'][:25]}... (⭐{task_data['points']})",
                        callback_data=f"assign_{task_id}"
                    )])
            tasks_text += "\n"
        
        keyboard.append([InlineKeyboardButton("🔙 Menu Assegnazione", callback_data="assign_menu")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(tasks_text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
    
    async def show_family_members_for_assignment(self, query, task_id):
        """Mostra i membri famiglia per assegnazione"""
        chat_id = query.message.chat_id
        current_user = query.from_user
        members = db.get_family_members(chat_id)
        
        # Verifica che la task esista
        if task_id not in db.data['tasks']:
            await query.edit_message_text("❌ Task non trovata!")
            return
        
        keyboard = []
        
        # Aggiungi prima "Assegna a me stesso"
        keyboard.append([InlineKeyboardButton(
            f"👤 {current_user.first_name} (io)",
            callback_data=f"assign_to_{task_id}_{current_user.id}"
        )])
        
        # Poi aggiungi gli altri membri della famiglia (escluso l'utente corrente)
        for member in members:
            if member['user_id'] != current_user.id:  # Escludi l'utente corrente per evitare duplicati
                keyboard.append([InlineKeyboardButton(
                    f"👤 {member['first_name']}",
                    callback_data=f"assign_to_{task_id}_{member['user_id']}"
                )])
        
        # Se non ci sono altri membri oltre l'utente corrente
        if len(members) <= 1:
            keyboard.append([InlineKeyboardButton(
                "👥 Invita altri membri della famiglia!",
                callback_data="invite_info"
            )])
        
        keyboard.append([InlineKeyboardButton("🔙 Indietro", callback_data="assign_menu")])
        
        task_name = db.data['tasks'][task_id]['name']
        task_points = db.data['tasks'][task_id]['points']
        task_time = db.data['tasks'][task_id]['time_minutes']
        
        assignment_text = f"""
*👥 Assegna Task:*

📋 *{task_name}*
⭐ {task_points} punti
⏱️ ~{task_time} minuti

*Seleziona a chi assegnare:*
        """
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            assignment_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
        """Gestisce i messaggi di testo dei bottoni della keyboard"""
        text = update.message.text
        
        if text == "📋 Le Mie Task":
            await self.my_tasks(update, context)
        elif text == "🎯 Assegna Task":
            # Mostra menu inline per assegnazione
            inline_keyboard = [
                [InlineKeyboardButton("🍽️ Cucina", callback_data="category_cucina")],
                [InlineKeyboardButton("🧹 Pulizie", callback_data="category_pulizie")],
                [InlineKeyboardButton("👕 Bucato & Casa", callback_data="category_bucato")],
                [InlineKeyboardButton("🌱 Esterni & Altro", callback_data="category_esterni")],
                [InlineKeyboardButton("📋 Tutte le Task", callback_data="assign_all_tasks")]
            ]
            reply_markup = InlineKeyboardMarkup(inline_keyboard)
            
            await update.message.reply_text(
                "*🎯 Seleziona Categoria per Assegnare Task:*",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
        elif text == "🏆 Classifica":
            await self.leaderboard(update, context)
        elif text == "📊 Statistiche":
            await self.stats(update, context)
        elif text == "📚 Tutte le Task":
            await self.show_tasks(update, context)
        elif text == "⚙️ Menu":
            # Mostra menu principale con bottoni inline
            inline_keyboard = self.get_quick_actions_inline()
            await update.message.reply_text(
                "*🏠 Menu Principale*\n\nSeleziona un'azione:",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=inline_keyboard
            )
        else:
            # Messaggio di default per comandi non riconosciuti
            await update.message.reply_text(
                "❓ Non ho capito. Usa i bottoni del menu o digita /help per l'aiuto!"
            )
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Mostra i membri famiglia per assegnazione"""
        chat_id = query.message.chat_id
        members = db.get_family_members(chat_id)
        
        keyboard = []
        for member in members:
            keyboard.append([InlineKeyboardButton(
                f"👤 {member['first_name']}",
                callback_data=f"assign_to_{task_id}_{member['user_id']}"
            )])
        
        keyboard.append([InlineKeyboardButton("🔙 Indietro", callback_data="assign_menu")])
        
        task_name = db.data['tasks'][task_id]['name']
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            f"*👥 Assegna '{task_name}' a:*",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
    
    async def assign_task_to_user(self, query, task_id, assigned_to):
        """Assegna attività a un utente"""
        chat_id = query.message.chat_id
        assigned_by = query.from_user.id
        
        print(f"DEBUG: Tentativo assegnazione - chat_id: {chat_id}, task_id: {task_id}, assigned_to: {assigned_to}")
        
        # Verifica che la task esista
        if task_id not in db.data['tasks']:
            await query.edit_message_text("❌ Task non trovata!")
            print(f"DEBUG: Task {task_id} non trovata in database")
            return
        
        # Verifica che non ci sia già una task identica assegnata allo stesso utente
        task_key = f"{chat_id}_{task_id}_{assigned_to}"
        if task_key in db.data['assigned_tasks']:
            await query.edit_message_text(
                "⚠️ *Task già assegnata!*\n\nQuesta attività è già stata assegnata a questo utente.",
                parse_mode=ParseMode.MARKDOWN
            )
            print(f"DEBUG: Task già assegnata - {task_key}")
            return
        
        # Assegna la task
        try:
            db.assign_task(chat_id, task_id, assigned_to, assigned_by)
            print(f"DEBUG: Task assegnata con successo - {task_key}")
        except Exception as e:
            print(f"DEBUG: Errore nell'assegnazione: {e}")
            await query.edit_message_text("❌ Errore nell'assegnazione della task")
            return
        
        task_data = db.data['tasks'][task_id]
        task_name = task_data['name']
        
        # Trova il nome dell'assegnatario
        assigned_to_name = "Utente sconosciuto"
        
        # Controlla se è l'utente stesso
        if assigned_to == assigned_by:
            assigned_to_name = f"{query.from_user.first_name} (te stesso)"
        else:
            # Cerca nei membri della famiglia
            members = db.get_family_members(chat_id)
            for member in members:
                if member['user_id'] == assigned_to:
                    assigned_to_name = member['first_name']
                    break
        
        keyboard = [
            [InlineKeyboardButton("🎯 Assegna Altra Task", callback_data="assign_menu")],
            [InlineKeyboardButton("📋 Vedi Task Assegnate", callback_data="show_my_tasks")],
            [InlineKeyboardButton("🏆 Vedi Classifica", callback_data="show_leaderboard")],
            [InlineKeyboardButton("🔙 Menu", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        success_text = f"""
✅ *Task Assegnata con Successo!*

📋 *{task_name}*
⭐ {task_data['points']} punti
⏱️ ~{task_data['time_minutes']} minuti

👤 *Assegnata a:* {assigned_to_name}
📅 *Scadenza:* {(datetime.now() + timedelta(days=3)).strftime('%d/%m/%Y')}

💡 *Suggerimento:* La persona assegnata può completare la task usando "📋 Le Mie Task"

🔍 *Debug Info:* Task key: `{task_key}`
        """
        
        await query.edit_message_text(
            success_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
    
    async def show_invite_info(self, query):
        """Mostra informazioni su come invitare membri famiglia"""
        # Usa il context.bot invece di query.bot 
        try:
            # Ottieni il bot dalle informazioni del query
            bot_username = query.from_user.username or "family_task_bot"  # fallback
            invite_text = f"""
*👥 Invita la Famiglia!*

Per aggiungere membri alla famiglia:

1. **Condividi questo bot:**
   Cerca `@{bot_username}` su Telegram

2. **Oppure condividi il link:**
   Invia loro questo messaggio per iniziare

3. **Ogni membro deve fare:**
   `/start` nel bot

4. **Automaticamente** appariranno nella classifica e potranno ricevere task!

💡 *Suggerimento:* Più membri = più divertimento e competizione! 🏆
            """
        except:
            # Fallback se non riusciamo a ottenere il username
            invite_text = """
*👥 Invita la Famiglia!*

Per aggiungere membri alla famiglia:

1. **Condividi questo bot**
2. **Ogni membro deve fare** `/start`
3. **Automaticamente** appariranno nella classifica!

💡 *Suggerimento:* Più membri = più divertimento! 🏆
            """
        
        keyboard = [
            [InlineKeyboardButton("🔙 Torna Assegnazione", callback_data="assign_menu")],
            [InlineKeyboardButton("🏠 Menu Principale", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(invite_text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
    
    async def complete_task(self, query, task_id):
        """Completa un'attività"""
        user_id = query.from_user.id
        chat_id = query.message.chat_id
        
        points = db.complete_task(chat_id, task_id, user_id)
        
        if points > 0:
            task_name = db.data['tasks'][task_id]['name']
            stats = db.data['user_stats'][user_id]
            
            # Controlla se c'è un nuovo livello
            level_up_text = ""
            new_level = (stats['total_points'] // 100) + 1
            if new_level > stats['level']:
                level_up_text = f"\n🎉 *LEVEL UP!* Sei ora livello {new_level}!"
            
            # Controlla nuovi badge
            new_badges = []
            if stats['tasks_completed'] == 10:
                new_badges.append("🥉 Rookie")
            elif stats['tasks_completed'] == 50:
                new_badges.append("🥈 Expert")
            elif stats['tasks_completed'] == 100:
                new_badges.append("🥇 Master")
            
            if stats['streak'] == 7:
                new_badges.append("⚡ Week Warrior")
            elif stats['streak'] == 30:
                new_badges.append("👑 Month Champion")
            
            if stats['total_points'] == 500:
                new_badges.append("💎 Point Collector")
            
            badge_text = ""
            if new_badges:
                badge_text = f"\n🏅 *Nuovo Badge:* {' '.join(new_badges)}"
            
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

def main():
    """Avvia il bot"""
    TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    
    if not TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN non trovato!")
        return
    
    # Crea applicazione
    application = Application.builder().token(TOKEN).build()
    bot = FamilyTaskBot()
    
    # Aggiungi error handler globale
    async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Log di tutti gli errori"""
        logger.error("Exception while handling an update:", exc_info=context.error)
        print(f"DEBUG: Errore globale: {context.error}")
        
        # Se possibile, informa l'utente
        if update and hasattr(update, 'effective_chat') and update.effective_chat:
            try:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text="❌ Si è verificato un errore. Riprova con /start"
                )
            except:
                pass
    
    # Registra error handler
    application.add_error_handler(error_handler)
    
    # Aggiungi handler
    application.add_handler(CommandHandler("start", bot.start))
    application.add_handler(CommandHandler("tasks", bot.show_tasks))
    application.add_handler(CommandHandler("mytasks", bot.my_tasks))
    application.add_handler(CommandHandler("leaderboard", bot.leaderboard))
    application.add_handler(CommandHandler("stats", bot.stats))
    application.add_handler(CommandHandler("help", bot.help_command))
    application.add_handler(CallbackQueryHandler(bot.button_handler))
    
    # Handler per messaggi di testo (bottoni keyboard)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, bot.handle_message))
    
    # Avvia il bot
    logger.info("🏠 Family Task Bot avviato!")
    print("DEBUG: Bot in esecuzione...")
    application.run_polling()

if __name__ == '__main__':
    main()
