#!/usr/bin/env python3

# Test specifico per le funzioni di assegnazione task
import os
import sys
import logging
from datetime import datetime, timedelta

# Aggiungi il path corrente per importare main.py
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from db import FamilyTaskDB

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

def test_assignment_functionality():
    """Test specifico per le funzioni di assegnazione"""
    print("\n🎯 Test delle Funzioni di Assegnazione Task\n")
    
    # Inizializza database in modalità test
    db = FamilyTaskDB()
    print(f"✅ Database inizializzato (modalità test: {db.test_mode})")
    
    # Setup dati di test
    chat_id = 123456
    user1_id = 789012
    user2_id = 789013
    
    # Aggiungi membri famiglia
    db.add_family_member(chat_id, user1_id, "mario", "Mario Rossi")
    db.add_family_member(chat_id, user2_id, "anna", "Anna Verdi")
    print("✅ Membri famiglia aggiunti")
    
    # Ottieni task disponibili
    tasks = db.get_all_tasks()
    if not tasks:
        print("❌ Nessuna task disponibile")
        return False
    
    test_task = tasks[0]
    task_id = test_task['id']
    print(f"✅ Task di test selezionata: {test_task['name']} (ID: {task_id})")
    
    # Test 1: Assegnazione normale
    print("\n📋 Test 1: Assegnazione normale")
    try:
        db.assign_task(chat_id, task_id, user1_id, user2_id)
        print(f"✅ Task {task_id} assegnata a user {user1_id}")
    except Exception as e:
        print(f"❌ Errore nell'assegnazione: {e}")
        return False
    
    # Test 2: Verifica assegnazione
    print("\n📋 Test 2: Verifica assegnazione")
    user_tasks = db.get_user_assigned_tasks(chat_id, user1_id)
    if user_tasks and len(user_tasks) > 0:
        assigned_task = user_tasks[0]
        if 'task_id' in assigned_task and assigned_task['task_id'] == task_id:
            print(f"✅ Task correttamente assegnata e recuperata")
            print(f"   Task ID: {assigned_task['task_id']}")
            print(f"   Nome: {assigned_task.get('name', 'N/A')}")
        else:
            print(f"❌ Task assegnata ma dati non corretti: {assigned_task}")
            return False
    else:
        print("❌ Task non trovata nelle assegnazioni utente")
        return False
    
    # Test 3: Tentativo di assegnazione duplicata
    print("\n📋 Test 3: Tentativo assegnazione duplicata")
    try:
        db.assign_task(chat_id, task_id, user1_id, user2_id)
        print("❌ Assegnazione duplicata non dovrebbe essere permessa")
        return False
    except ValueError as e:
        print(f"✅ Assegnazione duplicata correttamente bloccata: {e}")
    except Exception as e:
        print(f"❌ Errore inaspettato: {e}")
        return False
    
    # Test 4: Assegnazione a utente diverso
    print("\n📋 Test 4: Assegnazione a utente diverso")
    try:
        # Usa una task diversa per il secondo utente
        if len(tasks) > 1:
            second_task = tasks[1]
            second_task_id = second_task['id']
            db.assign_task(chat_id, second_task_id, user2_id, user1_id)
            print(f"✅ Task {second_task_id} assegnata a user {user2_id}")
            
            # Verifica che il secondo utente abbia la sua task
            user2_tasks = db.get_user_assigned_tasks(chat_id, user2_id)
            if user2_tasks and len(user2_tasks) > 0:
                print(f"✅ User2 ha {len(user2_tasks)} task assegnate")
            else:
                print("❌ User2 non ha task assegnate")
                return False
        else:
            print("⚠️ Skip test - solo una task disponibile")
    except Exception as e:
        print(f"❌ Errore nell'assegnazione a user2: {e}")
        return False
    
    # Test 5: Lista di tutte le task assegnate nella chat
    print("\n📋 Test 5: Lista task assegnate nella chat")
    all_assigned = db.get_assigned_tasks_for_chat(chat_id)
    print(f"✅ Totale task assegnate nella chat: {len(all_assigned)}")
    for task in all_assigned:
        print(f"   - Task {task.get('task_id')} → User {task.get('assigned_to')}")
    
    # Test 6: Completamento task e riassegnazione
    print("\n📋 Test 6: Completamento e riassegnazione")
    try:
        # Completa la prima task
        points, msg = db.complete_task(chat_id, task_id, user1_id)
        if points > 0:
            print(f"✅ Task completata: +{points} punti")
            
            # Ora dovrebbe essere possibile riassegnare la stessa task
            db.assign_task(chat_id, task_id, user2_id, user1_id)
            print(f"✅ Task riassegnata dopo completamento")
        else:
            print("❌ Completamento task fallito")
            return False
    except Exception as e:
        print(f"❌ Errore nel completamento/riassegnazione: {e}")
        return False
    
    print("\n🎉 Tutti i test di assegnazione completati con successo!")
    return True

if __name__ == "__main__":
    try:
        success = test_assignment_functionality()
        if success:
            print("\n✅ Sistema di assegnazione task funzionante!")
            exit(0)
        else:
            print("\n❌ Problemi rilevati nel sistema di assegnazione!")
            exit(1)
    except Exception as e:
        print(f"\n❌ Errore durante i test: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
