import logging
from datetime import datetime, timedelta
import os
import psycopg2
import psycopg2.extras

logger = logging.getLogger(__name__)

class FamilyTaskDB:
    def __init__(self):
        self.test_mode = True  # Stub: sempre test mode

    def get_all_tasks(self):
        # Stub: restituisce task di esempio
        return [
            {"id": "cucina_pulizia", "name": "Pulizia cucina", "points": 10, "time_minutes": 20},
            {"id": "bagno_pulizia", "name": "Pulizia bagno", "points": 12, "time_minutes": 25},
            {"id": "spazzatura", "name": "Portare fuori la spazzatura", "points": 5, "time_minutes": 5},
        ]

    def get_leaderboard(self, chat_id):
        # Stub: restituisce leaderboard di esempio
        return [
            {"user_id": 1, "first_name": "Mario", "total_points": 50, "level": 2, "tasks_completed": 5},
            {"user_id": 2, "first_name": "Anna", "total_points": 40, "level": 2, "tasks_completed": 4},
        ]

    def get_user_stats(self, user_id):
        # Stub: restituisce statistiche di esempio
        return {"total_points": 50, "tasks_completed": 5, "level": 2, "streak": 3}

    def get_user_assigned_tasks(self, chat_id, user_id):
        # Stub: restituisce task assegnate di esempio
        return [
            {"task_id": "cucina_pulizia", "name": "Pulizia cucina", "points": 10, "time_minutes": 20},
            {"task_id": "spazzatura", "name": "Portare fuori la spazzatura", "points": 5, "time_minutes": 5},
        ]

    def add_family_member(self, chat_id, user_id, username, first_name):
        # Stub: non fa nulla
        pass

    # ...existing code...
