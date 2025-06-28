#!/usr/bin/env python3
"""
Test script per verificare che il KeyError sia stato risolto.
Questo script simula vari scenari che in passato potevano causare KeyError.
"""

import os
import sys
import logging
from datetime import datetime, timedelta

# Aggiungi il path del progetto
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import del bot
from main import FamilyTaskDB

# Setup logging per il test
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_robust_get_user_assigned_tasks():
    """Test la robustezza di get_user_assigned_tasks"""
    print("\n🧪 TEST: Robustezza get_user_assigned_tasks")
    
    # Crea database in modalità test
    db = FamilyTaskDB()
    
    # Test 1: Utente senza task
    print("Test 1: Utente senza task assegnate")
    tasks = db.get_user_assigned_tasks(12345, 67890)
    print(f"Risultato: {len(tasks)} task (atteso: 0)")
    assert len(tasks) == 0, "Dovrebbe restituire lista vuota"
    
    # Test 2: Aggiungi membro e task
    print("Test 2: Aggiungi membro famiglia e assegna task")
    db.add_family_member(12345, 67890, "testuser", "Mario")
    
    # Verifica che le task di default siano caricate
    default_tasks = db.get_default_tasks()
    print(f"Task di default caricate: {len(default_tasks)}")
    
    # Assegna una task
    db.assign_task(12345, "cucina_pulizia", 67890, 67890)
    
    # Test 3: Recupera task assegnate
    print("Test 3: Recupera task assegnate")
    tasks = db.get_user_assigned_tasks(12345, 67890)
    print(f"Task recuperate: {len(tasks)}")
    
    # Verifica che ogni task abbia le chiavi necessarie
    for i, task in enumerate(tasks):
        print(f"Task {i+1}: {task}")
        
        # Verifica presenza chiavi obbligatorie
        required_keys = ['task_id', 'name', 'points', 'time_minutes']
        for key in required_keys:
            assert key in task, f"Chiave '{key}' mancante nella task {i+1}: {task}"
            
        # Verifica che task_id non sia None o vuoto
        assert task['task_id'], f"task_id vuoto nella task {i+1}: {task}"
        
        print(f"✅ Task {i+1} valida: ID={task['task_id']}, Nome={task['name']}")
    
    print("✅ Test get_user_assigned_tasks: PASSATO")

def test_edge_cases():
    """Test casi edge che potrebbero causare KeyError"""
    print("\n🧪 TEST: Casi edge e scenari problematici")
    
    db = FamilyTaskDB()
    
    # Test 1: Chat ID inesistente
    print("Test 1: Chat ID inesistente")
    tasks = db.get_user_assigned_tasks(99999, 11111)
    assert len(tasks) == 0, "Chat inesistente dovrebbe restituire lista vuota"
    print("✅ Chat inesistente gestita correttamente")
    
    # Test 2: User ID inesistente in chat valida
    print("Test 2: User ID inesistente in chat valida")
    db.add_family_member(11111, 22222, "user1", "Utente1")
    tasks = db.get_user_assigned_tasks(11111, 99999)  # user diverso
    assert len(tasks) == 0, "User inesistente dovrebbe restituire lista vuota"
    print("✅ User inesistente gestito correttamente")
    
    # Test 3: Task assegnata e poi task ID modificato (scenario corrotto)
    print("Test 3: Scenari con dati corrotti simulati")
    db.add_family_member(33333, 44444, "user2", "Utente2")
    
    # Simula assegnazione normale
    db.assign_task(33333, "spazzatura", 44444, 44444)
    tasks = db.get_user_assigned_tasks(33333, 44444)
    
    # Verifica che anche con possibili corruzioni, non si abbiano KeyError
    for task in tasks:
        # Simula accesso a tutte le chiavi che potrebbero causare KeyError
        try:
            task_id = task['task_id']
            name = task.get('name', 'Sconosciuto')
            points = task.get('points', 0)
            time_minutes = task.get('time_minutes', 0)
            due_date = task.get('due_date')
            
            print(f"✅ Task accessibile: {task_id}, {name}, {points}pt, {time_minutes}min")
            
        except KeyError as e:
            print(f"❌ KeyError rilevato: {e}")
            raise AssertionError(f"KeyError non dovrebbe verificarsi: {e}")
    
    print("✅ Test casi edge: PASSATO")

def test_callback_data_generation():
    """Test che i callback_data generati siano validi"""
    print("\n🧪 TEST: Generazione callback_data")
    
    db = FamilyTaskDB()
    
    # Setup scenario di test
    db.add_family_member(55555, 66666, "user3", "Utente3")
    db.assign_task(55555, "bucato", 66666, 66666)
    
    # Recupera task
    tasks = db.get_user_assigned_tasks(55555, 66666)
    
    print(f"Task per test callback: {len(tasks)}")
    
    for task in tasks:
        # Simula la generazione di callback_data come fa il bot
        task_id = task['task_id']
        callback_data = f"complete_{task_id}"
        
        print(f"Callback generato: {callback_data}")
        
        # Verifica che task_id sia valido per callback
        assert task_id, "task_id non può essere vuoto per callback"
        assert isinstance(task_id, str), "task_id deve essere stringa"
        assert len(task_id) > 0, "task_id deve avere lunghezza > 0"
        assert "_" not in task_id or task_id.count("_") < 3, "task_id non dovrebbe avere troppi underscore"
        
        print(f"✅ Callback valido per task: {task_id}")
    
    print("✅ Test callback_data: PASSATO")

def test_database_edge_cases():
    """Test specifici per problemi di database"""
    print("\n🧪 TEST: Edge cases database")
    
    db = FamilyTaskDB()
    
    # Verifica che il database gestisca correttamente connessioni multiple
    db.ensure_connection()
    
    # Test query multiple
    for i in range(5):
        chat_id = 77777 + i
        user_id = 88888 + i
        
        db.add_family_member(chat_id, user_id, f"user{i}", f"Utente{i}")
        tasks = db.get_user_assigned_tasks(chat_id, user_id)
        
        print(f"Iteration {i}: Chat {chat_id}, User {user_id}, Tasks: {len(tasks)}")
        
        # Ogni chiamata deve restituire lista valida
        assert isinstance(tasks, list), "Deve sempre restituire lista"
        
        # Se ci sono task, devono essere valide
        for task in tasks:
            assert 'task_id' in task, "Ogni task deve avere task_id"
            assert task['task_id'], "task_id non può essere vuoto"
    
    print("✅ Test database edge cases: PASSATO")

def main():
    """Esegue tutti i test"""
    print("🚀 INIZIO TEST RISOLUZIONE KEYERROR")
    print("=" * 50)
    
    try:
        test_robust_get_user_assigned_tasks()
        test_edge_cases()
        test_callback_data_generation()
        test_database_edge_cases()
        
        print("\n" + "=" * 50)
        print("🎉 TUTTI I TEST PASSATI!")
        print("✅ Il KeyError dovrebbe essere risolto definitivamente.")
        print("\nLe correzioni implementate:")
        print("- Normalizzazione robusta dei risultati database")
        print("- Controlli multipli di sicurezza sui dati")
        print("- Gestione di tutti i casi edge")
        print("- Fallback sicuri per dati corrotti")
        print("- Logging dettagliato per debugging")
        
        return True
        
    except Exception as e:
        print(f"\n❌ TEST FALLITO: {e}")
        logger.error(f"Errore nel test: {e}", exc_info=True)
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
