#!/usr/bin/env python3
"""
Local development server for GlyphMind AI Backend
Compatible with both local development and Render.com deployment
"""
import os
import sys
from pathlib import Path
import uvicorn

def setup_local_environment():
    """Setup environment for local development"""
    
    # Set development environment variables
    os.environ.setdefault("HOST", "127.0.0.1")
    os.environ.setdefault("PORT", "8000")
    os.environ.setdefault("LOG_LEVEL", "debug")
    os.environ.setdefault("ENVIRONMENT", "development")
    
    # Set up local data directory
    backend_dir = Path(__file__).parent
    data_dir = backend_dir / "data"
    os.environ.setdefault("DATA_DIR", str(data_dir))
    
    # Create data directories
    directories = [
        data_dir,
        data_dir / "cache",
        data_dir / "logs",
        data_dir / "models",
    ]
    
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)
    
    print("🧠 Starting GlyphMind AI Backend (Local Development)")
    print(f"🌐 Server: http://127.0.0.1:8000")
    print(f"📚 API Docs: http://127.0.0.1:8000/docs")
    print(f"📁 Data Dir: {data_dir}")
    print("🔄 Auto-reload enabled")

if __name__ == "__main__":
    try:
        # Setup local environment
        setup_local_environment()
        
        # Start the server with auto-reload for development
        uvicorn.run(
            "server.app:app",
            host="127.0.0.1",
            port=8000,
            reload=True,
            log_level="debug",
            reload_dirs=["server", "core", "web_intel", "knowledge_base", "evolution_engine", "router", "ledger", "logs", "config"]
        )
        
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
    except Exception as e:
        print(f"❌ Error starting server: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
