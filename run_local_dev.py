#!/usr/bin/env python3
"""
Local Development Launcher for GlyphMind AI
Starts both backend and frontend for local testing
"""
import os
import sys
import time
import subprocess
import threading
from pathlib import Path

def run_backend():
    """Run the backend server"""
    backend_dir = Path(__file__).parent / "backend"
    os.chdir(backend_dir)
    
    print("🔧 Starting Backend Server...")
    try:
        subprocess.run([sys.executable, "run_local.py"], check=True)
    except KeyboardInterrupt:
        print("🛑 Backend server stopped")
    except Exception as e:
        print(f"❌ Backend error: {e}")

def run_frontend():
    """Run the frontend server"""
    frontend_dir = Path(__file__).parent / "frontend"
    os.chdir(frontend_dir)
    
    # Wait for backend to start
    print("⏳ Waiting for backend to start...")
    time.sleep(5)
    
    print("🎨 Starting Frontend Server...")
    try:
        subprocess.run([sys.executable, "run_local.py"], check=True)
    except KeyboardInterrupt:
        print("🛑 Frontend server stopped")
    except Exception as e:
        print(f"❌ Frontend error: {e}")

def main():
    """Main function to start both servers"""
    print("🧠 GlyphMind AI - Local Development Environment")
    print("=" * 50)
    
    # Check Python version
    if sys.version_info < (3, 10):
        print("❌ Python 3.10+ required")
        sys.exit(1)
    
    # Create threads for backend and frontend
    backend_thread = threading.Thread(target=run_backend, daemon=True)
    frontend_thread = threading.Thread(target=run_frontend, daemon=True)
    
    try:
        # Start backend first
        backend_thread.start()
        
        # Start frontend after a delay
        frontend_thread.start()
        
        print("\n🎉 Both servers starting...")
        print("🌐 Backend API: http://127.0.0.1:8000")
        print("🎨 Frontend UI: http://127.0.0.1:7860")
        print("📚 API Docs: http://127.0.0.1:8000/docs")
        print("\n⏹️  Press Ctrl+C to stop both servers")
        
        # Keep main thread alive
        backend_thread.join()
        frontend_thread.join()
        
    except KeyboardInterrupt:
        print("\n🛑 Shutting down GlyphMind AI...")
        print("👋 Goodbye!")

if __name__ == "__main__":
    main()
