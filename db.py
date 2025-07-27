import logging
from datetime import datetime, timedelta
import os
import psycopg2
import psycopg2.extras
from contextlib import contextmanager

logger = logging.getLogger(__name__)

class FamilyTaskDB:
    def __init__(self):
        self.test_mode = False
        self.fallback_mode = False
        self._tasks = []
        self._assigned = []
        self._members = {}
        self._completed = []
        self.db_url = os.environ.get("DATABASE_URL")
        if not self.db_url:
            logger.warning("DATABASE_URL non impostato nelle variabili d'ambiente! Modalità fallback attivata.")
            self.fallback_mode = True
            self._load_fallback_tasks()
        else:
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

    def _get_default_tasks(self):
        """Get the list of default tasks as fallback when database is unavailable"""
        return [
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
            ("aspirapolvere", "Passare l'aspirapolvere", 8, 15),
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

    def _get_default_tasks(self):
        """Get the list of default tasks as fallback when database is unavailable"""
        return [
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
            ("aspirapolvere", "Passare l'aspirapolvere", 8, 15),
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

    def _load_fallback_tasks(self):
        """Load tasks in fallback mode (memory-only) when database is unavailable"""
        default_tasks = self._get_default_tasks()
        self._tasks = [
            {"id": t[0], "name": t[1], "points": t[2], "time_minutes": t[3]}
            for t in default_tasks
        ]
        logger.info(f"Loaded {len(self._tasks)} tasks in fallback mode (no database)")

    def _load_tasks_from_db(self):
        """Load tasks from database with fallback to in-memory defaults"""
        default_tasks = self._get_default_tasks()
        
        try:
            with self.get_db_connection() as conn:
                cur = conn.cursor()
                # Task di default sempre sincronizzate
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
                logger.info(f"Successfully loaded {len(self._tasks)} tasks from database")
        except Exception as e:
            logger.warning(f"Database connection failed, using fallback tasks: {e}")
            # Use in-memory fallback tasks when database is unavailable
            self._tasks = [
                {"id": t[0], "name": t[1], "points": t[2], "time_minutes": t[3]}
                for t in default_tasks
            ]
            logger.info(f"Loaded {len(self._tasks)} fallback tasks in memory")

    def add_family_member(self, chat_id, user_id, username, first_name):
        """Add a family member with improved error handling and logging"""
        if self.fallback_mode:
            # In fallback mode, store members in memory
            if chat_id not in self._members:
                self._members[chat_id] = {}
            self._members[chat_id][user_id] = {
                'user_id': user_id,
                'username': username,
                'first_name': first_name,
                'joined_date': datetime.now()
            }
            logger.info(f"Added member {user_id} ({first_name}) in chat {chat_id} (fallback mode)")
            return

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
                logger.debug(f"Successfully added/updated member {user_id} ({first_name}) in chat {chat_id}")
        except psycopg2.Error as e:
            logger.error(f"Database error in add_family_member for user {user_id} ({first_name}) in chat {chat_id}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in add_family_member for user {user_id} ({first_name}) in chat {chat_id}: {e}")
            raise

    def get_all_tasks(self):
        try:
            return self._tasks.copy()
        except Exception as e:
            logger.error(f"Errore in get_all_tasks: {e}")
            return []

    def assign_task(self, chat_id, task_id, assigned_to, assigned_by):
        if self.fallback_mode:
            # In fallback mode, store assignments in memory
            assignment = {
                'chat_id': chat_id,
                'task_id': task_id,
                'assigned_to': assigned_to,
                'assigned_by': assigned_by,
                'assigned_date': datetime.now(),
                'status': 'assigned'
            }
            
            # Check for duplicate assignment
            existing = [a for a in self._assigned if 
                       a['chat_id'] == chat_id and 
                       a['task_id'] == task_id and 
                       a['assigned_to'] == assigned_to and 
                       a['status'] == 'assigned']
            if existing:
                raise ValueError(f"Task già assegnata a questo utente")
            
            self._assigned.append(assignment)
            logger.info(f"Assigned task {task_id} to user {assigned_to} in chat {chat_id} (fallback mode)")
            return

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
        except ValueError as e:
            # This is expected for duplicate assignments
            logger.info(f"Assignment validation failed for task {task_id} to user {assigned_to}: {e}")
            raise
        except psycopg2.Error as e:
            logger.error(f"Database error in assign_task (task: {task_id}, user: {assigned_to}, chat: {chat_id}): {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in assign_task (task: {task_id}, user: {assigned_to}, chat: {chat_id}): {e}")
            raise

    def get_user_assigned_tasks(self, chat_id, user_id):
        if self.fallback_mode:
            # In fallback mode, get assignments from memory
            user_assignments = [a for a in self._assigned if 
                               a['chat_id'] == chat_id and 
                               a['assigned_to'] == user_id and 
                               a['status'] == 'assigned']
            
            result = []
            for assignment in user_assignments:
                task = next((t for t in self._tasks if t['id'] == assignment['task_id']), None)
                if task:
                    result.append({
                        "task_id": task['id'],
                        "name": task['name'],
                        "points": task['points'],
                        "time_minutes": task['time_minutes']
                    })
            return result

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

    def complete_task(self, chat_id, task_id, user_id):
        """Complete a task with improved validation and error handling"""
        if self.fallback_mode:
            # In fallback mode, handle completion in memory
            # Find the assignment
            assignment = None
            for i, a in enumerate(self._assigned):
                if (a['chat_id'] == chat_id and 
                    a['task_id'] == task_id and 
                    a['assigned_to'] == user_id and 
                    a['status'] == 'assigned'):
                    assignment = a
                    assignment_index = i
                    break
            
            if not assignment:
                logger.warning(f"Attempted to complete non-assigned task in fallback mode: chat_id={chat_id}, task_id={task_id}, user_id={user_id}")
                return False
            
            # Find the task details
            task = next((t for t in self._tasks if t['id'] == task_id), None)
            if not task:
                logger.error(f"Task {task_id} not found in fallback mode")
                return False
            
            # Mark as completed and add to completed tasks
            completion = {
                'chat_id': chat_id,
                'task_id': task_id,
                'assigned_to': user_id,
                'assigned_by': assignment['assigned_by'],
                'assigned_date': assignment['assigned_date'],
                'completed_date': datetime.now(),
                'points_earned': task['points']
            }
            self._completed.append(completion)
            
            # Remove from assigned tasks
            self._assigned.pop(assignment_index)
            
            logger.info(f"Task {task_id} completed by user {user_id} in chat {chat_id} (+{task['points']} points) [fallback mode]")
            return True

        try:
            with self.get_db_connection() as conn:
                cur = conn.cursor()
                
                # First, check if the task assignment exists and is in 'assigned' status
                cur.execute("""
                    SELECT COUNT(*) FROM assigned_tasks 
                    WHERE chat_id = %s AND task_id = %s AND assigned_to = %s AND status = 'assigned';
                """, (chat_id, task_id, user_id))
                count = cur.fetchone()[0]
                
                if count == 0:
                    logger.warning(f"Attempted to complete non-assigned task: chat_id={chat_id}, task_id={task_id}, user_id={user_id}")
                    return False
                
                # Verify the task exists in the tasks table
                cur.execute("SELECT points FROM tasks WHERE id = %s;", (task_id,))
                task_result = cur.fetchone()
                if not task_result:
                    logger.error(f"Task {task_id} not found in tasks table")
                    return False
                
                points = task_result[0]
                
                # Update status to 'completed'
                cur.execute("""
                    UPDATE assigned_tasks SET status = 'completed' 
                    WHERE chat_id = %s AND task_id = %s AND assigned_to = %s AND status = 'assigned';
                """, (chat_id, task_id, user_id))
                
                # Insert into completed_tasks for history
                cur.execute("""
                    INSERT INTO completed_tasks (chat_id, task_id, assigned_to, assigned_by, assigned_date, completed_date, points_earned)
                    SELECT chat_id, task_id, assigned_to, assigned_by, assigned_date, NOW(), %s
                    FROM assigned_tasks
                    WHERE chat_id = %s AND task_id = %s AND assigned_to = %s AND status = 'completed';
                """, (points, chat_id, task_id, user_id))
                
                # Remove from assigned_tasks (so it can be reassigned)
                cur.execute("""
                    DELETE FROM assigned_tasks 
                    WHERE chat_id = %s AND task_id = %s AND assigned_to = %s AND status = 'completed';
                """, (chat_id, task_id, user_id))
                
                conn.commit()
                logger.info(f"Task {task_id} completed by user {user_id} in chat {chat_id} (+{points} points)")
                return True
                
        except psycopg2.Error as e:
            logger.error(f"Database error in complete_task (chat_id={chat_id}, task_id={task_id}, user_id={user_id}): {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error in complete_task (chat_id={chat_id}, task_id={task_id}, user_id={user_id}): {e}")
            return False

    def get_family_members(self, chat_id):
        if self.fallback_mode:
            # In fallback mode, get members from memory
            if chat_id in self._members:
                return [
                    {"user_id": user_id, "username": member['username'], "first_name": member['first_name']}
                    for user_id, member in self._members[chat_id].items()
                ]
            return []

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
        if self.fallback_mode:
            # In fallback mode, calculate stats from memory
            user_completions = [c for c in self._completed if c['assigned_to'] == user_id]
            total_points = sum(c['points_earned'] for c in user_completions)
            tasks_completed = len(user_completions)
            level = 1 + total_points // 50
            streak = min(tasks_completed, 7)
            return {
                'total_points': total_points,
                'tasks_completed': tasks_completed,
                'level': level,
                'streak': streak
            }

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

    def get_user_badges(self, user_id):
        """Get user badges - stub implementation for compatibility"""
        # This is a stub implementation for tests - badges are not implemented yet
        return []

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
        if self.fallback_mode:
            # In fallback mode, get assignments from memory
            chat_assignments = [a for a in self._assigned if 
                               a['chat_id'] == chat_id and 
                               a['status'] == 'assigned']
            
            result = []
            for assignment in chat_assignments:
                task = next((t for t in self._tasks if t['id'] == assignment['task_id']), None)
                if task:
                    result.append({
                        "task_id": task['id'],
                        "assigned_to": assignment['assigned_to'],
                        "name": task['name'],
                        "points": task['points'],
                        "time_minutes": task['time_minutes']
                    })
            return result

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
