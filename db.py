import logging
from datetime import datetime, timedelta
import os
import psycopg2
import psycopg2.extras
from contextlib import contextmanager
import calendar

logger = logging.getLogger(__name__)

class FamilyTaskDB:
    def __init__(self):
        self.test_mode = False
        self._tasks = []
        self._assigned = []
        self._members = {}
        self._completed = []
        self.db_url = os.environ.get("DATABASE_URL")
        if not self.db_url:
            raise RuntimeError("DATABASE_URL non impostato nelle variabili d'ambiente!")
        self._load_tasks_from_db()

    @contextmanager
    def get_db_connection(self):
        """Context manager for database connections"""
        conn = None
        try:
            conn = psycopg2.connect(self.db_url, sslmode='require')
            yield conn
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Errore connessione database: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def _load_tasks_from_db(self):
        with self.get_db_connection() as conn:
            cur = conn.cursor()
            # Task di default sempre sincronizzate
            default_tasks = [
                ("cucina_pulizia", "Pulizia cucina", 10, 20),
                ("bagno_pulizia", "Pulizia bagno", 12, 25),
                ("spazzatura", "Portare fuori la spazzatura", 5, 5),
                ("bucato", "Fare il bucato", 8, 15),
                ("giardino", "Cura del giardino", 15, 30),
                ("spesa", "Fare la spesa", 7, 20),
                ("cena", "Preparare la cena", 10, 25),
                ("camera", "Riordinare la camera", 6, 10),
                ("animali", "Dare da mangiare agli animali", 4, 5),
                ("auto", "Lavare l'auto", 13, 30),
                ("lavastoviglie", "Caricare lavastoviglie", 6, 8),
                ("stendere_bucato", "Stendere il bucato", 6, 10),
                ("aspirapolvere", "Passare l’aspirapolvere", 8, 15),
                ("svuotare_lavastoviglie", "Svuotare la lavastoviglie", 5, 5),
                ("riordinare_soggiorno", "Riordinare il soggiorno", 6, 10),
                ("buttare_rifiuti", "Buttare la carta/vetro/plastica", 5, 5),
                ("fare_letti", "Fare i letti", 4, 5),
                ("preparare_tavola", "Preparare la tavola", 4, 5),
                ("sparecchiare_tavola", "Sparecchiare la tavola", 4, 5),
                ("lettiera_gatto", "Pulire la lettiera del gatto", 6, 8),
                ("pulire_garage", "Pulire il garage", 15, 30),
                ("pulire_finestre", "Pulire le finestre", 10, 20),
                ("organizzare_armadi", "Organizzare gli armadi", 12, 25),
                ("pulire_frigorifero", "Pulire il frigorifero", 8, 15),
                ("innaffiare_piante", "Innaffiare le piante", 3, 5),
                ("pulire_specchi", "Pulire gli specchi", 5, 10),
                ("cambiare_lenzuola", "Cambiare le lenzuola", 7, 15),
                ("pulire_forno", "Pulire il forno", 12, 25),
                ("raccogliere_foglie", "Raccogliere le foglie", 8, 20),
                ("pulire_balcone", "Pulire il balcone", 6, 15),
                ("organizzare_cantina", "Organizzare la cantina", 15, 40),
                ("pulire_scarpe", "Pulire le scarpe", 4, 10),
                ("spolverare_mobili", "Spolverare i mobili", 6, 15),
                ("pulire_elettrodomestici", "Pulire gli elettrodomestici", 10, 20),
                ("riordinare_scrivania", "Riordinare la scrivania", 5, 10),
                ("pulire_tappeti", "Pulire i tappeti", 9, 20),
                ("organizzare_garage", "Organizzare il garage", 18, 45),
                ("pulire_scale", "Pulire le scale", 7, 15),
                ("cambiare_filtri", "Cambiare i filtri dell'aria", 8, 20),
                ("pulire_ventilatori", "Pulire i ventilatori", 6, 15),
                ("organizzare_dispensa", "Organizzare la dispensa", 10, 25)
            ]
            for t in default_tasks:
                cur.execute(
                    "INSERT INTO tasks (id, name, points, time_minutes) VALUES (%s, %s, %s, %s) ON CONFLICT (id) DO NOTHING;",
                    t
                )
            conn.commit()
            cur.execute("SELECT id, name, points, time_minutes FROM tasks;")
            rows = cur.fetchall()
        self._tasks = [
            {"id": row[0], "name": row[1], "points": row[2], "time_minutes": row[3]}
            for row in rows
        ]

    def add_family_member(self, chat_id, user_id, username, first_name):
        try:
            with self.get_db_connection() as conn:
                cur = conn.cursor()
                cur.execute("INSERT INTO families (chat_id) VALUES (%s) ON CONFLICT DO NOTHING;", (chat_id,))
                # Ora aggiungi il membro
                cur.execute("""
                    INSERT INTO family_members (chat_id, user_id, username, first_name, joined_date)
                    VALUES (%s, %s, %s, %s, NOW())
                    ON CONFLICT (chat_id, user_id) DO NOTHING;
                """, (chat_id, user_id, username, first_name))
                conn.commit()
        except Exception as e:
            logger.error(f"Errore in add_family_member: {e}")
            raise

    def get_all_tasks(self):
        try:
            return self._tasks.copy()
        except Exception as e:
            logger.error(f"Errore in get_all_tasks: {e}")
            return []

    def assign_task(self, chat_id, task_id, assigned_to, assigned_by):
        try:
            with self.get_db_connection() as conn:
                cur = conn.cursor()
                # Check if already assigned to prevent duplicate
                cur.execute(
                    """
                    SELECT COUNT(*) FROM assigned_tasks 
                    WHERE chat_id = %s AND task_id = %s AND assigned_to = %s AND status = 'assigned';
                    """,
                    (chat_id, task_id, assigned_to)
                )
                count = cur.fetchone()[0]
                
                if count > 0:
                    raise ValueError(f"Task già assegnata a questo utente")
                
                # Allow multiple assignments to different users
                cur.execute(
                    """
                    INSERT INTO assigned_tasks (chat_id, task_id, assigned_to, assigned_by, assigned_date, status)
                    VALUES (%s, %s, %s, %s, NOW(), 'assigned');
                    """,
                    (chat_id, task_id, assigned_to, assigned_by)
                )
                conn.commit()
        except Exception as e:
            logger.error(f"Errore in assign_task: {e}")
            raise

    def get_user_assigned_tasks(self, chat_id, user_id):
        try:
            with self.get_db_connection() as conn:
                cur = conn.cursor()
                cur.execute("""
                    SELECT t.id, t.name, t.points, t.time_minutes
                    FROM assigned_tasks a
                    JOIN tasks t ON a.task_id = t.id
                    WHERE a.chat_id = %s AND a.assigned_to = %s AND a.status = 'assigned';
                """, (chat_id, user_id))
                rows = cur.fetchall()
                return [
                    {"task_id": row[0], "name": row[1], "points": row[2], "time_minutes": row[3]}
                    for row in rows
                ]
        except Exception as e:
            logger.error(f"Errore in get_user_assigned_tasks: {e}")
            return []

    def complete_task_immediately(self, chat_id, task_id, user_id):
        """Complete a task immediately (auto-assign and complete in one step)"""
        try:
            with self.get_db_connection() as conn:
                cur = conn.cursor()
                
                # Get task details for points
                task = self.get_task_by_id(task_id)
                if not task:
                    return False
                
                # Insert directly into completed_tasks without going through assigned_tasks
                cur.execute("""
                    INSERT INTO completed_tasks (chat_id, task_id, assigned_to, assigned_by, assigned_date, completed_date, points_earned)
                    VALUES (%s, %s, %s, %s, NOW(), NOW(), %s);
                """, (chat_id, task_id, user_id, user_id, task['points']))
                
                # Update monthly statistics
                self._update_monthly_stats(user_id, task['points'], cur)
                
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Errore in complete_task_immediately: {e}")
            return False

    def _update_monthly_stats(self, user_id, points, cursor):
        """Update monthly statistics for a user"""
        now = datetime.now()
        current_year = now.year
        current_month = now.month
        
        cursor.execute("""
            INSERT INTO monthly_stats (user_id, year, month, points_earned, tasks_completed)
            VALUES (%s, %s, %s, %s, 1)
            ON CONFLICT (user_id, year, month)
            DO UPDATE SET 
                points_earned = monthly_stats.points_earned + %s,
                tasks_completed = monthly_stats.tasks_completed + 1;
        """, (user_id, current_year, current_month, points, points))

    def complete_task(self, chat_id, task_id, user_id):
        try:
            with self.get_db_connection() as conn:
                cur = conn.cursor()
                # Aggiorna lo stato a 'completed'
                cur.execute("""
                    UPDATE assigned_tasks SET status = 'completed' WHERE chat_id = %s AND task_id = %s AND assigned_to = %s AND status = 'assigned';
                """, (chat_id, task_id, user_id))
                # Sposta la riga in completed_tasks per storico
                cur.execute("""
                    INSERT INTO completed_tasks (chat_id, task_id, assigned_to, assigned_by, assigned_date, completed_date, points_earned)
                    SELECT chat_id, task_id, assigned_to, assigned_by, assigned_date, NOW(),
                           (SELECT points FROM tasks WHERE id = assigned_tasks.task_id)
                    FROM assigned_tasks
                    WHERE chat_id = %s AND task_id = %s AND assigned_to = %s AND status = 'completed';
                """, (chat_id, task_id, user_id))
                
                # Get points for monthly stats update
                task = self.get_task_by_id(task_id)
                if task:
                    self._update_monthly_stats(user_id, task['points'], cur)
                
                # Elimina la riga da assigned_tasks (così può essere riassegnata)
                cur.execute("""
                    DELETE FROM assigned_tasks WHERE chat_id = %s AND task_id = %s AND assigned_to = %s AND status = 'completed';
                """, (chat_id, task_id, user_id))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Errore in complete_task: {e}")
            return False

    def get_family_members(self, chat_id):
        try:
            with self.get_db_connection() as conn:
                cur = conn.cursor()
                cur.execute("SELECT user_id, username, first_name FROM family_members WHERE chat_id = %s;", (chat_id,))
                rows = cur.fetchall()
                return [
                    {"user_id": row[0], "username": row[1], "first_name": row[2]} for row in rows
                ]
        except Exception as e:
            logger.error(f"Errore in get_family_members: {e}")
            return []

    def get_user_stats(self, user_id):
        try:
            with self.get_db_connection() as conn:
                cur = conn.cursor()
                cur.execute("""
                    SELECT COALESCE(SUM(points_earned),0), COUNT(*)
                    FROM completed_tasks
                    WHERE assigned_to = %s;
                """, (user_id,))
                row = cur.fetchone()
                total_points = row[0] or 0
                tasks_completed = row[1] or 0
                level = 1 + total_points // 50
                streak = min(tasks_completed, 7)
                return {
                    'total_points': total_points,
                    'tasks_completed': tasks_completed,
                    'level': level,
                    'streak': streak
                }
        except Exception as e:
            logger.error(f"Errore in get_user_stats: {e}")
            return None

    def get_user_task_completion_stats(self, user_id):
        """Get individual task completion statistics for a user"""
        try:
            with self.get_db_connection() as conn:
                cur = conn.cursor()
                cur.execute("""
                    SELECT t.name, COUNT(*) as completion_count
                    FROM completed_tasks ct
                    JOIN tasks t ON ct.task_id = t.id
                    WHERE ct.assigned_to = %s
                    GROUP BY ct.task_id, t.name
                    ORDER BY completion_count DESC, t.name ASC;
                """, (user_id,))
                rows = cur.fetchall()
                return [
                    {"task_name": row[0], "completion_count": row[1]}
                    for row in rows
                ]
        except Exception as e:
            logger.error(f"Errore in get_user_task_completion_stats: {e}")
            return []

    def get_leaderboard(self, chat_id):
        try:
            members = self.get_family_members(chat_id)
            leaderboard = []
            for m in members:
                stats = self.get_user_stats(m['user_id'])
                if stats:
                    leaderboard.append({
                        'user_id': m['user_id'],
                        'first_name': m['first_name'],
                        'total_points': stats['total_points'],
                        'tasks_completed': stats['tasks_completed'],
                        'level': stats['level']
                    })
            leaderboard.sort(key=lambda x: (-x['total_points'], -x['tasks_completed']))
            return leaderboard
        except Exception as e:
            logger.error(f"Errore in get_leaderboard: {e}")
            return []

    def get_task_by_id(self, task_id):
        try:
            for t in self._tasks:
                if t['id'] == task_id:
                    return t
            with self.get_db_connection() as conn:
                cur = conn.cursor()
                cur.execute("SELECT id, name, points, time_minutes FROM tasks WHERE id = %s;", (task_id,))
                row = cur.fetchone()
                if row:
                    return {"id": row[0], "name": row[1], "points": row[2], "time_minutes": row[3]}
            return None
        except Exception as e:
            logger.error(f"Errore in get_task_by_id: {e}")
            return None

    def get_assigned_tasks_for_chat(self, chat_id):
        try:
            with self.get_db_connection() as conn:
                cur = conn.cursor()
                cur.execute("""
                    SELECT a.task_id, a.assigned_to, t.name, t.points, t.time_minutes
                    FROM assigned_tasks a
                    JOIN tasks t ON a.task_id = t.id
                    WHERE a.chat_id = %s AND a.status = 'assigned';
                """, (chat_id,))
                rows = cur.fetchall()
                return [
                    {"task_id": row[0], "assigned_to": row[1], "name": row[2], "points": row[3], "time_minutes": row[4]}
                    for row in rows
                ]
        except Exception as e:
            logger.error(f"Errore in get_assigned_tasks_for_chat: {e}")
            return []

    def get_monthly_stats(self, user_id):
        """Get monthly statistics for a user for the current year"""
        try:
            with self.get_db_connection() as conn:
                cur = conn.cursor()
                current_year = datetime.now().year
                cur.execute("""
                    SELECT month, points_earned, tasks_completed
                    FROM monthly_stats
                    WHERE user_id = %s AND year = %s
                    ORDER BY month;
                """, (user_id, current_year))
                rows = cur.fetchall()
                
                # Fill missing months with zeros
                monthly_data = {}
                for month in range(1, 13):
                    monthly_data[month] = {'points': 0, 'tasks': 0}
                
                for row in rows:
                    month, points, tasks = row
                    monthly_data[month] = {'points': points, 'tasks': tasks}
                
                return monthly_data
        except Exception as e:
            logger.error(f"Errore in get_monthly_stats: {e}")
            return {}

    def get_current_month_stats(self, user_id):
        """Get current month statistics for a user"""
        try:
            with self.get_db_connection() as conn:
                cur = conn.cursor()
                now = datetime.now()
                current_year = now.year
                current_month = now.month
                
                cur.execute("""
                    SELECT points_earned, tasks_completed
                    FROM monthly_stats
                    WHERE user_id = %s AND year = %s AND month = %s;
                """, (user_id, current_year, current_month))
                row = cur.fetchone()
                
                if row:
                    return {'points': row[0], 'tasks': row[1]}
                else:
                    return {'points': 0, 'tasks': 0}
        except Exception as e:
            logger.error(f"Errore in get_current_month_stats: {e}")
            return {'points': 0, 'tasks': 0}

    def reset_monthly_stats(self):
        """Reset monthly stats (called at the beginning of each month)"""
        try:
            with self.get_db_connection() as conn:
                cur = conn.cursor()
                # The monthly stats are kept for historical purposes
                # This method can be used for future cleanup if needed
                logger.info("Monthly stats structure maintained for historical tracking")
                return True
        except Exception as e:
            logger.error(f"Errore in reset_monthly_stats: {e}")
            return False
