import logging
from datetime import datetime, timedelta
import os
import psycopg2
import psycopg2.extras

logger = logging.getLogger(__name__)

class FamilyTaskDB:
    def __init__(self):
        self.test_mode = False
        self._tasks = []
        self._assigned = []
        self._members = {}
        self._completed = []
        self.conn = None
        self._connect_db()
        self._load_tasks_from_db()

    def _connect_db(self):
        import psycopg2
        import os
        db_url = os.environ.get("DATABASE_URL")
        if not db_url:
            raise RuntimeError("DATABASE_URL non impostato nelle variabili d'ambiente!")
        self.conn = psycopg2.connect(db_url, sslmode='require')

    def _load_tasks_from_db(self):
        cur = self.conn.cursor()
        cur.execute("SELECT id, name, points, time_minutes FROM tasks;")
        rows = cur.fetchall()
        if not rows:
            # Se il DB è vuoto, inserisci task di default
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
                ("auto", "Lavare l'auto", 13, 30)
            ]
            for t in default_tasks:
                cur.execute(
                    "INSERT INTO tasks (id, name, points, time_minutes) VALUES (%s, %s, %s, %s) ON CONFLICT (id) DO NOTHING;",
                    t
                )
            self.conn.commit()
            cur.execute("SELECT id, name, points, time_minutes FROM tasks;")
            rows = cur.fetchall()
        self._tasks = [
            {"id": row[0], "name": row[1], "points": row[2], "time_minutes": row[3]}
            for row in rows
        ]
        cur.close()

    def add_family_member(self, chat_id, user_id, username, first_name):
        try:
            # Assicura che la famiglia esista
            cur = self.conn.cursor()
            cur.execute("INSERT INTO families (chat_id) VALUES (%s) ON CONFLICT DO NOTHING;", (chat_id,))
            # Ora aggiungi il membro
            cur.execute("""
                INSERT INTO family_members (chat_id, user_id, username, first_name, joined_date)
                VALUES (%s, %s, %s, %s, NOW())
                ON CONFLICT (chat_id, user_id) DO NOTHING;
            """, (chat_id, user_id, username, first_name))
            self.conn.commit()
            cur.close()
        except Exception as e:
            logger.error(f"Errore in add_family_member: {e}")
            self.conn.rollback()

    def get_all_tasks(self):
        try:
            return self._tasks.copy()
        except Exception as e:
            logger.error(f"Errore in get_all_tasks: {e}")
            return []

    def assign_task(self, chat_id, task_id, assigned_to, assigned_by):
        try:
            cur = self.conn.cursor()
            cur.execute(
                """
                INSERT INTO assigned_tasks (chat_id, task_id, assigned_to, assigned_by, assigned_date, status)
                VALUES (%s, %s, %s, %s, NOW(), 'assigned')
                ON CONFLICT (chat_id, task_id, assigned_to) DO NOTHING;
                """,
                (chat_id, task_id, assigned_to, assigned_by)
            )
            inserted = cur.rowcount
            self.conn.commit()
            cur.close()
            if inserted == 0:
                # Task già assegnata a questo utente
                raise ValueError("Task già assegnata a questo utente!")
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Errore in assign_task: {e}")
            self.conn.rollback()
            raise

    def get_user_assigned_tasks(self, chat_id, user_id):
        try:
            cur = self.conn.cursor()
            cur.execute("""
                SELECT t.id, t.name, t.points, t.time_minutes
                FROM assigned_tasks a
                JOIN tasks t ON a.task_id = t.id
                WHERE a.chat_id = %s AND a.assigned_to = %s AND a.status = 'assigned';
            """, (chat_id, user_id))
            rows = cur.fetchall()
            cur.close()
            return [
                {"task_id": row[0], "name": row[1], "points": row[2], "time_minutes": row[3]}
                for row in rows
            ]
        except Exception as e:
            logger.error(f"Errore in get_user_assigned_tasks: {e}")
            self.conn.rollback()
            return []

    def complete_task(self, chat_id, task_id, user_id):
        try:
            cur = self.conn.cursor()
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
            # Elimina la riga da assigned_tasks (così può essere riassegnata)
            cur.execute("""
                DELETE FROM assigned_tasks WHERE chat_id = %s AND task_id = %s AND assigned_to = %s AND status = 'completed';
            """, (chat_id, task_id, user_id))
            self.conn.commit()
            cur.close()
            return True
        except Exception as e:
            logger.error(f"Errore in complete_task: {e}")
            self.conn.rollback()
            return False

    def get_family_members(self, chat_id):
        try:
            cur = self.conn.cursor()
            cur.execute("SELECT user_id, username, first_name FROM family_members WHERE chat_id = %s;", (chat_id,))
            rows = cur.fetchall()
            cur.close()
            return [
                {"user_id": row[0], "username": row[1], "first_name": row[2]} for row in rows
            ]
        except Exception as e:
            logger.error(f"Errore in get_family_members: {e}")
            self.conn.rollback()
            return []

    def get_user_stats(self, user_id):
        try:
            cur = self.conn.cursor()
            cur.execute("""
                SELECT COALESCE(SUM(t.points),0), COUNT(*)
                FROM assigned_tasks a
                JOIN tasks t ON a.task_id = t.id
                WHERE a.assigned_to = %s AND a.status = 'completed';
            """, (user_id,))
            row = cur.fetchone()
            cur.close()
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
            self.conn.rollback()
            return None

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
            self.conn.rollback()
            return []

    def get_task_by_id(self, task_id):
        try:
            for t in self._tasks:
                if t['id'] == task_id:
                    return t
            cur = self.conn.cursor()
            cur.execute("SELECT id, name, points, time_minutes FROM tasks WHERE id = %s;", (task_id,))
            row = cur.fetchone()
            cur.close()
            if row:
                return {"id": row[0], "name": row[1], "points": row[2], "time_minutes": row[3]}
            return None
        except Exception as e:
            logger.error(f"Errore in get_task_by_id: {e}")
            self.conn.rollback()
            return None
