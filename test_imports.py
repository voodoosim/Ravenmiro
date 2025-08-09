#!/usr/bin/env python3
"""
Test script to verify all imports work correctly
"""

import sys
import os

# Add bot directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'bot'))

def test_imports():
    """Test all module imports"""
    try:
        print("Testing imports...")
        
        # Test config import
        from config import Config
        print("[OK] Config imported successfully")
        
        # Test session_handler import
        from session_handler import SessionManager
        print("[OK] SessionManager imported successfully")
        
        # Test mirror import
        from mirror import MirrorEngine
        print("[OK] MirrorEngine imported successfully")
        
        # Test commands import
        from commands import CommandHandler
        print("[OK] CommandHandler imported successfully")
        
        # Test creating Config instance
        config = Config()
        print("[OK] Config instance created successfully")
        
        print("\n[SUCCESS] All imports and basic functionality work correctly!")
        return True
        
    except ImportError as e:
        print(f"[ERROR] Import error: {e}")
        return False
    except Exception as e:
        print(f"[ERROR] Error: {e}")
        return False

if __name__ == "__main__":
    success = test_imports()
    sys.exit(0 if success else 1)