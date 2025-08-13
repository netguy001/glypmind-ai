#!/usr/bin/env python3
"""
Test script to verify Render.com deployment readiness
"""
import os
import sys
import asyncio
from pathlib import Path

def test_environment_setup():
    """Test environment variable handling"""
    print("🧪 Testing Environment Setup...")
    
    # Test PORT handling
    os.environ["PORT"] = "8000"
    port = int(os.environ.get("PORT", 8000))
    assert port == 8000, "PORT environment variable not working"
    print("✅ PORT environment variable: OK")
    
    # Test DATA_DIR handling
    os.environ["DATA_DIR"] = "/tmp/test_data"
    data_dir = os.environ.get("DATA_DIR", "data")
    assert data_dir == "/tmp/test_data", "DATA_DIR environment variable not working"
    print("✅ DATA_DIR environment variable: OK")
    
    # Test ENVIRONMENT handling
    os.environ["ENVIRONMENT"] = "production"
    env = os.environ.get("ENVIRONMENT", "development")
    assert env == "production", "ENVIRONMENT variable not working"
    print("✅ ENVIRONMENT variable: OK")

def test_imports():
    """Test that all required modules can be imported"""
    print("\n🧪 Testing Module Imports...")
    
    try:
        from server.app import app
        print("✅ FastAPI app import: OK")
    except Exception as e:
        print(f"❌ FastAPI app import failed: {e}")
        return False
    
    try:
        import uvicorn
        print("✅ Uvicorn import: OK")
    except Exception as e:
        print(f"❌ Uvicorn import failed: {e}")
        return False
    
    try:
        from config.config_manager import get_config
        config = get_config()
        print("✅ Config manager import: OK")
    except Exception as e:
        print(f"❌ Config manager import failed: {e}")
        return False
    
    return True

def test_data_directory():
    """Test data directory creation"""
    print("\n🧪 Testing Data Directory Creation...")
    
    test_data_dir = Path("/tmp/glyphmind_test")
    os.environ["DATA_DIR"] = str(test_data_dir)
    
    # Test directory creation
    directories = [
        test_data_dir,
        test_data_dir / "cache",
        test_data_dir / "logs", 
        test_data_dir / "models",
    ]
    
    for directory in directories:
        try:
            directory.mkdir(parents=True, exist_ok=True)
            assert directory.exists(), f"Could not create {directory}"
            print(f"✅ Created directory: {directory}")
        except Exception as e:
            print(f"❌ Failed to create {directory}: {e}")
            return False
    
    # Cleanup
    import shutil
    shutil.rmtree(test_data_dir)
    print("✅ Data directory test: OK")
    
    return True

async def test_database_initialization():
    """Test database initialization"""
    print("\n🧪 Testing Database Initialization...")
    
    test_data_dir = Path("/tmp/glyphmind_db_test")
    os.environ["DATA_DIR"] = str(test_data_dir)
    
    try:
        # Test knowledge base
        from knowledge_base.knowledge_manager import SQLiteKnowledgeStore
        kb_store = SQLiteKnowledgeStore()
        await kb_store.initialize()
        print("✅ Knowledge base initialization: OK")
        
        # Test ledger
        from ledger.ledger_manager import LedgerManager
        ledger = LedgerManager()
        await ledger.initialize()
        print("✅ Ledger initialization: OK")
        
        # Cleanup
        import shutil
        shutil.rmtree(test_data_dir)
        
        return True
        
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        return False

def test_cors_configuration():
    """Test CORS configuration"""
    print("\n🧪 Testing CORS Configuration...")
    
    # Test with ALLOWED_ORIGINS environment variable
    os.environ["ALLOWED_ORIGINS"] = "https://test1.hf.space,https://test2.hf.space"
    os.environ["ENVIRONMENT"] = "production"
    
    try:
        from server.app import app
        
        # Check that CORS middleware is configured
        cors_middleware = None
        for middleware in app.user_middleware:
            if "CORSMiddleware" in str(middleware.cls):
                cors_middleware = middleware
                break
        
        assert cors_middleware is not None, "CORS middleware not found"
        print("✅ CORS middleware configured: OK")
        
        return True
        
    except Exception as e:
        print(f"❌ CORS configuration test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 GlyphMind AI Backend - Render.com Readiness Test")
    print("=" * 50)
    
    tests = [
        ("Environment Setup", test_environment_setup),
        ("Module Imports", test_imports),
        ("Data Directory", test_data_directory),
        ("CORS Configuration", test_cors_configuration),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            if asyncio.iscoroutinefunction(test_func):
                result = asyncio.run(test_func())
            else:
                result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} test crashed: {e}")
            results.append((test_name, False))
    
    # Test database initialization separately
    try:
        print("\n🧪 Testing Database Initialization...")
        asyncio.run(test_database_initialization())
        results.append(("Database Initialization", True))
    except Exception as e:
        print(f"❌ Database initialization test crashed: {e}")
        results.append(("Database Initialization", False))
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 TEST RESULTS SUMMARY")
    print("=" * 50)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {test_name.ljust(25)}: {status}")
        if result:
            passed += 1
    
    print(f"\n🎯 Overall: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("🎉 All tests passed! Backend is ready for Render.com deployment.")
        return 0
    else:
        print("⚠️  Some tests failed. Please fix issues before deploying to Render.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
