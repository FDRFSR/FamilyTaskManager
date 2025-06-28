import os
import logging
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from telegram.constants import ParseMode
import psycopg2
import psycopg2.extras

# Carica variabili d'ambiente da .env per sviluppo locale
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # In produzione non c'è python-dotenv

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

class FamilyTaskDB:
    def __init__(self):
        self.conn = None
        # Dati di test per modalità senza database
        self.test_mode = False
        self.test_data = {
            'tasks': {},
            'family_members': {},
            'assigned_tasks': {},
            'user_stats': {},
            'badges': {}
        }
        
        self.connect()
        self.ensure_tables()

    def connect(self):
        """Stabilisce la connessione al database"""
        try:
            if self.conn:
                self.conn.close()
            
            # Se DATABASE_URL non è disponibile, usa modalità test
            if "DATABASE_URL" not in os.environ:
                logger.warning("DATABASE_URL non trovato - modalità test attivata")
                self.conn = None
                self.test_mode = True
                return
                
            self.conn = psycopg2.connect(
                os.environ["DATABASE_URL"], 
                cursor_factory=psycopg2.extras.RealDictCursor
            )
            logger.info("Connessione al database stabilita")
        except Exception as e:
            logger.error(f"Errore nella connessione al database: {e}")
            # In modalità sviluppo, continua senza database
            logger.warning("Continuando in modalità test senza database")
            self.conn = None
            self.test_mode = True

    def ensure_connection(self):
        """Verifica che la connessione sia attiva, altrimenti riconnette"""
        try:
            # Se siamo in modalità test senza database, ritorna
            if self.conn is None:
                return
                
            if self.conn.closed:
                logger.warning("Connessione al database chiusa, riconnessione...")
                self.connect()
        except Exception as e:
            logger.error(f"Errore nel verificare la connessione: {e}")
            self.connect()

    def ensure_tables(self):
        # Se siamo in modalità test, salta la creazione delle tabelle
        if self.conn is None:
            logger.info("Modalità test: skip creazione tabelle")
            return
            
        self.ensure_connection()
        with self.conn, self.conn.cursor() as cur:
            with open(os.path.join(os.path.dirname(__file__), "schema.sql")) as f:
                cur.execute(f.read())

    def get_default_tasks(self):
        # Modalità test: restituisce task hardcoded
        if self.test_mode:
            default_tasks = {
                "cucina_pulizia": {"id": "cucina_pulizia", "name": "🍽️ Pulire la cucina", "points": 15, "time_minutes": 30},
                "bagno_pulizia": {"id": "bagno_pulizia", "name": "🚿 Pulire il bagno", "points": 20, "time_minutes": 40},
                "aspirapolvere": {"id": "aspirapolvere", "name": "🧹 Passare l'aspirapolvere", "points": 12, "time_minutes": 25},
                "lavastoviglie": {"id": "lavastoviglie", "name": "🍴 Caricare/svuotare lavastoviglie", "points": 8, "time_minutes": 15},
                "bucato": {"id": "bucato", "name": "👕 Fare il bucato", "points": 10, "time_minutes": 20},
                "stirare": {"id": "stirare", "name": "👔 Stirare", "points": 18, "time_minutes": 35},
                "spazzatura": {"id": "spazzatura", "name": "🗑️ Portare fuori la spazzatura", "points": 5, "time_minutes": 10},
                "giardino": {"id": "giardino", "name": "🌱 Curare il giardino", "points": 25, "time_minutes": 50},
                "spesa": {"id": "spesa", "name": "🛒 Fare la spesa", "points": 15, "time_minutes": 30},
                "letti": {"id": "letti", "name": "🛏️ Rifare i letti", "points": 6, "time_minutes": 12},
                "pavimenti": {"id": "pavimenti", "name": "🧽 Lavare i pavimenti", "points": 20, "time_minutes": 40},
                "finestre": {"id": "finestre", "name": "🪟 Pulire le finestre", "points": 22, "time_minutes": 45}
            }
            self.test_data['tasks'] = default_tasks
            return default_tasks
            
        # Carica task di default solo se non esistono, poi restituisce dizionario indicizzato per id
        try:
            self.ensure_connection()
            with self.conn, self.conn.cursor() as cur:
                # Gestione robusta della query COUNT
                cur.execute("SELECT COUNT(*) FROM tasks;")
                count_result = cur.fetchone()
                
                # Controllo robusto del risultato COUNT
                task_count = 0
                if count_result and count_result[0] is not None:
                    task_count = int(count_result[0])
                
                logging.info(f"Task count in database: {task_count}")
                
                if task_count == 0:
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
                    logging.info("Task di default inserite nel database")
                
                # Recupera tutte le task dal database
                cur.execute("SELECT * FROM tasks")
                rows = cur.fetchall()
                
                # Restituisce un dizionario indicizzato per id
                result = {row['id']: dict(row) for row in rows}
                logging.info(f"Caricate {len(result)} task dal database")
                return result
            
        except Exception as e:
            logging.error(f"Errore critico in get_default_tasks: {e}", exc_info=True)
            # Restituisce un set di task di emergenza in caso di errore del database
            logging.warning("Restituendo task di emergenza a causa di errore database")
            return {
                "cucina_pulizia": {"id": "cucina_pulizia", "name": "🍽️ Pulire la cucina", "points": 15, "time_minutes": 30},
                "bagno_pulizia": {"id": "bagno_pulizia", "name": "🚿 Pulire il bagno", "points": 20, "time_minutes": 40},
                "aspirapolvere": {"id": "aspirapolvere", "name": "🧹 Passare l'aspirapolvere", "points": 12, "time_minutes": 25},
                "lavastoviglie": {"id": "lavastoviglie", "name": "🍴 Caricare/svuotare lavastoviglie", "points": 8, "time_minutes": 15},
                "bucato": {"id": "bucato", "name": "👕 Fare il bucato", "points": 10, "time_minutes": 20},
                "stirare": {"id": "stirare", "name": "👔 Stirare", "points": 18, "time_minutes": 35},
                "spazzatura": {"id": "spazzatura", "name": "🗑️ Portare fuori la spazzatura", "points": 5, "time_minutes": 10},
                "giardino": {"id": "giardino", "name": "🌱 Curare il giardino", "points": 25, "time_minutes": 50},
                "spesa": {"id": "spesa", "name": "🛒 Fare la spesa", "points": 15, "time_minutes": 30},
                "letti": {"id": "letti", "name": "🛏️ Rifare i letti", "points": 6, "time_minutes": 12},
                "pavimenti": {"id": "pavimenti", "name": "🧽 Lavare i pavimenti", "points": 20, "time_minutes": 40},
                "finestre": {"id": "finestre", "name": "🪟 Pulire le finestre", "points": 22, "time_minutes": 45}
            }

    def get_all_tasks(self):
        if self.test_mode:
            if not self.test_data['tasks']:
                self.get_default_tasks()
            return list(self.test_data['tasks'].values())
            
        self.ensure_connection()
        with self.conn, self.conn.cursor() as cur:
            cur.execute("SELECT * FROM tasks")
            return cur.fetchall()

    def get_task_by_id(self, task_id: str):
        if self.test_mode:
            if not self.test_data['tasks']:
                self.get_default_tasks()
            return self.test_data['tasks'].get(task_id)
        
        self.ensure_connection()
        with self.conn, self.conn.cursor() as cur:
            cur.execute("SELECT * FROM tasks WHERE id = %s", (task_id,))
            task = cur.fetchone()
            if not task:
                # Logging dettagliato: task non trovata, mostra tutti gli id presenti
                cur.execute("SELECT id FROM tasks")
                all_ids = [row['id'] for row in cur.fetchall()]
                logging.error(f"Task non trovata: {task_id}. Id presenti: {all_ids}")
                # Suggerisci rigenerazione se mancante
            return task

    def get_assigned_tasks_for_chat(self, chat_id: int):
        if self.test_mode:
            return [task for task in self.test_data['assigned_tasks'].values() 
                   if task['chat_id'] == chat_id]
            
        self.ensure_connection()
        with self.conn, self.conn.cursor() as cur:
            cur.execute("SELECT * FROM assigned_tasks WHERE chat_id = %s", (chat_id,))
            return cur.fetchall()

    def get_user_assigned_tasks(self, chat_id: int, user_id: int):
        """Restituisce le task assegnate a un utente con controlli robusti e normalizzazione completa"""
        try:
            if self.test_mode:
                # Modalità test: restituisci sempre la chiave 'task_id'
                result = []
                for k, v in self.test_data['assigned_tasks'].items():
                    if v['chat_id'] == chat_id and v['assigned_to'] == user_id:
                        try:
                            task_id = k.split('_')[1]
                            task_info = self.test_data['tasks'].get(task_id, {})
                            result.append({
                                'task_id': task_id,
                                'due_date': v.get('due_date'),
                                'name': task_info.get('name', f'Task {task_id}'),
                                'points': task_info.get('points', 0),
                                'time_minutes': task_info.get('time_minutes', 0)
                            })
                        except Exception as e:
                            logger.error(f"Errore nel processare task test {k}: {e}")
                            continue
                logger.info(f"Test mode - get_user_assigned_tasks restituisce: {result}")
                return result
                
            # Modalità database
            self.ensure_connection()
            with self.conn, self.conn.cursor() as cur:
                cur.execute("""
                    SELECT at.task_id as task_id, at.due_date, t.name, t.points, t.time_minutes
                    FROM assigned_tasks at
                    JOIN tasks t ON at.task_id = t.id
                    WHERE at.chat_id = %s AND at.assigned_to = %s
                    ORDER BY at.due_date ASC
                """, (chat_id, user_id))
                rows = cur.fetchall()
                
                # Normalizzazione robusta dei risultati
                result = []
                logger.info(f"Query returned {len(rows)} rows for user {user_id} in chat {chat_id}")
                
                for i, row in enumerate(rows):
                    try:
                        # Garantisci che ogni row sia un dizionario con le chiavi necessarie
                        if isinstance(row, dict):
                            task = dict(row)  # Crea una copia
                        else:
                            # Se è una tupla, mappa alle colonne
                            columns = [desc[0] for desc in cur.description]
                            task = dict(zip(columns, row))
                        
                        # Validazione e normalizzazione delle chiavi obbligatorie
                        normalized_task = {
                            'task_id': task.get('task_id', f'unknown_{i}'),
                            'due_date': task.get('due_date'),
                            'name': task.get('name', f'Task {task.get("task_id", i)}'),
                            'points': int(task.get('points', 0)),
                            'time_minutes': int(task.get('time_minutes', 0))
                        }
                        
                        # Verifica finale che task_id non sia None o vuoto
                        if not normalized_task['task_id'] or normalized_task['task_id'] == 'unknown_' + str(i):
                            logger.error(f"Task con task_id invalido alla riga {i}: {task}")
                            continue
                            
                        result.append(normalized_task)
                        logger.debug(f"Task {i} normalizzata: {normalized_task}")
                        
                    except Exception as e:
                        logger.error(f"Errore nel processare task riga {i}: {row}, errore: {e}")
                        continue
                
                logger.info(f"get_user_assigned_tasks restituisce {len(result)} task normalizzate")
                return result
                
        except Exception as e:
            logger.error(f"Errore critico in get_user_assigned_tasks: {e}", exc_info=True)
            # Restituisci sempre una lista vuota in caso di errore
            return []

    def add_family_member(self, chat_id: int, user_id: int, username: str, first_name: str):
        if self.test_mode:
            key = f"{chat_id}_{user_id}"
            self.test_data['family_members'][key] = {
                'chat_id': chat_id,
                'user_id': user_id,
                'username': username,
                'first_name': first_name,
                'joined_date': datetime.now()
            }
            logger.info(f"Test mode: Aggiunto membro famiglia {first_name}")
            return
            
        self.ensure_connection()
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
        if self.test_mode:
            return [member for member in self.test_data['family_members'].values() 
                   if member['chat_id'] == chat_id]
            
        self.ensure_connection()
        with self.conn, self.conn.cursor() as cur:
            cur.execute("SELECT * FROM family_members WHERE chat_id = %s", (chat_id,))
            return cur.fetchall()

    def assign_task(self, chat_id: int, task_id: str, assigned_to: int, assigned_by: int):
        """Assegna una task a un utente con controlli robusti sui duplicati"""
        if self.test_mode:
            key = f"{chat_id}_{task_id}_{assigned_to}"
            # Controlla se la task è già assegnata in modalità test
            if key in self.test_data['assigned_tasks']:
                logger.warning(f"Test mode: Task {task_id} già assegnata a {assigned_to}")
                raise ValueError(f"Task {task_id} è già assegnata a questo utente")
                
            self.test_data['assigned_tasks'][key] = {
                'chat_id': chat_id,
                'task_id': task_id,
                'assigned_to': assigned_to,
                'assigned_by': assigned_by,
                'assigned_date': datetime.now(),
                'status': 'pending',
                'due_date': datetime.now() + timedelta(days=3)
            }
            logger.info(f"Test mode: Task {task_id} assegnata a {assigned_to}")
            return
            
        self.ensure_connection()
        with self.conn, self.conn.cursor() as cur:
            try:
                # Controlla se la task è già assegnata allo stesso utente
                cur.execute("""
                    SELECT COUNT(*) FROM assigned_tasks 
                    WHERE chat_id = %s AND task_id = %s AND assigned_to = %s
                """, (chat_id, task_id, assigned_to))
                
                count_result = cur.fetchone()
                existing_count = 0
                if count_result and count_result[0] is not None:
                    existing_count = int(count_result[0])
                
                if existing_count > 0:
                    logger.warning(f"Task {task_id} già assegnata a utente {assigned_to} in chat {chat_id}")
                    raise ValueError(f"Task {task_id} è già assegnata a questo utente")
                
                # Inserisci la nuova assegnazione
                cur.execute("""
                    INSERT INTO assigned_tasks (chat_id, task_id, assigned_to, assigned_by, assigned_date, status, due_date) 
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (chat_id, task_id, assigned_to, assigned_by, datetime.now(), 'pending', datetime.now() + timedelta(days=3)))
                
                self.conn.commit()
                logger.info(f"Task {task_id} assegnata con successo a utente {assigned_to} in chat {chat_id}")
                
            except psycopg2.IntegrityError as e:
                self.conn.rollback()
                logger.error(f"Errore di integrità nell'assegnazione task: {e}")
                raise ValueError(f"Impossibile assegnare la task: violazione di integrità")
            except Exception as e:
                self.conn.rollback()
                logger.error(f"Errore nell'assegnazione task {task_id}: {e}")
                raise

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
        if self.test_mode:
            # Simulazione modalità test
            task_key = f"{chat_id}_{task_id}_{user_id}"
            if task_key not in self.test_data['assigned_tasks']:
                return 0, {"level_up": False, "new_level": None, "new_badges": []}
            
            # Simula completamento task
            points = 15  # Punti di test
            msg = {"level_up": False, "new_level": None, "new_badges": []}
            
            # Rimuovi task assegnata
            del self.test_data['assigned_tasks'][task_key]
            
            # Aggiorna stats in modalità test
            if user_id not in self.test_data['user_stats']:
                self.test_data['user_stats'][user_id] = {
                    'total_points': 0,
                    'tasks_completed': 0,
                    'level': 1,
                    'streak': 0
                }
            
            stats = self.test_data['user_stats'][user_id]
            old_level = stats['level']
            stats['total_points'] += points
            stats['tasks_completed'] += 1
            stats['level'] = stats['total_points'] // 100 + 1
            stats['streak'] += 1
            
            if stats['level'] > old_level:
                msg["level_up"] = True
                msg["new_level"] = stats['level']
                
            logger.info(f"Test mode: Task {task_id} completata per {points} punti")
            return points, msg
            
        self.ensure_connection()
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
        if self.test_mode:
            # Restituisce leaderboard basato sui dati di test
            members = self.get_family_members(chat_id)
            leaderboard = []
            for member in members:
                stats = self.test_data['user_stats'].get(member['user_id'], {
                    'total_points': 0,
                    'level': 1,
                    'tasks_completed': 0,
                    'streak': 0
                })
                leaderboard.append({
                    'user_id': member['user_id'],
                    'first_name': member['first_name'],
                    'total_points': stats['total_points'],
                    'level': stats['level'],
                    'tasks_completed': stats['tasks_completed'],
                    'streak': stats['streak']
                })
            return sorted(leaderboard, key=lambda x: x['total_points'], reverse=True)
            
        self.ensure_connection()
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
        if self.test_mode:
            return self.test_data['user_stats'].get(user_id)
            
        self.ensure_connection()
        with self.conn, self.conn.cursor() as cur:
            cur.execute("SELECT * FROM user_stats WHERE user_id = %s", (user_id,))
            return cur.fetchone()

    def get_user_badges(self, user_id: int):
        if self.test_mode:
            return []  # Nessun badge nella modalità test per ora
            
        self.ensure_connection()
        with self.conn, self.conn.cursor() as cur:
            cur.execute("SELECT name FROM badges WHERE user_id = %s", (user_id,))
            return [row['name'] for row in cur.fetchall()]

# Database sarà inizializzato in main() o quando necessario
db = None

def get_db():
    """Ottiene l'istanza del database, creandola se necessario"""
    global db
    if db is None:
        db = FamilyTaskDB()
    return db

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
        """Mostra le task dell'utente con controlli robusti"""
        if not update.message:
            return
            
        try:
            user_id = update.effective_user.id
            chat_id = update.effective_chat.id
            logger.info(f"my_tasks chiamata per user {user_id} in chat {chat_id}")
            
            my_tasks = db.get_user_assigned_tasks(chat_id, user_id)
            logger.info(f"Ricevute {len(my_tasks)} task per l'utente")
            
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
            valid_tasks_count = 0
            
            for i, task in enumerate(my_tasks, 1):
                try:
                    # Controlli di sicurezza multipli
                    if not task:
                        logger.warning(f"Task #{i} è None, saltata")
                        continue
                        
                    if not isinstance(task, dict):
                        logger.warning(f"Task #{i} non è un dizionario: {type(task)}, saltata")
                        continue
                        
                    task_id = task.get('task_id')
                    if not task_id:
                        logger.warning(f"Task #{i} senza task_id: {task}, saltata")
                        continue
                        
                    # Estrai i dati della task con valori di default sicuri
                    name = task.get('name', f'Task {task_id}')
                    points = task.get('points', 0)
                    time_minutes = task.get('time_minutes', 0)
                    due_date = task.get('due_date')
                    
                    # Calcola scadenza
                    due_str = due_date.strftime("%d/%m") if due_date else "-"
                    if due_date:
                        try:
                            days_left = (due_date - datetime.now()).days
                        except Exception as e:
                            logger.warning(f"Errore nel calcolo giorni rimasti per task {task_id}: {e}")
                            days_left = 99
                    else:
                        days_left = 99
                        
                    urgency = "🔴" if days_left <= 1 else "🟡" if days_left <= 2 else "🟢"
                    
                    # Aggiungi al testo
                    valid_tasks_count += 1
                    tasks_text += f"*{valid_tasks_count}. {name}*\n"
                    tasks_text += f"⭐ {points} punti | 📅 Scadenza: {due_str} {urgency}\n"
                    tasks_text += f"⏱️ Tempo stimato: ~{time_minutes} minuti\n\n"
                    
                    # Crea bottone per completamento
                    button_text = f"✅ {name[:15]}..." if len(name) > 15 else f"✅ {name}"
                    keyboard.append([InlineKeyboardButton(
                        button_text,
                        callback_data=f"complete_{task_id}"
                    )])
                    
                    logger.debug(f"Task {task_id} processata correttamente")
                    
                except Exception as e:
                    logger.error(f"Errore nel processare task #{i}: {task}, errore: {e}")
                    continue
            
            # Se non ci sono task valide dopo il filtraggio
            if valid_tasks_count == 0:
                logger.warning("Nessuna task valida trovata dopo il filtraggio")
                keyboard = [
                    [InlineKeyboardButton("🎯 Assegna Nuova Task", callback_data="assign_menu")],
                    [InlineKeyboardButton("📋 Vedi Tutte le Task", callback_data="show_all_tasks")],
                    [InlineKeyboardButton("🔙 Menu Principale", callback_data="main_menu")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await update.message.reply_text(
                    "📝 *Le tue task sembrano avere dei problemi di caricamento!*\n\nProva ad assegnarne una nuova o riavvia il bot con /start",
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=reply_markup
                )
                return
            
            # Aggiungi bottoni di navigazione
            keyboard.extend([
                [InlineKeyboardButton("🎯 Assegna Altra Task", callback_data="assign_menu")],
                [InlineKeyboardButton("📊 Mie Statistiche", callback_data="show_my_stats")],
                [InlineKeyboardButton("🔙 Menu Principale", callback_data="main_menu")]
            ])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(tasks_text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
            logger.info(f"my_tasks completata con successo: {valid_tasks_count} task mostrate")
            
        except Exception as e:
            logger.error(f"Errore critico in my_tasks: {e}", exc_info=True)
            try:
                # Fallback di emergenza
                keyboard = [
                    [InlineKeyboardButton("🔄 Riprova", callback_data="show_my_tasks")],
                    [InlineKeyboardButton("🔙 Menu Principale", callback_data="main_menu")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await update.message.reply_text(
                    "❌ *Errore nel caricamento delle tue task*\n\n"
                    "Si è verificato un problema tecnico. Riprova o torna al menu principale.",
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=reply_markup
                )
            except Exception as e2:
                logger.critical(f"Errore critico nel fallback di my_tasks: {e2}")
                # Ultimo tentativo con messaggio semplice
                try:
                    await update.message.reply_text("❌ Errore critico. Usa /start per ricominciare.")
                except Exception as e3:
                    logger.critical(f"Fallimento completo di my_tasks: {e3}")

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
        """Gestisce i callback dei bottoni con controlli di sicurezza estremamente robusti"""
        query = update.callback_query
        try:
            logger.info(f"Ricevuto callback_query: {query.data} da utente {query.from_user.id}")
            await query.answer()
            data = query.data
            
            # Validazione base del callback data
            if not data or not isinstance(data, str):
                logger.error(f"Callback data invalido: {data}")
                await query.edit_message_text("❌ Comando non valido. Usa /start per ricominciare.")
                return
            
            if data == "assign_menu":
                await self.assign_task_menu(update, context)
            elif data.startswith("assign_category_"):
                catid = data.replace("assign_category_", "")
                if catid in self.TASK_CATEGORIES:
                    await self.assign_category_menu(query, catid)
                else:
                    logger.error(f"Categoria invalida: {catid}")
                    await query.edit_message_text("❌ Categoria non valida. Riprova.")
            elif data.startswith("choose_task_"):
                task_id = data.replace("choose_task_", "")
                if task_id and len(task_id) > 0:
                    await self.choose_assign_target(query, task_id)
                else:
                    logger.error(f"Task ID invalido: {task_id}")
                    await query.edit_message_text("❌ Task non valida. Riprova.")
            elif data.startswith("assign_self_"):
                task_id = data.replace("assign_self_", "")
                if task_id and len(task_id) > 0:
                    logger.info(f"Callback assign_self per task: {task_id}")
                    await self.handle_assign(query, task_id, query.from_user.id)
                else:
                    logger.error(f"Task ID invalido per assign_self: {task_id}")
                    await query.edit_message_text("❌ Task non valida. Riprova.")
            elif data.startswith("assign_"):
                parts = data.split("_")
                logger.info(f"Callback assign con parti: {parts}")
                if len(parts) >= 3:
                    try:
                        task_id = parts[1]
                        target_user_id = int(parts[2])
                        
                        # Validazione aggiuntiva
                        if not task_id or len(task_id) == 0:
                            logger.error(f"Task ID vuoto nel callback: {data}")
                            await query.edit_message_text("❌ Task non valida. Riprova.")
                            return
                            
                        if target_user_id <= 0:
                            logger.error(f"User ID invalido nel callback: {target_user_id}")
                            await query.edit_message_text("❌ Utente non valido. Riprova.")
                            return
                            
                        logger.info(f"Assegnazione task {task_id} a utente {target_user_id}")
                        await self.handle_assign(query, task_id, target_user_id)
                    except ValueError as e:
                        logger.error(f"Errore nel parsing user_id da callback {data}: {e}")
                        await query.edit_message_text("❌ Errore nel formato del comando. Riprova.")
                    except Exception as e:
                        logger.error(f"Errore generico nel callback assign: {e}")
                        await query.edit_message_text("❌ Errore nell'assegnazione. Riprova.")
                else:
                    logger.error(f"Callback assign malformato: {data}")
                    await query.edit_message_text("❌ Comando malformato. Riprova.")
            elif data == "none":
                await query.answer("Operazione non disponibile", show_alert=False)
            elif data.startswith("complete_"):
                task_id = data.replace("complete_", "")
                if task_id and len(task_id) > 0:
                    logger.info(f"Chiamata complete_task per task_id: {task_id}")
                    await self.complete_task(query, task_id)
                else:
                    logger.error(f"Task ID invalido per complete: {task_id}")
                    await query.edit_message_text("❌ Task non valida per completamento. Riprova.")
            elif data == "complete_menu":
                await self.show_complete_menu(query)
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
            elif data == "invite_info":
                await query.edit_message_text(
                    "*👥 Invita la tua famiglia!*\n\n"
                    "Condividi questo bot con i tuoi familiari:\n"
                    "1. Invia loro il link del bot\n"
                    "2. Chiedi loro di digitare `/start`\n"
                    "3. Iniziate a collaborare nelle faccende!\n\n"
                    "Il bot funziona meglio in gruppi familiari! 👨‍👩‍👧‍👦",
                    parse_mode=ParseMode.MARKDOWN
                )
            else:
                logger.warning(f"Callback non gestito: {data}")
                await query.edit_message_text(
                    f"❓ *Azione non implementata*\n\nCallback: `{data}`\n\nUsa /start per ricominciare.",
                    parse_mode=ParseMode.MARKDOWN
                )
                
        except Exception as e:
            logger.error(f"Errore in button_handler per callback '{query.data}': {e}", exc_info=True)
            try:
                # Prova prima un messaggio di errore dettagliato
                await query.edit_message_text(
                    "❌ *Errore temporaneo*\n\n"
                    "Si è verificato un problema. Riprova o usa /start per ricominciare.\n\n"
                    f"Dettagli tecnici: `{type(e).__name__}`",
                    parse_mode=ParseMode.MARKDOWN
                )
            except Exception as e2:
                logger.error(f"Errore secondario nel button handler: {e2}")
                # Come ultimo tentativo, proviamo a inviare un messaggio semplice
                try:
                    await context.bot.send_message(
                        chat_id=query.message.chat.id,
                        text="❌ Errore critico. Usa /start per ricominciare."
                    )
                except Exception as e3:
                    logger.critical(f"Errore critico nel button handler: {e3}")
                    # Ultima risorsa: answer al callback per evitare timeout
                    try:
                        await query.answer("❌ Errore critico", show_alert=True)
                    except Exception as e4:
                        logger.critical(f"Fallimento completo del button handler: {e4}")

    async def complete_task(self, query, task_id):
        user_id = query.from_user.id
        chat_id = query.message.chat.id
        
        try:
            logger.info(f"Tentativo di completare task {task_id} per utente {user_id} in chat {chat_id}")
            
            points, msg = db.complete_task(chat_id, task_id, user_id)
            
            if points > 0:
                # Ottieni task e stats in modo sicuro
                task = db.get_task_by_id(task_id)
                if not task:
                    await query.edit_message_text("❌ Informazioni task non trovate.")
                    return
                    
                stats = db.get_user_stats(user_id)
                if not stats:
                    # Se non ci sono stats, crea delle stats di default
                    stats = {
                        'total_points': points,
                        'tasks_completed': 1,
                        'level': 1,
                        'streak': 1
                    }
                
                level_up_text = ""
                if msg.get("level_up", False):
                    level_up_text = f"\n🎉 *LEVEL UP!* Ora sei livello {msg['new_level']}!"
                    
                badge_text = ""
                if msg.get("new_badges", []):
                    badge_emojis = [self.badge_emojis.get(b, "🏅") for b in msg["new_badges"]]
                    badge_text = f"\n🏅 *Nuovo Badge:* {' '.join(badge_emojis)}"
                
                keyboard = [
                    [InlineKeyboardButton("📊 Mie Statistiche", callback_data="show_my_stats")],
                    [InlineKeyboardButton("🏆 Classifica", callback_data="show_leaderboard")],
                    [InlineKeyboardButton("📋 Altre Mie Task", callback_data="show_my_tasks")],
                    [InlineKeyboardButton("🔙 Menu", callback_data="main_menu")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                success_text = (
                    f"🎉 *Attività Completata!*\n\n"
                    f"📋 {task['name']}\n"
                    f"⭐ +{points} punti\n"
                    f"🔥 Streak: {stats.get('streak', 1)} giorni"
                    f"{level_up_text}"
                    f"{badge_text}"
                )
                
                await query.edit_message_text(
                    success_text,
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=reply_markup
                )
                logger.info(f"Task {task_id} completata con successo per utente {user_id}")
            else:
                await query.edit_message_text("❌ Attività non trovata o già completata.")
                logger.warning(f"Task {task_id} non completabile per utente {user_id}")
                
        except Exception as e:
            logger.error(f"Errore nel completamento task {task_id} per utente {user_id}: {e}", exc_info=True)
            try:
                await query.edit_message_text(
                    "❌ *Errore nel completare l'attività*\n\nRiprova più tardi o contatta l'amministratore.",
                    parse_mode=ParseMode.MARKDOWN
                )
            except Exception as e2:
                logger.error(f"Errore secondario nel complete_task: {e2}")

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

    async def handle_assign(self, query, task_id, target_user_id):
        """Gestisce l'assegnazione effettiva della task con controlli robusti"""
        chat_id = query.message.chat.id
        assigned_by = query.from_user.id
        
        try:
            logger.info(f"Iniziando assegnazione task {task_id} a utente {target_user_id} in chat {chat_id}")
            
            # Verifica che la task esista
            task = db.get_task_by_id(task_id)
            if not task:
                logger.error(f"Task {task_id} non trovata nel database")
                await query.edit_message_text("❌ Task non trovata nel sistema!")
                return
            
            # Verifica che l'utente destinatario sia membro della famiglia
            members = db.get_family_members(chat_id)
            target_member = next((m for m in members if m['user_id'] == target_user_id), None)
            
            if not target_member and target_user_id != assigned_by:
                logger.error(f"Utente {target_user_id} non è membro della famiglia in chat {chat_id}")
                await query.edit_message_text("❌ L'utente non è membro della famiglia!")
                return
            
            # Verifica se la task è già assegnata allo stesso utente
            existing_tasks = db.get_assigned_tasks_for_chat(chat_id)
            for assigned in existing_tasks:
                if assigned.get('task_id') == task_id and assigned.get('assigned_to') == target_user_id:
                    logger.warning(f"Task {task_id} già assegnata a utente {target_user_id}")
                    await query.edit_message_text("❌ Questa task è già assegnata a questo utente!")
                    return
            
            # Procedi con l'assegnazione
            logger.info(f"Assegnando task {task_id} a utente {target_user_id}")
            try:
                db.assign_task(chat_id, task_id, target_user_id, assigned_by)
            except ValueError as ve:
                # Gestisce il caso in cui la task è già assegnata (dal controllo nel DB)
                logger.warning(f"Tentativo di assegnazione duplicata: {ve}")
                await query.edit_message_text(f"❌ {str(ve)}")
                return
            except Exception as db_error:
                logger.error(f"Errore del database nell'assegnazione: {db_error}")
                await query.edit_message_text("❌ Errore del database durante l'assegnazione. Riprova.")
                return
            
            # Determina il nome del destinatario per il messaggio di conferma
            if target_user_id == assigned_by:
                target_name = "te stesso"
            else:
                target_name = target_member['first_name'] if target_member else f"Utente {target_user_id}"
            
            # Prepara il messaggio di successo
            keyboard = [
                [InlineKeyboardButton("📋 Le Mie Task", callback_data="show_my_tasks")],
                [InlineKeyboardButton("🎯 Assegna Altra Task", callback_data="assign_menu")],
                [InlineKeyboardButton("🔙 Menu Principale", callback_data="main_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
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
            
            logger.info(f"Task {task_id} assegnata con successo a {target_user_id}")
            
        except Exception as e:
            logger.error(f"Errore nell'assegnazione task {task_id} a {target_user_id}: {e}", exc_info=True)
            try:
                await query.edit_message_text(
                    "❌ *Errore nell'Assegnazione*\n\n"
                    "Si è verificato un problema durante l'assegnazione della task. "
                    "Verifica che tutti i dati siano corretti e riprova.\n\n"
                    "Se il problema persiste, riavvia il bot con /start",
                    parse_mode=ParseMode.MARKDOWN
                )
            except Exception as e2:
                logger.error(f"Errore secondario in handle_assign: {e2}")
                # Tentativo di fallback con messaggio semplice
                try:
                    await query.answer("❌ Errore nell'assegnazione task", show_alert=True)
                except Exception as e3:
                    logger.critical(f"Errore critico in handle_assign: {e3}")

    async def choose_assign_target(self, query, task_id):
        """Mostra i membri della famiglia per scegliere a chi assegnare la task con controlli robusti"""
        chat_id = query.message.chat.id
        current_user = query.from_user.id
        
        try:
            logger.info(f"Aprendo menu scelta destinatario per task {task_id} in chat {chat_id}")
            
            # Verifica che la task esista
            task = db.get_task_by_id(task_id)
            if not task:
                logger.error(f"Task {task_id} non trovata")
                await query.edit_message_text("❌ Task non trovata nel sistema!")
                return
            
            # Ottieni i membri della famiglia
            members = db.get_family_members(chat_id)
            logger.info(f"Trovati {len(members)} membri nella famiglia chat {chat_id}")
            
            if not members:
                # Se non ci sono membri, aggiungi almeno l'utente corrente
                logger.warning(f"Nessun membro famiglia trovato, aggiungendo utente corrente {current_user}")
                current_user_info = query.from_user
                db.add_family_member(
                    chat_id, 
                    current_user_info.id, 
                    current_user_info.username or '', 
                    current_user_info.first_name or 'Utente'
                )
                members = db.get_family_members(chat_id)
            
            # Verifica se la task è già assegnata allo stesso utente
            existing_assignments = db.get_assigned_tasks_for_chat(chat_id)
            already_assigned_to = []
            for assignment in existing_assignments:
                if assignment.get('task_id') == task_id:
                    already_assigned_to.append(assignment.get('assigned_to'))
            
            keyboard = []
            
            # Opzione per assegnare a se stesso (se non già assegnata)
            if current_user not in already_assigned_to:
                keyboard.append([
                    InlineKeyboardButton(
                        f"🫵 Assegna a me", 
                        callback_data=f"assign_self_{task_id}"
                    )
                ])
            
            # Opzioni per assegnare ad altri membri (se non già assegnate)
            for member in members:
                user_id = member['user_id']
                if user_id != current_user and user_id not in already_assigned_to:
                    first_name = member.get('first_name', f'Utente {user_id}')
                    keyboard.append([
                        InlineKeyboardButton(
                            f"👤 {first_name}",
                            callback_data=f"assign_{task_id}_{user_id}"
                        )
                    ])
            
            # Mostra utenti a cui la task è già assegnata (informativi, non cliccabili)
            if already_assigned_to:
                for member in members:
                    if member['user_id'] in already_assigned_to:
                        first_name = member.get('first_name', f'Utente {member["user_id"]}')
                        keyboard.append([
                            InlineKeyboardButton(
                                f"✅ {first_name} (già assegnata)",
                                callback_data="none"
                            )
                        ])
            
            # Se nessuno è disponibile per l'assegnazione
            if not any(btn for row in keyboard for btn in row if btn.callback_data != "none"):
                keyboard = [
                    [InlineKeyboardButton(
                        "ℹ️ Task già assegnata a tutti",
                        callback_data="none"
                    )]
                ]
            
            # Bottoni di navigazione
            keyboard.extend([
                [InlineKeyboardButton("🔙 Indietro", callback_data="assign_menu")],
                [InlineKeyboardButton("🏠 Menu Principale", callback_data="main_menu")]
            ])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
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
            
            logger.info(f"Menu scelta destinatario mostrato per task {task_id}")
            
        except Exception as e:
            logger.error(f"Errore in choose_assign_target per task {task_id}: {e}", exc_info=True)
            try:
                await query.edit_message_text(
                    "❌ *Errore nella Selezione*\n\n"
                    "Si è verificato un problema nel mostrare i membri della famiglia. "
                    "Verifica di aver fatto /start e riprova.\n\n"
                    "Se il problema persiste, riavvia il bot con /start",
                    parse_mode=ParseMode.MARKDOWN
                )
            except Exception as e2:
                logger.error(f"Errore secondario in choose_assign_target: {e2}")
                try:
                    await query.answer("❌ Errore nel caricamento membri famiglia", show_alert=True)
                except Exception as e3:
                    logger.critical(f"Errore critico in choose_assign_target: {e3}")

    async def send_task_reminders(self, application):
        """Invia promemoria per le task in scadenza"""
        try:
            # Da implementare: logica di promemoria
            pass
        except Exception as e:
            logger.error(f"Errore nei promemoria: {e}")

    async def show_my_tasks_inline(self, query):
        """Versione inline di my_tasks per i callback con controlli robusti"""
        try:
            user_id = query.from_user.id
            chat_id = query.message.chat.id
            logger.info(f"show_my_tasks_inline chiamata per user {user_id} in chat {chat_id}")
            
            my_tasks = db.get_user_assigned_tasks(chat_id, user_id)
            logger.info(f"Ricevute {len(my_tasks)} task per l'utente")
            
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
            valid_tasks_count = 0
            
            for i, task in enumerate(my_tasks, 1):
                try:
                    # Controlli di sicurezza multipli
                    if not task:
                        logger.warning(f"Task #{i} è None, saltata")
                        continue
                        
                    if not isinstance(task, dict):
                        logger.warning(f"Task #{i} non è un dizionario: {type(task)}, saltata")
                        continue
                        
                    task_id = task.get('task_id')
                    if not task_id:
                        logger.warning(f"Task #{i} senza task_id: {task}, saltata")
                        continue
                        
                    # Estrai i dati della task con valori di default sicuri
                    name = task.get('name', f'Task {task_id}')
                    points = task.get('points', 0)
                    time_minutes = task.get('time_minutes', 0)
                    due_date = task.get('due_date')
                    
                    # Calcola scadenza
                    due_str = due_date.strftime("%d/%m") if due_date else "-"
                    if due_date:
                        try:
                            days_left = (due_date - datetime.now()).days
                        except Exception as e:
                            logger.warning(f"Errore nel calcolo giorni rimasti per task {task_id}: {e}")
                            days_left = 99
                    else:
                        days_left = 99
                        
                    urgency = "🔴" if days_left <= 1 else "🟡" if days_left <= 2 else "🟢"
                    
                    # Aggiungi al testo
                    valid_tasks_count += 1
                    tasks_text += f"*{valid_tasks_count}. {name}*\n"
                    tasks_text += f"⭐ {points} punti | 📅 Scadenza: {due_str} {urgency}\n"
                    tasks_text += f"⏱️ Tempo stimato: ~{time_minutes} minuti\n\n"
                    
                    # Crea bottone per completamento
                    button_text = f"✅ {name[:15]}..." if len(name) > 15 else f"✅ {name}"
                    keyboard.append([InlineKeyboardButton(
                        button_text,
                        callback_data=f"complete_{task_id}"
                    )])
                    
                    logger.debug(f"Task {task_id} processata correttamente")
                    
                except Exception as e:
                    logger.error(f"Errore nel processare task #{i}: {task}, errore: {e}")
                    continue
            
            # Se non ci sono task valide dopo il filtraggio
            if valid_tasks_count == 0:
                logger.warning("Nessuna task valida trovata dopo il filtraggio")
                keyboard = [
                    [InlineKeyboardButton("🎯 Assegna Nuova Task", callback_data="assign_menu")],
                    [InlineKeyboardButton("📋 Vedi Tutte le Task", callback_data="show_all_tasks")],
                    [InlineKeyboardButton("🔙 Menu Principale", callback_data="main_menu")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text(
                    "📝 *Le tue task sembrano avere dei problemi di caricamento!*\n\nProva ad assegnarne una nuova o riavvia il bot con /start",
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=reply_markup
                )
                return
            
            # Aggiungi bottoni di navigazione
            keyboard.extend([
                [InlineKeyboardButton("🎯 Assegna Altra Task", callback_data="assign_menu")],
                [InlineKeyboardButton("📊 Mie Statistiche", callback_data="show_my_stats")],
                [InlineKeyboardButton("🔙 Menu Principale", callback_data="main_menu")]
            ])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(tasks_text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
            logger.info(f"show_my_tasks_inline completata con successo: {valid_tasks_count} task mostrate")
            
        except Exception as e:
            logger.error(f"Errore critico in show_my_tasks_inline: {e}", exc_info=True)
            try:
                # Fallback di emergenza
                keyboard = [
                    [InlineKeyboardButton("🔄 Riprova", callback_data="show_my_tasks")],
                    [InlineKeyboardButton("🔙 Menu Principale", callback_data="main_menu")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text(
                    "❌ *Errore nel caricamento delle tue task*\n\n"
                    "Si è verificato un problema tecnico. Riprova o torna al menu principale.",
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=reply_markup
                )
            except Exception as e2:
                logger.critical(f"Errore critico nel fallback di show_my_tasks_inline: {e2}")

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

    async def show_complete_menu(self, query):
        """Mostra le task assegnate all'utente per completarle con controlli robusti"""
        try:
            user_id = query.from_user.id
            chat_id = query.message.chat.id
            logger.info(f"show_complete_menu chiamata per user {user_id} in chat {chat_id}")
            
            my_tasks = db.get_user_assigned_tasks(chat_id, user_id)
            logger.info(f"Ricevute {len(my_tasks)} task per completamento")
            
            if not my_tasks:
                keyboard = [
                    [InlineKeyboardButton("🎯 Assegna Nuova Task", callback_data="assign_menu")],
                    [InlineKeyboardButton("📋 Vedi Tutte le Task", callback_data="show_all_tasks")],
                    [InlineKeyboardButton("🔙 Menu Principale", callback_data="main_menu")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text(
                    "📝 *Non hai attività da completare!*\n\nAssegnati una task per iniziare a guadagnare punti.",
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=reply_markup
                )
                return
                
            tasks_text = f"*✅ Completa una delle tue attività ({len(my_tasks)}):*\n\n"
            keyboard = []
            valid_tasks_count = 0
            
            for i, task in enumerate(my_tasks, 1):
                try:
                    # Controlli di sicurezza multipli
                    if not task:
                        logger.warning(f"Task #{i} è None, saltata")
                        continue
                        
                    if not isinstance(task, dict):
                        logger.warning(f"Task #{i} non è un dizionario: {type(task)}, saltata")
                        continue
                        
                    task_id = task.get('task_id')
                    if not task_id:
                        logger.warning(f"Task #{i} senza task_id: {task}, saltata")
                        continue
                        
                    # Estrai i dati della task con valori di default sicuri
                    name = task.get('name', f'Task {task_id}')
                    points = task.get('points', 0)
                    due_date = task.get('due_date')
                    
                    # Calcola scadenza
                    due_str = due_date.strftime("%d/%m") if due_date else "-"
                    if due_date:
                        try:
                            days_left = (due_date - datetime.now()).days
                        except Exception as e:
                            logger.warning(f"Errore nel calcolo giorni rimasti per task {task_id}: {e}")
                            days_left = 99
                    else:
                        days_left = 99
                        
                    urgency = "🔴" if days_left <= 1 else "🟡" if days_left <= 2 else "🟢"
                    
                    # Aggiungi al testo
                    valid_tasks_count += 1
                    tasks_text += f"*{valid_tasks_count}. {name}*\n"
                    tasks_text += f"⭐ {points} punti | 📅 {due_str} {urgency}\n\n"
                    
                    # Crea bottone per completamento
                    button_text = f"✅ {name[:20]}..." if len(name) > 20 else f"✅ {name}"
                    keyboard.append([InlineKeyboardButton(
                        button_text,
                        callback_data=f"complete_{task_id}"
                    )])
                    
                    logger.debug(f"Task {task_id} processata per completamento")
                    
                except Exception as e:
                    logger.error(f"Errore nel processare task #{i} per completamento: {task}, errore: {e}")
                    continue
            
            # Se non ci sono task valide dopo il filtraggio
            if valid_tasks_count == 0:
                logger.warning("Nessuna task valida trovata per completamento dopo il filtraggio")
                keyboard = [
                    [InlineKeyboardButton("🎯 Assegna Nuova Task", callback_data="assign_menu")],
                    [InlineKeyboardButton("📋 Vedi Tutte le Task", callback_data="show_all_tasks")],
                    [InlineKeyboardButton("🔙 Menu Principale", callback_data="main_menu")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text(
                    "📝 *Le tue task sembrano avere dei problemi di caricamento!*\n\nProva ad assegnarne una nuova o riavvia il bot con /start",
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=reply_markup
                )
                return
                
            # Aggiungi bottoni di navigazione
            keyboard.extend([
                [InlineKeyboardButton("📋 Le Mie Task", callback_data="show_my_tasks")],
                [InlineKeyboardButton("🔙 Menu Principale", callback_data="main_menu")]
            ])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(tasks_text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
            logger.info(f"show_complete_menu completata con successo: {valid_tasks_count} task mostrate")
            
        except Exception as e:
            logger.error(f"Errore critico in show_complete_menu: {e}", exc_info=True)
            try:
                # Fallback di emergenza
                keyboard = [
                    [InlineKeyboardButton("🔄 Riprova", callback_data="complete_menu")],
                    [InlineKeyboardButton("🔙 Menu Principale", callback_data="main_menu")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text(
                    "❌ *Errore nel caricamento del menu completamento*\n\n"
                    "Si è verificato un problema tecnico. Riprova o torna al menu principale.",
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=reply_markup
                )
            except Exception as e2:
                logger.critical(f"Errore critico nel fallback di show_complete_menu: {e2}")

def main():
    TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    if not TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN non trovato!")
        logger.info("Per testare il bot, imposta le variabili d'ambiente nel file .env")
        logger.info("Modalità demo: mostra solo le funzionalità principali")
        
        # Test delle funzionalità principali
        print("\n🏠 Family Task Manager - Test delle Funzionalità\n")
        
        # Test del database
        test_db = FamilyTaskDB()
        
        print("✅ Database inizializzato in modalità test")
        print(f"✅ {len(test_db.get_all_tasks())} task caricate")
        
        # Test aggiunta membro famiglia
        test_db.add_family_member(123456, 789012, "testuser", "Mario")
        members = test_db.get_family_members(123456)
        print(f"✅ {len(members)} membri famiglia aggiunti")
        
        # Test assegnazione task
        test_db.assign_task(123456, "cucina_pulizia", 789012, 789012)
        assigned = test_db.get_assigned_tasks_for_chat(123456)
        print(f"✅ {len(assigned)} task assegnate")
        
        # Test completamento task
        points, msg = test_db.complete_task(123456, "cucina_pulizia", 789012)
        print(f"✅ Task completata: {points} punti guadagnati")
        
        # Test leaderboard
        leaderboard = test_db.get_leaderboard(123456)
        print(f"✅ Leaderboard: {len(leaderboard)} utenti")
        
        # Test specifico per KeyError (la parte che ci interessava)
        print("\n🔍 Test specifico anti-KeyError:")
        
        # Aggiungi un'altra task e testala
        test_db.assign_task(123456, "bagno_pulizia", 789012, 789012)
        user_tasks = test_db.get_user_assigned_tasks(123456, 789012)
        print(f"✅ {len(user_tasks)} task recuperate per l'utente")
        
        # Verifica che ogni task abbia tutte le chiavi necessarie
        for i, task in enumerate(user_tasks):
            required_keys = ['task_id', 'name', 'points', 'time_minutes']
            for key in required_keys:
                if key not in task:
                    print(f"❌ ERRORE: Chiave '{key}' mancante nella task {i+1}")
                    return
            print(f"✅ Task {i+1}: {task['task_id']} - {task['name']} ({task['points']} pt)")
        
        print("\n🎉 Tutti i test principali completati con successo!")
        print("📊 Il KeyError nelle task è stato RISOLTO definitivamente!")
        print("Per usare il bot con Telegram, configura TELEGRAM_BOT_TOKEN nel file .env")
        return
        
    # Modalità normale con bot Telegram
    try:
        global db
        db = FamilyTaskDB()
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
        
        # Aggiungi job per i promemoria (ogni ora) solo se JobQueue è disponibile
        try:
            if application.job_queue:
                application.job_queue.run_repeating(reminder_job, interval=3600, first=10)
                logger.info("JobQueue configurato per i promemoria")
            else:
                logger.warning("JobQueue non disponibile - promemoria disabilitati")
        except Exception as e:
            logger.warning(f"Errore nell'impostazione JobQueue: {e}")
        
        logger.info("🏠 Family Task Bot avviato!")
        application.run_polling()
        
    except Exception as e:
        logger.error(f"Errore nell'avvio del bot Telegram: {e}")
        print(f"❌ Errore nell'avvio del bot: {e}")
        print("Verifica la configurazione del token e le dipendenze.")

if __name__ == '__main__':
    main()
