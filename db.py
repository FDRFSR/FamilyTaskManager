import logging
from datetime import datetime, timedelta
import os
import psycopg2
import psycopg2.extras

logger = logging.getLogger(__name__)

class FamilyTaskDB:
    def __init__(self):
        self.test_mode = True
        self._tasks = [
            {"id": "cucina_pulizia", "name": "Pulizia cucina", "points": 10, "time_minutes": 20},
            {"id": "bagno_pulizia", "name": "Pulizia bagno", "points": 12, "time_minutes": 25},
            {"id": "spazzatura", "name": "Portare fuori la spazzatura", "points": 5, "time_minutes": 5},
            {"id": "bucato", "name": "Fare il bucato", "points": 8, "time_minutes": 15},
            {"id": "giardino", "name": "Cura del giardino", "points": 15, "time_minutes": 30},
            {"id": "spesa", "name": "Fare la spesa", "points": 7, "time_minutes": 20},
            {"id": "cena", "name": "Preparare la cena", "points": 10, "time_minutes": 25},
            {"id": "camera", "name": "Riordinare la camera", "points": 6, "time_minutes": 10},
            {"id": "animali", "name": "Dare da mangiare agli animali", "points": 4, "time_minutes": 5},
            {"id": "auto", "name": "Lavare l'auto", "points": 13, "time_minutes": 30},
        ]
        self._assigned = []  # [{chat_id, task_id, assigned_to, assigned_by}]
        self._members = {}   # chat_id: [{user_id, username, first_name}]

    def add_family_member(self, chat_id, user_id, username, first_name):
        if chat_id not in self._members:
            self._members[chat_id] = []
        if not any(m['user_id'] == user_id for m in self._members[chat_id]):
            self._members[chat_id].append({"user_id": user_id, "username": username, "first_name": first_name})

    def get_all_tasks(self):
        return self._tasks.copy()

    def assign_task(self, chat_id, task_id, assigned_to, assigned_by):
        # Non permette doppioni
        for a in self._assigned:
            if a['chat_id'] == chat_id and a['task_id'] == task_id and a['assigned_to'] == assigned_to:
                raise ValueError("Task già assegnata a questo utente!")
        self._assigned.append({
            "chat_id": chat_id,
            "task_id": task_id,
            "assigned_to": assigned_to,
            "assigned_by": assigned_by
        })

    def get_user_assigned_tasks(self, chat_id, user_id):
        assigned_ids = [a['task_id'] for a in self._assigned if a['chat_id'] == chat_id and a['assigned_to'] == user_id]
        return [
            {"task_id": t["id"], "name": t["name"], "points": t["points"], "time_minutes": t["time_minutes"]}
            for t in self._tasks if t["id"] in assigned_ids
        ]

    def get_assigned_tasks_for_chat(self, chat_id):
        return [a for a in self._assigned if a['chat_id'] == chat_id]

    def get_family_members(self, chat_id):
        return self._members.get(chat_id, [])

    def get_task_by_id(self, task_id):
        for t in self._tasks:
            if t['id'] == task_id:
                return t
        return None
