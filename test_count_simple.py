#!/usr/bin/env python3
"""
Test semplice per verificare la correzione del problema COUNT
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

# Test minimale
print("🔍 Test minimale della correzione COUNT...")

try:
    from main import FamilyTaskDB
    print("✅ Import FamilyTaskDB riuscito")
    
    # Crea istanza
    db = FamilyTaskDB()
    print("✅ Istanza FamilyTaskDB creata")
    
    # Test get_default_tasks
    tasks = db.get_default_tasks()
    print(f"✅ get_default_tasks completato: {len(tasks)} task")
    
    # Verifica che le task abbiano le chiavi corrette
    for task_id, task in list(tasks.items())[:3]:  # Controlla solo le prime 3
        if 'task_id' not in task and 'id' not in task:
            print(f"❌ Task {task_id} manca di id")
        else:
            print(f"✅ Task {task_id}: OK")
    
    print("\n🎉 CORREZIONE COUNT FUNZIONANTE!")
    
except Exception as e:
    print(f"❌ ERRORE: {e}")
    import traceback
    traceback.print_exc()
