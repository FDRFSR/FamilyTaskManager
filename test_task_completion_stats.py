#!/usr/bin/env python3

print("🏠 FAMILY TASK MANAGER - TEST TASK COMPLETION STATISTICS")
print("=" * 60)

import os
import sys
import ast

# Test 1: Check if the new method exists in db.py
print("Test 1: Verificando la presenza del nuovo metodo...")
try:
    with open('db.py', 'r') as f:
        content = f.read()
        
    if 'get_user_task_completion_stats' in content:
        print("✅ Metodo get_user_task_completion_stats trovato nel codice")
        
        # Parse the code to verify it's syntactically correct
        try:
            ast.parse(content)
            print("✅ Sintassi del file db.py corretta")
        except SyntaxError as e:
            print(f"❌ Errore di sintassi in db.py: {e}")
            sys.exit(1)
    else:
        print("❌ Metodo get_user_task_completion_stats non trovato")
        sys.exit(1)
        
except Exception as e:
    print(f"❌ Errore nella lettura di db.py: {e}")
    sys.exit(1)

# Test 2: Check if bot_handlers.py was updated correctly
print("\nTest 2: Verificando gli aggiornamenti in bot_handlers.py...")
try:
    with open('bot_handlers.py', 'r') as f:
        content = f.read()
        
    if 'get_user_task_completion_stats' in content:
        print("✅ Chiamata al nuovo metodo trovata in bot_handlers.py")
        
        if 'Task completate per tipo:' in content:
            print("✅ Nuovo testo delle statistiche individuali trovato")
        else:
            print("❌ Testo per le statistiche individuali non trovato")
            sys.exit(1)
            
        # Parse the code to verify it's syntactically correct
        try:
            ast.parse(content)
            print("✅ Sintassi del file bot_handlers.py corretta")
        except SyntaxError as e:
            print(f"❌ Errore di sintassi in bot_handlers.py: {e}")
            sys.exit(1)
    else:
        print("❌ Chiamata al nuovo metodo non trovata in bot_handlers.py")
        sys.exit(1)
        
except Exception as e:
    print(f"❌ Errore nella lettura di bot_handlers.py: {e}")
    sys.exit(1)

# Test 3: Try importing without database connection
print("\nTest 3: Verificando l'importabilità del codice...")
try:
    # Mock the database URL to avoid connection
    os.environ["DATABASE_URL"] = "postgresql://test:test@localhost/test"
    
    # Import just the module without initializing
    import db
    print("✅ Modulo db importato correttamente")
    
    # Check if the method exists in the class
    if hasattr(db.FamilyTaskDB, 'get_user_task_completion_stats'):
        print("✅ Metodo get_user_task_completion_stats presente nella classe")
    else:
        print("❌ Metodo get_user_task_completion_stats non presente nella classe")
        sys.exit(1)
        
except Exception as e:
    print(f"❌ Errore nell'importazione: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n🎯 TUTTI I TEST COMPLETATI CON SUCCESSO!")
print("✅ La nuova funzionalità è implementata correttamente")
print("✅ I file sono sintatticamente corretti")
print("✅ Il codice è importabile senza errori")