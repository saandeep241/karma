#!/usr/bin/env python3
"""
Quick local test script to verify the application works correctly.
"""

import asyncio
import sys
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

async def test_database():
    """Test database connection and initialization."""
    print("🔍 Testing database connection...")
    try:
        from app.database.connection import init_db, engine
        from app.config import get_settings
        
        settings = get_settings()
        
        # Initialize database
        await init_db()
        
        # Test connection
        from sqlalchemy import text
        async with engine.begin() as conn:
            result = await conn.execute(text("SELECT 1"))
            result.fetchone()
        
        db_type = "PostgreSQL" if settings.use_postgresql else "SQLite"
        print(f"✅ Database connection successful ({db_type})")
        return True
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        return False

def test_config():
    """Test configuration loading."""
    print("🔍 Testing configuration...")
    try:
        from app.config import get_settings
        
        settings = get_settings()
        
        print(f"  - Database: {'PostgreSQL' if settings.use_postgresql else 'SQLite (default)'}")
        print(f"  - Cloud Storage: {'Enabled' if settings.use_cloud_storage else 'Disabled (default)'}")
        print(f"  - AI Enabled: {settings.is_ai_enabled}")
        print(f"  - Auth Enabled: {settings.is_auth_enabled}")
        
        print("✅ Configuration loaded successfully")
        return True
    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        return False

def test_storage_service():
    """Test storage service."""
    print("🔍 Testing storage service...")
    try:
        from app.services.storage_service import get_storage_service
        
        storage = get_storage_service()
        
        # Test write (should be no-op when disabled)
        result = storage.write_json("test", "test.json", {"test": "data"})
        
        if storage.is_cloud_storage_enabled:
            print("  - Cloud Storage: Enabled")
        else:
            print("  - Cloud Storage: Disabled (files won't be written)")
            print("  - Write operation returned:", result)
        
        print("✅ Storage service initialized successfully")
        return True
    except Exception as e:
        print(f"❌ Storage service test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_imports():
    """Test that all critical modules can be imported."""
    print("🔍 Testing module imports...")
    try:
        from app.main import app
        from app.routes import tasks_router, suggestions_router
        from app.services import db_service
        from app.agents import karma_orchestrator
        
        print("✅ All modules imported successfully")
        return True
    except Exception as e:
        print(f"❌ Import test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Run all tests."""
    print("=" * 60)
    print("🧪 Karma Local Testing")
    print("=" * 60)
    print()
    
    results = []
    
    # Run tests
    results.append(("Configuration", test_config()))
    results.append(("Storage Service", test_storage_service()))
    results.append(("Database", await test_database()))
    results.append(("Module Imports", await test_imports()))
    
    # Summary
    print()
    print("=" * 60)
    print("📊 Test Results")
    print("=" * 60)
    
    all_passed = True
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {name}")
        if not passed:
            all_passed = False
    
    print()
    if all_passed:
        print("✅ All tests passed! Ready to start server.")
        print()
        print("To start the server:")
        print("  cd backend")
        print("  source venv/bin/activate")
        print("  uvicorn app.main:app --reload --port 8000")
    else:
        print("❌ Some tests failed. Please check the errors above.")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
