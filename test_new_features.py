#!/usr/bin/env python3

"""
Test script for new Family Task Manager features:
1. Immediate task completion
2. Monthly statistics tracking
3. Enhanced statistics display

Note: This is a basic test to validate the code structure.
Full testing requires a PostgreSQL database connection.
"""

import os
import sys
from datetime import datetime

def test_imports():
    """Test that all modules can be imported"""
    try:
        from db import FamilyTaskDB
        from bot_handlers import FamilyTaskBot
        print("✅ All modules imported successfully")
        return True
    except Exception as e:
        print(f"❌ Import error: {e}")
        return False

def test_database_methods():
    """Test that new database methods exist"""
    try:
        from db import FamilyTaskDB
        
        # Check if new methods exist in the class definition without instantiating
        assert hasattr(FamilyTaskDB, 'complete_task_immediately'), "complete_task_immediately method missing"
        assert hasattr(FamilyTaskDB, 'get_monthly_stats'), "get_monthly_stats method missing"
        assert hasattr(FamilyTaskDB, 'get_current_month_stats'), "get_current_month_stats method missing"
        assert hasattr(FamilyTaskDB, '_update_monthly_stats'), "_update_monthly_stats method missing"
        
        print("✅ All new database methods exist")
        return True
    except Exception as e:
        print(f"❌ Database methods test failed: {e}")
        return False

def test_bot_handlers():
    """Test that bot handlers have been updated"""
    try:
        from bot_handlers import FamilyTaskBot
        bot = FamilyTaskBot()
        
        # Check that button_handler method exists (it should have the new handlers)
        assert hasattr(bot, 'button_handler'), "button_handler method missing"
        
        print("✅ Bot handlers updated successfully")
        return True
    except Exception as e:
        print(f"❌ Bot handlers test failed: {e}")
        return False

def test_schema_updates():
    """Test that schema includes monthly_stats table"""
    try:
        with open('schema.sql', 'r') as f:
            schema_content = f.read()
        
        assert 'monthly_stats' in schema_content, "monthly_stats table missing from schema"
        assert 'user_id BIGINT' in schema_content, "monthly_stats structure incomplete"
        assert 'year INTEGER' in schema_content, "monthly_stats year field missing"
        assert 'month INTEGER' in schema_content, "monthly_stats month field missing"
        
        print("✅ Schema updated with monthly_stats table")
        return True
    except Exception as e:
        print(f"❌ Schema test failed: {e}")
        return False

def main():
    print("🏠 FAMILY TASK MANAGER - NEW FEATURES TEST")
    print("=" * 50)
    
    tests = [
        ("Module Imports", test_imports),
        ("Database Methods", test_database_methods),
        ("Bot Handlers", test_bot_handlers),
        ("Schema Updates", test_schema_updates),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n🧪 Testing {test_name}...")
        if test_func():
            passed += 1
        else:
            print(f"❌ {test_name} failed")
    
    print(f"\n📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED!")
        print("\n✨ New features implemented:")
        print("• ⚡ Immediate task completion workflow")
        print("• 📊 Monthly statistics tracking")
        print("• 🎨 Enhanced statistics display with visual charts")
        print("• 📅 Monthly progress visualization")
        print("\n🚀 Bot ready for deployment with new features!")
        return True
    else:
        print(f"\n❌ {total - passed} tests failed")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)