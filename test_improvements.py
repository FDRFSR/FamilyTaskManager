#!/usr/bin/env python3
"""
Test script to verify the increased number of tasks and optimizations
"""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock

# Test without requiring actual database connection
class TestFamilyTaskManager(unittest.TestCase):
    
    @patch.dict(os.environ, {'DATABASE_URL': 'postgresql://test:test@localhost/test'})
    @patch('psycopg2.connect')
    def test_task_count_increased(self, mock_connect):
        """Test that the number of default tasks has been increased"""
        from db import FamilyTaskDB
        
        # Mock database connection and cursor
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchall.return_value = []  # Simulate empty database
        
        # Create FamilyTaskDB instance
        db = FamilyTaskDB()
        
        # Check that tasks were loaded
        self.assertIsNotNone(db._tasks)
        
        # Count the default tasks by examining the method
        import inspect
        source = inspect.getsource(db._load_tasks_from_db)
        
        # Count task entries in the source code more accurately
        task_count = source.count('("', source.find('default_tasks'))
        
        print(f"Number of default tasks found: {task_count}")
        
        # Verify we have more than the original 21 tasks
        self.assertGreater(task_count, 21, "Should have more than 21 tasks")
        self.assertGreaterEqual(task_count, 40, "Should have at least 40 tasks after expansion")
    
    def test_bot_handlers_syntax(self):
        """Test that bot handlers code is syntactically correct"""
        try:
            import bot_handlers
            bot = bot_handlers.FamilyTaskBot()
            
            # Test that categories are properly defined
            self.assertTrue(hasattr(bot, 'CATEGORIES'))
            self.assertTrue(hasattr(bot, 'CATEGORY_MAP'))
            self.assertGreater(len(bot.CATEGORIES), 0)
            self.assertGreater(len(bot.CATEGORY_MAP), 0)
            
            print("Bot handlers loaded successfully with optimized structure")
            return True
        except Exception as e:
            self.fail(f"Bot handlers failed to load: {e}")
    
    def test_utils_module(self):
        """Test that utils module is properly structured"""
        try:
            import utils
            self.assertTrue(hasattr(utils, 'send_and_track_message'))
            self.assertTrue(hasattr(utils, 'delete_old_messages'))
            print("Utils module loaded successfully")
            return True
        except Exception as e:
            self.fail(f"Utils module failed to load: {e}")

if __name__ == '__main__':
    print("🧪 Testing Family Task Manager improvements...")
    print("=" * 50)
    
    unittest.main(verbosity=2)