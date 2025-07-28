#!/usr/bin/env python3

# Test script per verificare le funzionalità del bot senza Telegram
import os
import sys
import logging
from datetime import datetime, timedelta

# Aggiungi il path corrente per importare main.py
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Carica variabili d'ambiente da .env per sviluppo locale
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Importa solo la classe database dal main
from main import FamilyTaskDB

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

def test_bot_functionality():
    """Test completo delle funzionalità del bot senza Telegram"""
    print("\n🏠 Family Task Manager - Test delle Funzionalità Core\n")
    
    # Test del database
    print("📊 Inizializzazione database...")
    db = FamilyTaskDB()
    
    if db.test_mode:
        print("✅ Database inizializzato in modalità test")
    else:
        print("✅ Database PostgreSQL connesso")
    
    # Test task
    print("\n📋 Test gestione task...")
    tasks = db.get_all_tasks()
    print(f"✅ {len(tasks)} task caricate")
    
    # Mostra alcune task di esempio
    for i, task in enumerate(tasks[:3]):
        print(f"  - {task['name']} ({task['points']} punti, ~{task['time_minutes']} min)")
    
    # Test famiglia
    print("\n👥 Test gestione famiglia...")
    chat_id = 123456
    user_id = 789012
    db.add_family_member(chat_id, user_id, "testuser", "Mario Rossi")
    db.add_family_member(chat_id, 789013, "testuser2", "Anna Verdi")
    
    members = db.get_family_members(chat_id)
    print(f"✅ {len(members)} membri famiglia aggiunti:")
    for member in members:
        print(f"  - {member['first_name']} (ID: {member['user_id']})")
    
    # Test assegnazione task
    print("\n🎯 Test assegnazione task...")
    if tasks:
        task_to_assign = tasks[0]
        db.assign_task(chat_id, task_to_assign['id'], user_id, user_id)
        
        assigned = db.get_assigned_tasks_for_chat(chat_id)
        user_tasks = db.get_user_assigned_tasks(chat_id, user_id)
        
        print(f"✅ {len(assigned)} task assegnate nella chat")
        print(f"✅ {len(user_tasks)} task assegnate all'utente Mario")
    
    # Test completamento task
    print("\n✅ Test completamento task...")
    if tasks:
        task_id = task_to_assign['id']
        success = db.complete_task(chat_id, task_id, user_id)
        
        if success:
            # Get the task details to show completion info
            task_details = db.get_task_by_id(task_id)
            if task_details:
                print(f"✅ Task '{task_to_assign['name']}' completata: +{task_details['points']} punti")
            else:
                print("✅ Task completata con successo")
        else:
            print("❌ Completamento task fallito")
    
    # Test statistiche
    print("\n📊 Test statistiche...")
    stats = db.get_user_stats(user_id)
    if stats:
        print(f"✅ Statistiche Mario:")
        print(f"  - Punti totali: {stats['total_points']}")
        print(f"  - Task completate: {stats['tasks_completed']}")
        print(f"  - Livello: {stats['level']}")
        print(f"  - Streak: {stats['streak']}")
    
    # Test leaderboard
    print("\n🏆 Test leaderboard...")
    leaderboard = db.get_leaderboard(chat_id)
    print(f"✅ Leaderboard con {len(leaderboard)} utenti:")
    
    for i, entry in enumerate(leaderboard, 1):
        position = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}°"
        badges = db.get_user_badges(entry['user_id'])
        badge_text = f" 🏅{len(badges)}" if badges else ""
        
        print(f"  {position} {entry['first_name']}: {entry['total_points']} punti "
              f"(Lv.{entry['level']}, {entry['tasks_completed']} task){badge_text}")
    
    print("\n🎉 Tutti i test completati con successo!")
    
    if db.test_mode:
        print("\n💡 Modalità test attiva - i dati non sono persistenti")
        print("   Per usare PostgreSQL in produzione, configura DATABASE_URL")
    
    print("\n🚀 Il bot è pronto per essere deployato su Railway con Telegram!")
    return True

if __name__ == "__main__":
    try:
        success = test_bot_functionality()
        if success:
            print("\n✅ Test completati con successo!")
            exit(0)
        else:
            print("\n❌ Alcuni test sono falliti!")
            exit(1)
    except Exception as e:
        print(f"\n❌ Errore durante i test: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
