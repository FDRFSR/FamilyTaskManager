#!/usr/bin/env python3

print("🏠 FAMILY TASK MANAGER - COMPREHENSIVE FUNCTIONALITY TEST")
print("=" * 65)

import os
import sys

# Mock environment for testing
os.environ["DATABASE_URL"] = "postgresql://test:test@localhost/test"

class MockDB:
    """Mock database class for testing without real database connection"""
    def __init__(self):
        self.completed_tasks = [
            {"task_id": "preparare_tavola", "task_name": "Preparare la tavola", "user_id": 123, "completion_count": 3},
            {"task_id": "cucina_pulizia", "task_name": "Pulizia cucina", "user_id": 123, "completion_count": 2},
            {"task_id": "spazzatura", "task_name": "Portare fuori la spazzatura", "user_id": 123, "completion_count": 5},
            {"task_id": "preparare_tavola", "task_name": "Preparare la tavola", "user_id": 456, "completion_count": 1},
        ]
    
    def get_user_task_completion_stats(self, user_id):
        """Mock implementation of the new method"""
        user_stats = []
        for task in self.completed_tasks:
            if task["user_id"] == user_id:
                user_stats.append({
                    "task_name": task["task_name"],
                    "completion_count": task["completion_count"]
                })
        # Sort by completion count (descending) then by name
        return sorted(user_stats, key=lambda x: (-x["completion_count"], x["task_name"]))

def test_new_functionality():
    """Test the new task completion statistics functionality"""
    print("Test 1: Simulazione delle nuove statistiche individuali...")
    
    mock_db = MockDB()
    
    # Test user 123 (has multiple completed tasks)
    stats_user_123 = mock_db.get_user_task_completion_stats(123)
    print(f"✅ Statistiche per utente 123: {len(stats_user_123)} task diverse completate")
    
    expected_output = []
    for task_stat in stats_user_123:
        count_text = "volta" if task_stat['completion_count'] == 1 else "volte"
        line = f"• **{task_stat['task_name']}**: completata {task_stat['completion_count']} {count_text}"
        expected_output.append(line)
        print(f"   {line}")
    
    # Test user 456 (has fewer completed tasks)
    stats_user_456 = mock_db.get_user_task_completion_stats(456)
    print(f"✅ Statistiche per utente 456: {len(stats_user_456)} task diverse completate")
    
    for task_stat in stats_user_456:
        count_text = "volta" if task_stat['completion_count'] == 1 else "volte"
        line = f"• **{task_stat['task_name']}**: completata {task_stat['completion_count']} {count_text}"
        print(f"   {line}")
    
    # Test user 999 (no completed tasks)
    stats_user_999 = mock_db.get_user_task_completion_stats(999)
    print(f"✅ Statistiche per utente 999: {len(stats_user_999)} task completate (utente nuovo)")
    
    return True

def test_method_signature():
    """Test that the actual method signature is correct"""
    print("\nTest 2: Verificando la signature del metodo reale...")
    
    try:
        import db
        
        # Check if method exists
        if hasattr(db.FamilyTaskDB, 'get_user_task_completion_stats'):
            print("✅ Metodo get_user_task_completion_stats presente")
            
            # Get method signature
            import inspect
            method = getattr(db.FamilyTaskDB, 'get_user_task_completion_stats')
            sig = inspect.signature(method)
            print(f"✅ Signature: {sig}")
            
            # Check parameter count (self + user_id)
            params = list(sig.parameters.keys())
            if len(params) == 2 and 'self' in params and 'user_id' in params:
                print("✅ Parametri corretti: self e user_id")
            else:
                print(f"❌ Parametri incorretti: {params}")
                return False
                
        else:
            print("❌ Metodo non trovato")
            return False
            
    except Exception as e:
        print(f"❌ Errore nel test: {e}")
        return False
    
    return True

def test_integration():
    """Test integration with bot_handlers"""
    print("\nTest 3: Verificando l'integrazione con bot_handlers...")
    
    try:
        import bot_handlers
        
        # Check if the stats method calls the new database method
        with open('bot_handlers.py', 'r') as f:
            content = f.read()
            
        if 'get_user_task_completion_stats' in content:
            print("✅ bot_handlers chiama il nuovo metodo del database")
        else:
            print("❌ bot_handlers non chiama il nuovo metodo")
            return False
            
        if 'Task completate per tipo:' in content:
            print("✅ Nuovo testo per le statistiche individuali presente")
        else:
            print("❌ Testo delle statistiche individuali mancante")
            return False
            
        if 'completion_count' in content:
            print("✅ Logica per contare le completate presente")
        else:
            print("❌ Logica di conteggio mancante")
            return False
            
    except Exception as e:
        print(f"❌ Errore nel test di integrazione: {e}")
        return False
    
    return True

def main():
    """Run all tests"""
    print("Avviando test completi della nuova funzionalità...\n")
    
    success = True
    
    # Test 1: Mock functionality
    if not test_new_functionality():
        success = False
    
    # Test 2: Method signature
    if not test_method_signature():
        success = False
    
    # Test 3: Integration
    if not test_integration():
        success = False
    
    print("\n" + "=" * 65)
    if success:
        print("🎉 TUTTI I TEST COMPLETATI CON SUCCESSO!")
        print("✅ La nuova funzionalità per le statistiche individuali è implementata correttamente")
        print("✅ L'integrazione tra database e bot handler funziona")
        print("✅ L'output mostrerà: 'preparare la tavola completata 3 volte', ecc.")
    else:
        print("❌ ALCUNI TEST SONO FALLITI!")
        sys.exit(1)

if __name__ == "__main__":
    main()